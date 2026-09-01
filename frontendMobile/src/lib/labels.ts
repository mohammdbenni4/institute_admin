// Arabic labels for the daily-record scales, and a client-side mirror of the
// backend's reward-card scoring so the teacher sees the total update instantly.
// The backend remains authoritative; these are for preview only.

import type { Attitude, DailyRecord, Rating, ScoringSettings } from './api/types';

export const RATING_OPTIONS: { value: Rating; label: string }[] = [
	{ value: 4, label: 'ممتاز' },
	{ value: 3, label: 'جيد جداً' },
	{ value: 2, label: 'جيد' },
	{ value: 1, label: 'ضعيف' }
];

export const ATTITUDE_OPTIONS: { value: Attitude; label: string }[] = [
	{ value: 3, label: 'مؤدب' },
	{ value: 2, label: 'متوسط' },
	{ value: 1, label: 'مشاغب' }
];

export const ADDED_POINTS_OPTIONS = [0, 5, 10, 20, 25, 50, 100];

export function ratingLabel(r: number | null | undefined): string {
	return RATING_OPTIONS.find((o) => o.value === r)?.label ?? '—';
}

export function attitudeLabel(a: number | null | undefined): string {
	return ATTITUDE_OPTIONS.find((o) => o.value === a)?.label ?? '—';
}

const RATING_CARD: Record<number, number> = { 4: 7, 3: 5, 2: 3 };

export function cardPresent(present: boolean): number {
	return present ? 5 : 0;
}

export function cardExam(rating: number | null | undefined): number {
	return rating == null ? 0 : (RATING_CARD[rating] ?? 0);
}

export function cardAttitude(attitude: number | null | undefined): number {
	return attitude ?? 0;
}

/** Preview the reward-card total from the editable fields. */
export function previewTotal(input: {
	present: boolean;
	rating: number | null;
	attitude: number | null;
	added_points: number;
}): number {
	return (
		cardPresent(input.present) +
		cardExam(input.rating) +
		cardAttitude(input.attitude) +
		(input.added_points || 0)
	);
}

export interface CardScores {
	present: number;
	exam: number;
	revision: number;
	attitude: number;
	total: number;
}

/** Reward-card scores using the institute's configured weights (or defaults). */
export function computeScores(
	input: {
		present: boolean;
		excused?: boolean;
		late?: boolean;
		rating: number | null;
		revision_rating?: number | null;
		attitude: number | null;
		added_points: number;
	},
	s: ScoringSettings | null
): CardScores {
	let present: number;
	if (input.present) {
		// «متأخر» is priced separately, defaulting to the on-time weight.
		present = input.late ? (s?.late_points ?? s?.present_points ?? 5) : (s?.present_points ?? 5);
	} else if (input.excused) {
		present = s?.excused_points ?? 0;
	} else {
		present = s?.absent_points ?? 0;
	}
	const ratingMap: Record<number, number> = s
		? { 4: s.rating_4_points, 3: s.rating_3_points, 2: s.rating_2_points, 1: s.rating_1_points }
		: { 4: 7, 3: 5, 2: 3, 1: 0 };
	const exam = input.present && input.rating != null ? (ratingMap[input.rating] ?? 0) : 0;
	const revisionMap: Record<number, number> = s
		? {
				4: s.revision_4_points,
				3: s.revision_3_points,
				2: s.revision_2_points,
				1: s.revision_1_points
			}
		: { 4: 7, 3: 5, 2: 3, 1: 0 };
	const revision =
		input.present && input.revision_rating != null ? (revisionMap[input.revision_rating] ?? 0) : 0;
	const attMap: Record<number, number> = s
		? { 3: s.attitude_3_points, 2: s.attitude_2_points, 1: s.attitude_1_points }
		: { 3: 3, 2: 2, 1: 1 };
	const attitude = input.present && input.attitude != null ? (attMap[input.attitude] ?? 0) : 0;
	return {
		present,
		exam,
		revision,
		attitude,
		total: present + exam + revision + attitude + (input.added_points || 0)
	};
}

// --- Structured revision (المراجعة) --------------------------------------
// The teacher builds a list of revision parts; we serialise them into an Arabic
// message stored in the record's `revision_lesson`, and derive the points:
// all parts succeeded → full revision points (rating 4); any failure → 0 (rating 1).

/** Which portion of a juzʼ was revised: 0 = كله (whole), 1 = النصف الأول, 2 = النصف الثاني. */
export type RevisionHalf = 0 | 1 | 2;

export interface RevisionRow {
	part: number; // 1..30 (جزء)
	half: RevisionHalf;
	success: boolean;
}

export const QURAN_PARTS = Array.from({ length: 30 }, (_, i) => i + 1);

export const HALF_OPTIONS: { value: RevisionHalf; label: string }[] = [
	{ value: 1, label: 'النصف الأول' },
	{ value: 2, label: 'النصف الثاني' },
	{ value: 0, label: 'كله' }
];

export function halfLabel(half: RevisionHalf): string {
	return half === 0 ? 'كله' : half === 1 ? 'النصف الأول' : 'النصف الثاني';
}

/** Serialise revision rows into the Arabic message saved to `revision_lesson`.
 *  Digits are Latin; `parseRevisions` still reads the Arabic-Indic form written by
 *  older app versions. */
export function serializeRevisions(rows: RevisionRow[]): string | null {
	if (rows.length === 0) return null;
	return rows
		.map((r) => `الجزء ${r.part} (${halfLabel(r.half)}): ${r.success ? 'نجح' : 'أخفق'}`)
		.join('، ');
}

function westernNum(s: string): number {
	return Number(s.replace(/[٠-٩]/g, (d) => String('٠١٢٣٤٥٦٧٨٩'.indexOf(d))));
}

/** Best-effort parse of a stored revision message back into editable rows. */
export function parseRevisions(text: string | null | undefined): RevisionRow[] {
	if (!text) return [];
	const rows: RevisionRow[] = [];
	for (const seg of text.split('،')) {
		const m = seg
			.trim()
			.match(/الجزء\s+([٠-٩0-9]+)\s*\((النصف الأول|النصف الثاني|كله)\)\s*:\s*(نجح|أخفق)/);
		if (!m) continue;
		const part = westernNum(m[1]);
		if (part < 1 || part > 30) continue;
		const half: RevisionHalf = m[2] === 'كله' ? 0 : m[2] === 'النصف الأول' ? 1 : 2;
		rows.push({ part, half, success: m[3] === 'نجح' });
	}
	return rows;
}

// --- Structured revision for رشيدي students: مراحل (1..6) instead of أجزاء, no نصف. ---

export interface RashidiRevisionRow {
	stage: number; // 1..6
	success: boolean;
}

/** Serialise رشيدي revision rows into the Arabic message saved to `revision_lesson`. */
export function serializeRashidiRevisions(rows: RashidiRevisionRow[]): string | null {
	if (rows.length === 0) return null;
	return rows.map((r) => `المرحلة ${r.stage}: ${r.success ? 'نجح' : 'أخفق'}`).join('، ');
}

/** Best-effort parse of a stored رشيدي revision message back into editable rows. */
export function parseRashidiRevisions(text: string | null | undefined): RashidiRevisionRow[] {
	if (!text) return [];
	const rows: RashidiRevisionRow[] = [];
	for (const seg of text.split('،')) {
		const m = seg.trim().match(/المرحلة\s+([٠-٩0-9]+)\s*:\s*(نجح|أخفق)/);
		if (!m) continue;
		const stage = westernNum(m[1]);
		if (stage < 1 || stage > 6) continue;
		rows.push({ stage, success: m[2] === 'نجح' });
	}
	return rows;
}

/** A short Arabic summary of attendance for a student's latest record. */
export function recordSummary(r: DailyRecord): string {
	if (!r.present) return r.excused ? 'أذن' : 'غائب';
	const bits: string[] = [];
	if (r.rating) bits.push(ratingLabel(r.rating));
	bits.push(`${r.total_points} نقطة`);
	return bits.join(' · ');
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
