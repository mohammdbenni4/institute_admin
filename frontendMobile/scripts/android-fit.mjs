// Post-`cap add android` patches. `android/` is gitignored and regenerated from
// scratch by Capacitor, so every native change we depend on has to be re-applied
// from tracked sources here. Run after `npx cap add android` (the `cap:android` /
// `apk:debug` scripts already do). Every step is independently idempotent.
//
//   1. Opt out of Android 15 (targetSdk 35) forced edge-to-edge so the WebView sits
//      BELOW the status/navigation bars — the app isn't designed edge-to-edge, and
//      without this the UI runs under the bars on devices like the Samsung A54. Also
//      colours the status bar to match the dark-green top bar.
//   2. Install the ReportPrinter plugin and register it with MainActivity. Android's
//      WebView has no `window.print()`, so without this the report export button does
//      nothing at all on the phone (see native/android/ReportPrinter.java).
//   3. Stamp the version from package.json onto build.gradle. Regenerating `android/`
//      resets it to Capacitor's default `1` / `"1.0"`, and a versionCode that does not
//      increase makes Android refuse the update — this used to have to be remembered
//      by hand on every rebuild. package.json is now the single source of truth, which
//      also keeps the number shown inside the app identical to the one Android shows.

import { copyFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const ANDROID = join(ROOT, 'android');
const NATIVE_SRC = join(ROOT, 'native', 'android');
const APP_PACKAGE = 'cloud/sarhalquran/teacher';

if (!existsSync(ANDROID)) {
	console.error('android-fit: android/ not found — run `npx cap add android` first.');
	process.exit(1);
}

// ---------------------------------------------------------------- 1. edge-to-edge ---

function patchStyles() {
	const path = join(ANDROID, 'app/src/main/res/values/styles.xml');
	if (!existsSync(path)) {
		console.error('android-fit: styles.xml not found.');
		process.exit(1);
	}

	let xml = readFileSync(path, 'utf8');
	if (xml.includes('windowOptOutEdgeToEdgeEnforcement')) {
		console.log('  edge-to-edge: already patched.');
		return;
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
			body.includes('windowOptOutEdgeToEdgeEnforcement')
				? m
				: `${open}${body}${ITEMS}\n    ${close}`
	);

	writeFileSync(path, xml);
	console.log('  edge-to-edge: opted out + status bar colour set.');
}

// ------------------------------------------------------------- 2. ReportPrinter ---

/** Copy a tracked .java file into the generated project, only when it differs. */
function installJava(fileName, targetPackageDir) {
	const from = join(NATIVE_SRC, fileName);
	if (!existsSync(from)) {
		console.error(`android-fit: missing native source ${from}`);
		process.exit(1);
	}
	const dir = join(ANDROID, 'app/src/main/java', targetPackageDir);
	mkdirSync(dir, { recursive: true });
	const to = join(dir, fileName);
	if (existsSync(to) && readFileSync(to, 'utf8') === readFileSync(from, 'utf8')) return false;
	copyFileSync(from, to);
	return true;
}

function patchPrinter() {
	const copiedPlugin = installJava('ReportPrinter.java', APP_PACKAGE);
	// Lives in `android.print` on purpose — see the file's own comment.
	const copiedCallbacks = installJava('PrintAdapterCallbacks.java', 'android/print');

	// A plugin class that ships with the app (rather than an npm package) has to be
	// registered explicitly, or the bridge never exposes it to JavaScript.
	const mainPath = join(ANDROID, 'app/src/main/java', APP_PACKAGE, 'MainActivity.java');
	if (!existsSync(mainPath)) {
		console.error('android-fit: MainActivity.java not found.');
		process.exit(1);
	}
	let java = readFileSync(mainPath, 'utf8');
	let registered = java.includes('registerPlugin(ReportPrinter.class)');

	if (!registered) {
		if (!java.includes('import android.os.Bundle;')) {
			java = java.replace(
				'import com.getcapacitor.BridgeActivity;',
				'import android.os.Bundle;\n\nimport com.getcapacitor.BridgeActivity;'
			);
		}
		// Capacitor's template body is an empty `{}`; replace it with the override.
		java = java.replace(
			/public class MainActivity extends BridgeActivity \{\s*\}/,
			`public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        // Must be registered before super.onCreate() so the bridge picks it up.
        registerPlugin(ReportPrinter.class);
        super.onCreate(savedInstanceState);
    }
}`
		);
		if (!java.includes('registerPlugin(ReportPrinter.class)')) {
			console.error(
				'android-fit: could not register ReportPrinter — MainActivity.java has an ' +
					'unexpected shape. Register it by hand before building.'
			);
			process.exit(1);
		}
		writeFileSync(mainPath, java);
		registered = true;
	}

	const parts = [];
	if (copiedPlugin || copiedCallbacks) parts.push('sources installed');
	else parts.push('sources up to date');
	console.log(`  ReportPrinter: ${parts.join(', ')}, registered in MainActivity.`);
}

// ----------------------------------------------------------------- 3. version ---

function patchVersion() {
	const pkg = JSON.parse(readFileSync(join(ROOT, 'package.json'), 'utf8'));
	const versionName = pkg.version;
	const versionCode = pkg.androidVersionCode;
	if (!versionName || !Number.isInteger(versionCode)) {
		console.error(
			'android-fit: package.json needs a "version" string and an integer "androidVersionCode".'
		);
		process.exit(1);
	}

	const path = join(ANDROID, 'app/build.gradle');
	if (!existsSync(path)) {
		console.error('android-fit: app/build.gradle not found.');
		process.exit(1);
	}
	let gradle = readFileSync(path, 'utf8');
	const before = gradle;
	gradle = gradle.replace(/versionCode\s+\d+/, `versionCode ${versionCode}`);
	gradle = gradle.replace(/versionName\s+"[^"]*"/, `versionName "${versionName}"`);

	if (!/versionCode\s+\d+/.test(gradle) || !/versionName\s+"[^"]*"/.test(gradle)) {
		console.error('android-fit: could not find versionCode/versionName in app/build.gradle.');
		process.exit(1);
	}
	if (gradle !== before) writeFileSync(path, gradle);
	console.log(`  version: versionCode ${versionCode}, versionName "${versionName}".`);
}

console.log('android-fit: applying native patches…');
patchStyles();
patchPrinter();
patchVersion();
