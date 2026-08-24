// Fail the build when the vendored icon font is out of date.
//
// Why this exists: a Material Symbols icon is a *ligature*. If the font is missing
// the glyph, the browser silently paints the icon's name as ordinary text — the
// settings button renders the word "settings" at icon size, covering the content
// next to it. Nothing errors; it just looks broken, and only on screens nobody
// re-checked after the edit.
//
// This has happened twice: once when `remove` was added to the list, and once when
// a branch added `settings` to the list but the regenerated font was not carried
// across in a merge. Both are the same mistake — the ICONS list and the vendored
// .woff2 drifted apart.
//
// The check is a pure list comparison, so it has no false positives:
//   scripts/fetch-fonts.mjs ICONS  ==  static/fonts/icons.json
// The manifest is written by fetch-fonts.mjs at the moment it downloads the subset,
// so it describes what the font really contains, not what someone intended.
//
// Fix for a failure: run `npm run fonts` (needs network) and commit the result.

import { readFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const SCRIPT = join(ROOT, 'scripts', 'fetch-fonts.mjs');
const MANIFEST = join(ROOT, 'static', 'fonts', 'icons.json');

/** The ICONS array as it appears in fetch-fonts.mjs, read as text so this script
 *  never has to import (and thus run) the downloader. */
async function requestedIcons() {
	const source = await readFile(SCRIPT, 'utf8');
	const block = source.split('const ICONS = [')[1]?.split('];')[0];
	if (!block) throw new Error('could not find the ICONS array in scripts/fetch-fonts.mjs');
	return [...block.matchAll(/'([a-z][a-z_0-9]*)'/g)].map((m) => m[1]);
}

async function vendoredIcons() {
	try {
		return JSON.parse(await readFile(MANIFEST, 'utf8')).icons ?? [];
	} catch (e) {
		if (e.code === 'ENOENT') return null;
		throw e;
	}
}

const requested = await requestedIcons();
const vendored = await vendoredIcons();

if (vendored === null) {
	console.error('✗ static/fonts/icons.json is missing — run `npm run fonts`.');
	process.exit(1);
}

const missing = requested.filter((i) => !vendored.includes(i));
const stale = vendored.filter((i) => !requested.includes(i));

if (missing.length === 0 && stale.length === 0) {
	console.log(`✓ icon font is up to date (${requested.length} icons)`);
	process.exit(0);
}

console.error('✗ The vendored icon font does not match the ICONS list.\n');
if (missing.length) {
	console.error(
		`  Requested but NOT in the font — these would render as literal words:\n    ${missing.join(', ')}\n`
	);
}
if (stale.length) {
	console.error(
		`  In the font but no longer requested (harmless, just stale):\n    ${stale.join(', ')}\n`
	);
}
console.error('  Fix: run `npm run fonts` (requires network) and commit static/fonts/.');
process.exit(1);
