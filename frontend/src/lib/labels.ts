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

/**
 * How many pages one daily record covers («العدد الكلي» for that day).
 *
 * `exam_total` is what the teacher typed and it always wins when present — it is the
 * only way a fraction can be expressed («نصف صفحة» = 0.5), and 42 records in August
 * alone carry one.
 *
 * But that field is optional, and in practice teachers fill in the page range and
 * leave it blank: 1104 of 2491 recitation records in August 2026 had no `exam_total`.
 * Summing only the records that carried one made every report understate the month —
 * a student with 15 recorded days and pages 51→66 printed a total of «4 صفحة». So when
 * it is missing, fall back to the range the teacher *did* record.
 */
export function recordPages(record: {
	exam_from: number | null;
	exam_to: number | null;
	exam_total: number | null;
}): number {
	if (record.exam_total != null) return record.exam_total;
	if (record.exam_from != null && record.exam_to != null) {
		// Inclusive — «من 54 إلى 55» is two pages, not one. A reversed range is bad data
		// rather than negative progress, so it contributes nothing instead of subtracting.
		return record.exam_to >= record.exam_from ? record.exam_to - record.exam_from + 1 : 0;
	}
	// Only one end of the range was recorded: a single page was recited.
	if (record.exam_from != null || record.exam_to != null) return 1;
	return 0;
}

/**
 * Total pages across many records. Rounded to two decimals because adding halves as
 * floats leaves artefacts like 2.5000000000000004, which would be printed verbatim.
 */
export function totalRecordPages(
	records: { exam_from: number | null; exam_to: number | null; exam_total: number | null }[]
): number {
	return Math.round(records.reduce((sum, r) => sum + recordPages(r), 0) * 100) / 100;
}
