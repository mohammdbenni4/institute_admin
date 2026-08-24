// Page ⇄ (surah, ayah, juz) lookups against the standard 604-page Hafs 'an Asim mushaf.

import { AYAH_INFO } from './ayahs';
import { PAGE_START } from './pages';
import { SURAHS, type SurahInfo } from './surahs';

export type { SurahInfo };
export { SURAHS };

export interface PageRef {
	page: number;
	surah: SurahInfo;
	ayah: number;
	juz: number;
}

/** The surah + starting ayah + juz a mushaf page (1..604) opens on, or null if out of range. */
export function pageRef(page: number): PageRef | null {
	if (!Number.isInteger(page) || page < 1 || page > PAGE_START.length) return null;
	const [surahNumber, ayah, juz] = PAGE_START[page - 1];
	const surah = SURAHS[surahNumber - 1];
	if (!surah) return null;
	return { page, surah, ayah, juz };
}

/** The page + juz a given surah/ayah falls on, or null if out of range. */
export function pageForAyah(
	surahNumber: number,
	ayah: number
): { page: number; juz: number } | null {
	const arr = AYAH_INFO[surahNumber - 1];
	if (!arr) return null;
	const entry = arr[ayah - 1];
	if (!entry) return null;
	const [page, juz] = entry;
	return { page, juz };
}

/** First mushaf page of each juz (1..30), derived once from PAGE_START. */
const JUZ_START_PAGE: readonly number[] = (() => {
	const arr: number[] = new Array(30).fill(0);
	for (let p = 1; p <= PAGE_START.length; p++) {
		const juz = PAGE_START[p - 1][2];
		if (!arr[juz - 1]) arr[juz - 1] = p;
	}
	return arr;
})();

/** Jump straight to the start of a juz (1..30): its first page, surah and ayah. */
export function pageForJuz(juz: number): PageRef | null {
	if (!Number.isInteger(juz) || juz < 1 || juz > JUZ_START_PAGE.length) return null;
	const page = JUZ_START_PAGE[juz - 1];
	return page ? pageRef(page) : null;
}

/** Every mushaf page a surah spans (its own firstPage..lastPage), for a page dropdown
 *  narrowed to just that surah. */
export function pagesForSurah(surah: SurahInfo): number[] {
	return Array.from(
		{ length: surah.lastPage - surah.firstPage + 1 },
		(_, i) => surah.firstPage + i
	);
}

/** Every juz a surah spans (min..max over its pages), for a juz dropdown narrowed to
 *  just that surah. Contiguous, since a surah's pages are contiguous and juz only ever
 *  increase with the page number. */
export function juzsForSurah(surah: SurahInfo): number[] {
	let first = Infinity;
	let last = -Infinity;
	for (let p = surah.firstPage; p <= surah.lastPage; p++) {
		const juz = PAGE_START[p - 1][2];
		if (juz < first) first = juz;
		if (juz > last) last = juz;
	}
	return Array.from({ length: last - first + 1 }, (_, i) => first + i);
}

/** The first page within [fromPage, toPage] that belongs to the given juz, or null. */
export function firstPageOfJuzInRange(
	juz: number,
	fromPage: number,
	toPage: number
): number | null {
	for (let p = fromPage; p <= toPage; p++) {
		if (PAGE_START[p - 1][2] === juz) return p;
	}
	return null;
}

/** [firstPage, lastPage] a juz (1..30) spans across the whole mushaf. */
export function juzPageRange(juz: number): { first: number; last: number } | null {
	if (!Number.isInteger(juz) || juz < 1 || juz > JUZ_START_PAGE.length) return null;
	const first = JUZ_START_PAGE[juz - 1];
	const last = juz < JUZ_START_PAGE.length ? JUZ_START_PAGE[juz] - 1 : PAGE_START.length;
	return { first, last };
}

/** Every mushaf page a juz spans, for a page dropdown narrowed to just that juz. */
export function pagesForJuz(juz: number): number[] {
	const r = juzPageRange(juz);
	if (!r) return [];
	return Array.from({ length: r.last - r.first + 1 }, (_, i) => r.first + i);
}

/** Every surah a juz touches (even briefly), for a surah dropdown narrowed to just that
 *  juz — the mirror of `juzsForSurah`. */
export function surahsForJuz(juz: number): SurahInfo[] {
	const r = juzPageRange(juz);
	if (!r) return [];
	return SURAHS.filter((s) => s.firstPage <= r.last && s.lastPage >= r.first);
}

/** A surah's ayahs that fall within a given juz, for an ayah dropdown narrowed to both
 *  the picked surah and the picked juz at once. */
export function ayahsInJuz(surah: SurahInfo, juz: number): number[] {
	const arr = AYAH_INFO[surah.number - 1];
	if (!arr) return [];
	const out: number[] = [];
	for (let i = 0; i < arr.length; i++) {
		if (arr[i][1] === juz) out.push(i + 1);
	}
	return out;
}

/** One line describing a page: «سورة البقرة، الآية 6». */
export function pageRefLabel(page: number): string | null {
	const ref = pageRef(page);
	return ref ? `${ref.surah.name}، الآية ${ref.ayah}` : null;
}

/** Page/juz/surah breakdown, abbreviated and ordered صفحة/جزء/سورة: «ص45 · ج3 · البقرة». */
export function pageFullLabel(page: number): string | null {
	const ref = pageRef(page);
	return ref ? `ص${ref.page} · ج${ref.juz} · ${ref.surah.name}` : null;
}
