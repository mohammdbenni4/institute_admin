// Post-`cap add android` patch: opt out of Android 15 (targetSdk 35) forced
// edge-to-edge so the WebView sits BELOW the status/navigation bars (the app isn't
// designed edge-to-edge — without this, content extends under the bars and the UI
// doesn't fit on devices like the Samsung A54). Also colours the status bar to match
// the dark-green top bar. Idempotent; run after `npx cap add android`.

import { existsSync, readFileSync, writeFileSync } from 'node:fs';

const path = 'android/app/src/main/res/values/styles.xml';
if (!existsSync(path)) {
	console.error('styles.xml not found — run `npx cap add android` first.');
	process.exit(1);
}

let xml = readFileSync(path, 'utf8');
if (xml.includes('windowOptOutEdgeToEdgeEnforcement')) {
	console.log('android-fit: already patched.');
	process.exit(0);
}

const ITEMS = [
	'<item name="android:windowOptOutEdgeToEdgeEnforcement" tools:targetApi="35">true</item>',
	'<item name="android:statusBarColor">#134D36</item>',
	'<item name="android:windowLightStatusBar">false</item>'
]
	.map((i) => `        ${i}`)
	.join('\n');

// Ensure the `tools:` namespace exists on <resources>.
if (!/<resources[^>]*xmlns:tools=/.test(xml)) {
	xml = xml.replace(
		/<resources(\s|>)/,
		'<resources xmlns:tools="http://schemas.android.com/tools"$1'
	);
}

// Self-closing AppTheme styles → open/close with the items.
xml = xml.replace(
	/<style\s+name="(AppTheme[^"]*)"\s+parent="([^"]*)"\s*\/>/g,
	(_m, name, parent) => `<style name="${name}" parent="${parent}">\n${ITEMS}\n    </style>`
);

// Inject the items into every AppTheme* style that lacks them.
xml = xml.replace(
	/(<style\s+name="AppTheme[^"]*"[^>]*>)([\s\S]*?)(<\/style>)/g,
	(m, open, body, close) =>
		body.includes('windowOptOutEdgeToEdgeEnforcement') ? m : `${open}${body}${ITEMS}\n    ${close}`
);

writeFileSync(path, xml);
console.log('android-fit: opted out of edge-to-edge + set status bar colour.');
