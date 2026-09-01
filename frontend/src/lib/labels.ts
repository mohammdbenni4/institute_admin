// Arabic display labels for backend enums + small formatting helpers.

import type { Attitude, OrphanStatus, Rating, UserRole, Weekday } from '$lib/api';
import { WEEKDAYS } from '$lib/api';

export const ROLE_LABELS: Record<UserRole, string> = {
	super_admin: 'مدير عام',
	teacher: 'معلم'
};

export const ORPHAN_LABELS: Record<OrphanStatus, string> = {
	father: 'يتيم الأب',
	mother: 'يتيم الأم',
	both: 'يتيم الأبوين'
};

export const WEEKDAY_LABELS: Record<Weekday, string> = {
	saturday: 'السبت',
	sunday: 'الأحد',
	monday: 'الإثنين',
	tuesday: 'الثلاثاء',
	wednesday: 'الأربعاء',
	thursday: 'الخميس',
	friday: 'الجمعة'
};

export const ORDERED_WEEKDAYS = WEEKDAYS;

/** Format an ISO date/datetime as a localized Gregorian date, or `—` if empty. */
export function formatDate(value: string | null | undefined): string {
	if (!value) return '—';
	const date = new Date(value);
	if (Number.isNaN(date.getTime())) return value;
	return new Intl.DateTimeFormat('ar', {
		year: 'numeric',
		month: 'long',
		day: 'numeric'
	}).format(date);
}

// --- Daily-record scales ---------------------------------------------------
export const RATING_LABELS: Record<Rating, string> = {
	4: 'ممتاز',
	3: 'جيد جداً',
	2: 'جيد',
	1: 'ضعيف'
};

export const ATTITUDE_LABELS: Record<Attitude, string> = {
	3: 'مؤدب',
	2: 'متوسط',
	1: 'مشاغب'
};

export function ratingLabel(r: Rating | null | undefined): string {
	return r == null ? '—' : RATING_LABELS[r];
}

export function attitudeLabel(a: Attitude | null | undefined): string {
	return a == null ? '—' : ATTITUDE_LABELS[a];
}

// --- Month helpers (for the `<input type="month">` value `YYYY-MM`) --------
/** The current month as `YYYY-MM`. */
export function currentMonth(): string {
	const d = new Date();
	return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
}

/** First and last ISO dates (`YYYY-MM-DD`) of a `YYYY-MM` month. */
export function monthBounds(month: string): { from: string; to: string } {
	const [y, m] = month.split('-').map(Number);
	const last = new Date(y, m, 0).getDate();
	const mm = String(m).padStart(2, '0');
	return { from: `${y}-${mm}-01`, to: `${y}-${mm}-${String(last).padStart(2, '0')}` };
}

/** A human month label, e.g. "يونيو ٢٠٢٦". */
export function formatMonth(month: string): string {
	const [y, m] = month.split('-').map(Number);
	return new Intl.DateTimeFormat('ar', { month: 'long', year: 'numeric' }).format(
		new Date(y, m - 1, 1)
	);
}

/** One record's page range as `[first, last]`, or null when it recorded no recitation. */
function recordRange(record: {
	exam_from: number | null;
	exam_to: number | null;
}): [number, number] | null {
	const { exam_from: from, exam_to: to } = record;
	if (from != null && to != null) {
		// A reversed range is a typo, not backwards progress. Trust «من», which is the
		// field the teacher fills first, and ignore the impossible «إلى».
		return to >= from ? [from, to] : [from, from];
	}
	if (from != null) return [from, from];
	if (to != null) return [to, to];
	return null;
}

/**
 * How many *distinct* pages a student covered over a set of records.
 *
 * **Revision is never counted here.** المراجعة lives in its own column and is only
 * ever text — «الجزء ٣٠ (كله): نجح» for a قرآن student, «المرحلة ٢: نجح» for a رشيدي
 * one — so it carries no page range at all. The parameter type below deliberately
 * accepts only the two exam columns, which makes it structurally impossible for a
 * revision to reach this count, now or after any future edit.
 *
 * Deliberately not a sum. Teachers drill the same page for days at a time —
 * مؤيد recited pages 39–41 across ten sessions, repeating page 40 six times — so
 * adding the daily counts printed «من 39 إلى 41 · المجموع 10 صفحة», a line that
 * contradicts itself. Counting each page once makes the total mean progress
 * («how far did the student get») and guarantees it can never exceed the range
 * shown beside it.
 *
 * `exam_total` is deliberately ignored here: it is a per-day count and cannot say
 * *which* pages were involved. It still drives the daily rows, and no record in
 * the database carries one without also carrying a range, so nothing is lost.
 * The one thing this cannot express is a half page — a student who recited only
 * «نصف صفحة» of page 10 counts as having covered that page.
 */
export function pagesCovered(
	records: { exam_from: number | null; exam_to: number | null }[]
): number {
	const pages = new Set<number>();
	for (const record of records) {
		const range = recordRange(record);
		if (!range) continue;
		const [first, last] = range;
		// The mushaf is 604 pages; anything wider is bad data, so count only its start
		// rather than inflating the total with hundreds of pages nobody recited.
		if (last - first > 604) {
			pages.add(first);
			continue;
		}
		for (let page = first; page <= last; page++) pages.add(page);
	}
	return pages.size;
}

/**
 * The span of pages touched in the period, as `من … إلى …`.
 *
 * Min and max — *not* the first and last record. Ordering by date printed
 * «من 56 إلى 41» for a student whose first session happened to start high and
 * whose last one ended low, and hid that another student had gone back to page 23
 * by showing «من 30 إلى 31».
 */
export function recitedRange(records: { exam_from: number | null; exam_to: number | null }[]): {
	from: number | null;
	to: number | null;
} {
	let from: number | null = null;
	let to: number | null = null;
	for (const record of records) {
		const range = recordRange(record);
		if (!range) continue;
		if (from == null || range[0] < from) from = range[0];
		if (to == null || range[1] > to) to = range[1];
	}
	return { from, to };
}
