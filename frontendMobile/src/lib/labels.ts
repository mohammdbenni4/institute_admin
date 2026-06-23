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

export const ADDED_POINTS_OPTIONS = [0, 5, 10, 15, 20];

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
		rating: number | null;
		revision_rating?: number | null;
		attitude: number | null;
		added_points: number;
	},
	s: ScoringSettings | null
): CardScores {
	let present: number;
	if (input.present) {
		present = s?.present_points ?? 5;
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

/** A short Arabic summary of attendance for a student's latest record. */
export function recordSummary(r: DailyRecord): string {
	if (!r.present) return r.excused ? 'أذن' : 'غائب';
	const bits: string[] = [];
	if (r.rating) bits.push(ratingLabel(r.rating));
	bits.push(`${r.total_points} نقطة`);
	return bits.join(' · ');
}
