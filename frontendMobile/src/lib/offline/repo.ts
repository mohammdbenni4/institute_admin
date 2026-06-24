// Repository: the single data API the UI uses. Reads are network-first with a cache
// fallback (so everything works offline); writes update the local mirror immediately,
// flag the record dirty, and kick a background sync. The UI never calls the network
// layer (`$lib/api`) directly anymore.

import {
	dailyRecordsApi,
	halaqahsApi,
	problemsApi,
	scoringApi,
	studentsApi,
	type Attitude,
	type DailyRecord,
	type Halaqah,
	type Problem,
	type ProblemBrief,
	type Rating,
	type ScoringSettings,
	type Student
} from '$lib/api';
import { computeScores } from '$lib/labels';
import { db, metaGet, metaSet, type CachedRecord } from './db';
import { net } from './net.svelte';
import { refreshPending } from './state.svelte';
import { isNetworkError, syncNow } from './sync';

const SCORING_KEY = 'scoring.settings';

// ---------------------------------------------------------------- reads ----------

export async function listHalaqahs(teacherId: string): Promise<Halaqah[]> {
	if (net.online) {
		try {
			const res = await halaqahsApi.list({ teacher_id: teacherId, limit: 200 });
			await db.halaqahs.bulkPut(res.items);
			return res.items;
		} catch (e) {
			if (!isNetworkError(e)) throw e;
		}
	}
	return db.halaqahs.where('teacher_id').equals(teacherId).toArray();
}

export async function getHalaqah(id: string): Promise<Halaqah> {
	if (net.online) {
		try {
			const h = await halaqahsApi.get(id);
			await db.halaqahs.put(h);
			return h;
		} catch (e) {
			if (!isNetworkError(e)) throw e;
		}
	}
	const cached = await db.halaqahs.get(id);
	if (!cached) throw new Error('هذه الحلقة غير متوفرة دون اتصال');
	return cached;
}

export async function listStudents(halaqahId: string): Promise<Student[]> {
	if (net.online) {
		try {
			const res = await studentsApi.list({ halaqah_id: halaqahId, limit: 200 });
			await db.students.bulkPut(res.items);
			return res.items;
		} catch (e) {
			if (!isNetworkError(e)) throw e;
		}
	}
	return db.students.where('halaqah_id').equals(halaqahId).toArray();
}

export async function getStudent(id: string): Promise<Student> {
	if (net.online) {
		try {
			const s = await studentsApi.get(id);
			await db.students.put(s);
			return s;
		} catch (e) {
			if (!isNetworkError(e)) throw e;
		}
	}
	const cached = await db.students.get(id);
	if (!cached) throw new Error('بيانات الطالب غير متوفرة دون اتصال');
	return cached;
}

async function cachedScoring(): Promise<ScoringSettings | null> {
	return (await metaGet<ScoringSettings>(SCORING_KEY)) ?? null;
}

export async function getScoring(): Promise<ScoringSettings | null> {
	if (net.online) {
		try {
			const s = await scoringApi.get();
			await metaSet(SCORING_KEY, s);
			return s;
		} catch {
			/* fall through to cache */
		}
	}
	return cachedScoring();
}

export async function listProblems(): Promise<Problem[]> {
	if (net.online) {
		try {
			const res = await problemsApi.list({ limit: 500 });
			await db.problems.clear();
			await db.problems.bulkPut(res.items);
			return res.items;
		} catch {
			/* fall through to cache */
		}
	}
	return db.problems.toArray();
}

async function fetchAllRecords(
	halaqahId: string,
	from: string,
	to: string
): Promise<DailyRecord[]> {
	const PAGE = 200;
	let items: DailyRecord[] = [];
	let offset = 0;
	for (;;) {
		const res = await dailyRecordsApi.list({
			halaqah_id: halaqahId,
			date_from: from,
			date_to: to,
			limit: PAGE,
			offset
		});
		items = items.concat(res.items);
		offset += PAGE;
		if (items.length >= res.total || res.items.length === 0) break;
	}
	return items;
}

/** Upsert server records into the cache, but never clobber un-pushed local edits. */
async function mergeServerRecords(items: DailyRecord[]): Promise<void> {
	for (const srv of items) {
		const existing = await db.records
			.where('[student_id+record_date]')
			.equals([srv.student_id, srv.record_date])
			.first();
		if (existing?.dirty) continue;
		if (existing && existing.id !== srv.id) await db.records.delete(existing.id);
		await db.records.put({ ...srv, dirty: 0, localOnly: 0 });
	}
}

export async function listMonthRecords(
	halaqahId: string,
	from: string,
	to: string
): Promise<DailyRecord[]> {
	if (net.online) {
		try {
			await mergeServerRecords(await fetchAllRecords(halaqahId, from, to));
		} catch (e) {
			if (!isNetworkError(e)) throw e;
		}
	}
	return db.records
		.where('halaqah_id')
		.equals(halaqahId)
		.and((r) => r.record_date >= from && r.record_date <= to)
		.toArray();
}

export async function getDayRecord(studentId: string, date: string): Promise<DailyRecord | null> {
	if (net.online) {
		try {
			const res = await dailyRecordsApi.list({
				student_id: studentId,
				record_date: date,
				limit: 1
			});
			if (res.items[0]) await mergeServerRecords([res.items[0]]);
		} catch (e) {
			if (!isNetworkError(e)) throw e;
		}
	}
	const cached = await db.records
		.where('[student_id+record_date]')
		.equals([studentId, date])
		.first();
	return cached ?? null;
}

// --------------------------------------------------------------- writes ----------

export interface UpsertInput {
	student_id: string;
	teacher_id: string;
	halaqah_id: string;
	record_date: string;
	present?: boolean;
	excused?: boolean;
	exam_from?: number | null;
	exam_to?: number | null;
	exam_total?: number | null;
	homework?: string | null;
	problems?: string | null;
	rating?: Rating | null;
	revision_lesson?: string | null;
	revision_rating?: Rating | null;
	attitude?: Attitude | null;
	added_points?: number | null;
	notes?: string | null;
	problem_ids?: string[];
}

async function tagsFor(ids: string[]): Promise<ProblemBrief[]> {
	if (ids.length === 0) return [];
	const probs = await db.problems.bulkGet(ids);
	return probs
		.filter((p): p is Problem => !!p)
		.map((p) => ({ id: p.id, name: p.name, level_id: p.level_id, level_name: p.level_name }));
}

/** Optimistic reward-card totals using the cached scoring policy (server is authoritative). */
function applyOptimisticScores(rec: CachedRecord, scoring: ScoringSettings | null): void {
	const s = computeScores(
		{
			present: rec.present,
			excused: rec.excused,
			rating: rec.rating,
			revision_rating: rec.revision_rating,
			attitude: rec.attitude,
			added_points: rec.added_points ?? 0
		},
		scoring
	);
	rec.card_present = s.present;
	rec.card_exam = s.exam;
	rec.card_revision = s.revision;
	rec.card_attitude = s.attitude;
	rec.total_points = s.total;
}

function blankRecord(input: UpsertInput, now: string): CachedRecord {
	return {
		id: `local:${crypto.randomUUID()}`,
		student_id: input.student_id,
		teacher_id: input.teacher_id,
		halaqah_id: input.halaqah_id,
		record_date: input.record_date,
		present: true,
		excused: false,
		exam_from: null,
		exam_to: null,
		exam_total: null,
		homework: null,
		problems: null,
		rating: null,
		revision_lesson: null,
		revision_rating: null,
		attitude: null,
		added_points: 0,
		notes: null,
		tagged_problems: [],
		card_present: 0,
		card_exam: 0,
		card_revision: 0,
		card_attitude: 0,
		total_points: 0,
		created_at: now,
		updated_at: now,
		dirty: 1,
		localOnly: 1
	};
}

async function buildCachedRecord(
	existing: CachedRecord | undefined,
	input: UpsertInput
): Promise<CachedRecord> {
	const now = new Date().toISOString();
	const base = existing ?? blankRecord(input, now);
	const pick = <T>(v: T | undefined, fallback: T): T => (v !== undefined ? v : fallback);

	const rec: CachedRecord = {
		...base,
		present: pick(input.present, base.present),
		excused: pick(input.excused, base.excused),
		exam_from: pick(input.exam_from, base.exam_from),
		exam_to: pick(input.exam_to, base.exam_to),
		exam_total: pick(input.exam_total, base.exam_total),
		homework: pick(input.homework, base.homework),
		problems: pick(input.problems, base.problems),
		rating: pick(input.rating, base.rating),
		revision_lesson: pick(input.revision_lesson, base.revision_lesson),
		revision_rating: pick(input.revision_rating, base.revision_rating),
		attitude: pick(input.attitude, base.attitude),
		added_points: pick(input.added_points, base.added_points) ?? 0,
		notes: pick(input.notes, base.notes),
		updated_at: now,
		dirty: 1,
		localOnly: existing ? existing.localOnly : 1
	};

	if (input.problem_ids !== undefined) {
		rec.problem_ids = input.problem_ids;
		rec.tagged_problems = await tagsFor(input.problem_ids);
	} else {
		rec.problem_ids = base.problem_ids ?? base.tagged_problems.map((p) => p.id);
	}

	applyOptimisticScores(rec, await cachedScoring());
	return rec;
}

/** Create-or-update a daily record by its natural key (student, date). */
export async function upsertDailyRecord(input: UpsertInput): Promise<CachedRecord> {
	const existing = await db.records
		.where('[student_id+record_date]')
		.equals([input.student_id, input.record_date])
		.first();
	const rec = await buildCachedRecord(existing, input);
	await db.records.put(rec);
	await refreshPending();
	void syncNow();
	return rec;
}

export interface AttendanceInput {
	halaqah_id: string;
	teacher_id: string;
	record_date: string;
	entries: { student_id: string; present: boolean; excused: boolean }[];
}

/** Mark attendance for a whole halaqah (keeps each record's assessment fields). */
export async function setAttendance(input: AttendanceInput): Promise<void> {
	for (const e of input.entries) {
		const existing = await db.records
			.where('[student_id+record_date]')
			.equals([e.student_id, input.record_date])
			.first();
		const rec = await buildCachedRecord(existing, {
			student_id: e.student_id,
			teacher_id: input.teacher_id,
			halaqah_id: input.halaqah_id,
			record_date: input.record_date,
			present: e.present,
			excused: e.excused
		});
		await db.records.put(rec);
	}
	await refreshPending();
	void syncNow();
}
