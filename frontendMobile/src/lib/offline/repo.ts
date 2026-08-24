// Repository: the single data API the UI uses.
//
// Reads are *cache-first with background revalidation*: they answer from the local
// mirror immediately and report fresh server data through `ReadOpts.onFresh`. (They
// used to be network-first, which meant a stalled connection cost a full timeout per
// call and the app appeared frozen.) Writes update the mirror, flag the record dirty
// and kick a background sync. The UI never calls `$lib/api` directly.

import {
	dailyRecordsApi,
	halaqahsApi,
	networkLooksDown,
	parentSummonsApi,
	problemsApi,
	scoringApi,
	scoringPresetsApi,
	studentsApi,
	type Attitude,
	type DailyRecord,
	type Halaqah,
	type Problem,
	type ProblemBrief,
	type Rating,
	type ParentSummon,
	type ScoringPreset,
	type ScoringSettings,
	type Student,
	type StudentUpdate
} from '$lib/api';
import { computeScores } from '$lib/labels';
import {
	db,
	metaGet,
	metaSet,
	type CachedHalaqah,
	type CachedRecord,
	type RecordBaseline
} from './db';
import { net } from './net.svelte';
import { refreshPending } from './state.svelte';
import { isNetworkError, syncNow } from './sync';

const SCORING_KEY = 'scoring.settings';
const SCORING_PRESETS_KEY = 'scoring.presets';
// Last-seen summons list, so the panel still renders something offline.
const SUMMONS_KEY = 'summons.list';

// ------------------------------------------------------- read-through core -------

/**
 * Options every read accepts.
 *
 * `onFresh` is what makes the app usable on a weak connection: the call returns the
 * cached copy *immediately* and, if the network later answers, hands the fresh data
 * back through this callback so the page updates in place. Nothing ever blocks on a
 * request that is going to time out.
 */
export interface ReadOpts<T> {
	/** Called with server data when a background refresh succeeds (never on cache hits). */
	onFresh?: (value: T) => void;
	/** Wait for the server instead of answering from cache (the manual «تحديث» button). */
	force?: boolean;
}

/** Should we even try the network right now? */
function canReachNetwork(): boolean {
	return net.online && !networkLooksDown();
}

/**
 * Cache-first read with background revalidation.
 *
 * - cache hit  → return it now, refresh in the background, report via `onFresh`
 * - cache miss → await the network (there is nothing to show otherwise)
 * - offline    → cache only
 *
 * Reads used to be network-*first*, so on a stalled connection every call paid the
 * full timeout before falling back and the whole screen sat on a spinner.
 */
async function readThrough<T>(
	load: () => Promise<T>,
	fetchRemote: () => Promise<T>,
	store: (value: T) => Promise<void>,
	isUsable: (value: T) => boolean,
	opts: ReadOpts<T> = {}
): Promise<T> {
	const cached = await load();
	const wantNetwork = opts.force || !isUsable(cached);

	if (!canReachNetwork()) {
		if (opts.force && !net.online) return cached;
		return cached;
	}

	if (wantNetwork) {
		try {
			const fresh = await fetchRemote();
			await store(fresh);
			return await load();
		} catch (e) {
			if (!isNetworkError(e)) throw e;
			return cached; // network died — the cache is the best we have
		}
	}

	// Usable cache: answer now, catch up in the background.
	void (async () => {
		try {
			const fresh = await fetchRemote();
			await store(fresh);
			opts.onFresh?.(await load());
		} catch {
			/* background refresh is best-effort */
		}
	})();
	return cached;
}

/** Flatten a halaqah's membership into the plain string array Dexie can index. */
function toCachedHalaqah(h: Halaqah): CachedHalaqah {
	return { ...h, teacher_ids: (h.teachers ?? []).map((t) => t.id) };
}

// ---------------------------------------------------------------- reads ----------

export async function listHalaqahs(
	teacherId: string,
	opts: ReadOpts<Halaqah[]> = {}
): Promise<Halaqah[]> {
	return readThrough(
		// `teacher_ids` (multiEntry), not `teacher_id`: the latter is only the responsible
		// teacher, so an assisting teacher would find nothing here while offline.
		() => db.halaqahs.where('teacher_ids').equals(teacherId).toArray(),
		async () => (await halaqahsApi.list({ teacher_id: teacherId, limit: 200 })).items,
		(items) => db.halaqahs.bulkPut(items.map(toCachedHalaqah)).then(() => undefined),
		(items) => items.length > 0,
		opts
	);
}

export async function getHalaqah(id: string, opts: ReadOpts<Halaqah> = {}): Promise<Halaqah> {
	const result = await readThrough(
		() => db.halaqahs.get(id),
		() => halaqahsApi.get(id),
		async (h) => {
			if (h) await db.halaqahs.put(toCachedHalaqah(h));
		},
		(h) => h != null,
		opts as ReadOpts<Halaqah | undefined>
	);
	if (!result) throw new Error('هذه الحلقة غير متوفرة دون اتصال');
	return result;
}

export async function listStudents(
	halaqahId: string,
	opts: ReadOpts<Student[]> = {}
): Promise<Student[]> {
	return readThrough(
		() => db.students.where('halaqah_id').equals(halaqahId).toArray(),
		async () => (await studentsApi.list({ halaqah_id: halaqahId, limit: 200 })).items,
		async (items) => {
			// Students removed from the halaqah server-side must disappear locally too,
			// otherwise the roster only ever grows.
			const keep = new Set(items.map((s) => s.id));
			const stale = (await db.students.where('halaqah_id').equals(halaqahId).toArray())
				.filter((s) => !keep.has(s.id))
				.map((s) => s.id);
			if (stale.length) await db.students.bulkDelete(stale);
			await db.students.bulkPut(items);
		},
		(items) => items.length > 0,
		opts
	);
}

export async function getStudent(id: string, opts: ReadOpts<Student> = {}): Promise<Student> {
	const result = await readThrough(
		() => db.students.get(id),
		() => studentsApi.get(id),
		async (s) => {
			if (s) await db.students.put(s);
		},
		(s) => s != null,
		opts as ReadOpts<Student | undefined>
	);
	if (!result) throw new Error('بيانات الطالب غير متوفرة دون اتصال');
	return result;
}

async function cachedScoring(): Promise<ScoringSettings | null> {
	return (await metaGet<ScoringSettings>(SCORING_KEY)) ?? null;
}

export async function getScoring(opts: ReadOpts<ScoringSettings | null> = {}) {
	return readThrough(
		cachedScoring,
		() => scoringApi.get(),
		(s) => (s ? metaSet(SCORING_KEY, s) : Promise.resolve()),
		(s) => s != null,
		opts
	);
}

async function cachedScoringPresets(): Promise<ScoringPreset[]> {
	return (await metaGet<ScoringPreset[]>(SCORING_PRESETS_KEY)) ?? [];
}

/** Named pricing systems assignable to a student in halaqah settings (see `updateStudent`). */
export async function listScoringPresets(
	opts: ReadOpts<ScoringPreset[]> = {}
): Promise<ScoringPreset[]> {
	return readThrough(
		cachedScoringPresets,
		async () => (await scoringPresetsApi.list()).items,
		(items) => metaSet(SCORING_PRESETS_KEY, items),
		(items) => items.length > 0,
		opts
	);
}

/** The config that actually prices a student's points: their assigned preset (from cache)
 *  falling back to the halaqah's single default scoring — mirrors `scoringFor` in the mock
 *  server so the optimistic local total matches what the server will compute. */
export async function getScoringForStudent(studentId: string): Promise<ScoringSettings | null> {
	const student = await db.students.get(studentId);
	if (student?.scoring_preset_id) {
		const preset = (await cachedScoringPresets()).find((p) => p.id === student.scoring_preset_id);
		if (preset) return preset;
	}
	return cachedScoring();
}

/** Update a student's track (رشيدي/قرآن) and/or assigned pricing preset. Requires a live
 *  connection — unlike daily records, this settings edit has no offline queue. */
export async function updateStudent(id: string, patch: StudentUpdate): Promise<Student> {
	if (!canReachNetwork()) throw new Error('يتطلب هذا التغيير اتصالاً بالإنترنت');
	const updated = await studentsApi.update(id, patch);
	await db.students.put(updated);
	return updated;
}

export async function listProblems(opts: ReadOpts<Problem[]> = {}): Promise<Problem[]> {
	return readThrough(
		() => db.problems.toArray(),
		async () => (await problemsApi.list({ limit: 500 })).items,
		async (items) => {
			await db.problems.clear();
			await db.problems.bulkPut(items);
		},
		(items) => items.length > 0,
		opts
	);
}

/** Page through the list endpoint (the API caps `limit` at 200). */
async function fetchAllRecords(query: {
	halaqah_id?: string;
	student_id?: string;
	date_from: string;
	date_to: string;
}): Promise<DailyRecord[]> {
	const PAGE = 200;
	let items: DailyRecord[] = [];
	let offset = 0;
	for (;;) {
		const res = await dailyRecordsApi.list({ ...query, limit: PAGE, offset });
		items = items.concat(res.items);
		offset += PAGE;
		if (items.length >= res.total || res.items.length === 0) break;
	}
	return items;
}

/** Upsert server records into the cache, but never clobber un-pushed local edits.
 *  One bulk read + one bulk write instead of two round-trips per record — this used
 *  to be the slowest part of opening a halaqah with a full month of history. */
async function mergeServerRecords(items: DailyRecord[]): Promise<void> {
	if (items.length === 0) return;
	// A record queued for deletion may still show up in a server response that was
	// in flight before the delete reached it — without this, a background refresh
	// could resurrect a record the teacher just deleted.
	const pendingDeleteIds = new Set((await db.pendingDeletes.toArray()).map((d) => d.id));
	const keys = items.map((r) => [r.student_id, r.record_date] as [string, string]);
	const existing = await db.records.where('[student_id+record_date]').anyOf(keys).toArray();
	const byKey = new Map(existing.map((r) => [`${r.student_id}|${r.record_date}`, r]));

	const toPut: CachedRecord[] = [];
	const toDelete: string[] = [];
	for (const srv of items) {
		if (pendingDeleteIds.has(srv.id)) continue;
		const prev = byKey.get(`${srv.student_id}|${srv.record_date}`);
		if (prev?.dirty) continue; // local edit wins until it is pushed
		if (prev && prev.id !== srv.id) toDelete.push(prev.id);
		toPut.push({ ...srv, dirty: 0, localOnly: 0 });
	}
	if (toDelete.length) await db.records.bulkDelete(toDelete);
	if (toPut.length) await db.records.bulkPut(toPut);
}

/** Marker proving a date window was fetched at least once, so an empty month is
 *  served from cache instead of re-hitting the network on every visit. */
function rangeKey(scope: string, id: string, from: string, to: string): string {
	return `range.${scope}.${id}.${from}..${to}`;
}

export async function listMonthRecords(
	halaqahId: string,
	from: string,
	to: string,
	opts: ReadOpts<DailyRecord[]> = {}
): Promise<DailyRecord[]> {
	const key = rangeKey('halaqah', halaqahId, from, to);
	let fetched = (await metaGet<number>(key)) != null;
	return readThrough(
		() =>
			db.records
				.where('halaqah_id')
				.equals(halaqahId)
				.and((r) => r.record_date >= from && r.record_date <= to)
				.toArray(),
		() => fetchAllRecords({ halaqah_id: halaqahId, date_from: from, date_to: to }),
		async (items) => {
			await mergeServerRecords(items);
			await metaSet(key, Date.now());
			fetched = true;
		},
		() => fetched,
		opts
	);
}

/** All of one student's records in a date window. Used to surface a student's most
 *  recent recitation/homework even when it falls in an earlier month. */
export async function listStudentRecords(
	studentId: string,
	from: string,
	to: string,
	opts: ReadOpts<DailyRecord[]> = {}
): Promise<DailyRecord[]> {
	const key = rangeKey('student', studentId, from, to);
	let fetched = (await metaGet<number>(key)) != null;
	return readThrough(
		() =>
			db.records
				.where('student_id')
				.equals(studentId)
				.and((r) => r.record_date >= from && r.record_date <= to)
				.toArray(),
		() => fetchAllRecords({ student_id: studentId, date_from: from, date_to: to }),
		async (items) => {
			await mergeServerRecords(items);
			await metaSet(key, Date.now());
			fetched = true;
		},
		() => fetched,
		opts
	);
}

/** A student's most recent recitation and the homework they were last assigned. */
export interface LatestRecitation {
	record: DailyRecord | null;
	homework: string | null;
}

/** Does this record represent a recitation (exam range/total, rating, or revision)? */
function hasRecitation(r: DailyRecord): boolean {
	return (
		r.rating != null ||
		r.exam_from != null ||
		r.exam_to != null ||
		r.exam_total != null ||
		!!r.revision_lesson
	);
}

/** Compute «آخر تسميع» + «آخر واجب» from whatever is in the local mirror. */
async function latestFromCache(
	studentIds: string[],
	before?: string
): Promise<Map<string, LatestRecitation>> {
	const out = new Map<string, LatestRecitation>();
	for (const id of studentIds) {
		const rows = (await db.records.where('student_id').equals(id).toArray())
			.filter((r) => (before ? r.record_date < before : true))
			.sort((a, b) => b.record_date.localeCompare(a.record_date));
		out.set(id, {
			record: rows.find(hasRecitation) ?? null,
			homework: rows.find((r) => r.homework && r.homework.trim() !== '')?.homework ?? null
		});
	}
	return out;
}

/**
 * Per-student last recitation + last homework, with **no date window**.
 *
 * The screens used to derive this from a fixed three-month fetch, so a student who
 * had been absent longer than that showed «لم يُسجّل تسميع بعد» even though they had
 * a history. The server answers straight from the whole table; offline we fall back
 * to the local mirror.
 */
export async function latestRecitations(
	studentIds: string[],
	before?: string
): Promise<Map<string, LatestRecitation>> {
	if (studentIds.length === 0) return new Map();
	if (canReachNetwork()) {
		try {
			const res = await dailyRecordsApi.latestRecitations(studentIds, before);
			// Fold the server's answer into the cache so the offline path matches.
			await mergeServerRecords(
				res.items.map((i) => i.last_recitation).filter((r): r is DailyRecord => r != null)
			);
			return new Map(
				res.items.map((i) => [i.student_id, { record: i.last_recitation, homework: i.homework }])
			);
		} catch (e) {
			if (!isNetworkError(e)) throw e;
		}
	}
	return latestFromCache(studentIds, before);
}

export async function getDayRecord(
	studentId: string,
	date: string,
	opts: ReadOpts<DailyRecord | null> = {}
): Promise<DailyRecord | null> {
	const key = rangeKey('day', studentId, date, date);
	let fetched = (await metaGet<number>(key)) != null;
	return readThrough(
		async () =>
			(await db.records.where('[student_id+record_date]').equals([studentId, date]).first()) ??
			null,
		async () =>
			(await dailyRecordsApi.list({ student_id: studentId, record_date: date, limit: 1 }))
				.items[0] ?? null,
		async (rec) => {
			if (rec) await mergeServerRecords([rec]);
			await metaSet(key, Date.now());
			fetched = true;
		},
		() => fetched,
		opts
	);
}

// --------------------------------------------------------------- writes ----------

export interface UpsertInput {
	student_id: string;
	teacher_id: string;
	halaqah_id: string;
	record_date: string;
	present?: boolean;
	excused?: boolean;
	late?: boolean;
	excuse_reason?: string | null;
	exam_from?: number | null;
	exam_to?: number | null;
	exam_from_line?: number | null;
	exam_to_line?: number | null;
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
			late: rec.late,
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

/** UUID with a fallback (crypto.randomUUID needs a secure context, which a WebView may lack). */
function uid(): string {
	const c = globalThis.crypto;
	if (c?.randomUUID) return c.randomUUID();
	if (c?.getRandomValues) {
		const b = c.getRandomValues(new Uint8Array(16));
		b[6] = (b[6] & 0x0f) | 0x40;
		b[8] = (b[8] & 0x3f) | 0x80;
		const h = [...b].map((x) => x.toString(16).padStart(2, '0')).join('');
		return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`;
	}
	return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function blankRecord(input: UpsertInput, now: string): CachedRecord {
	return {
		id: `local:${uid()}`,
		student_id: input.student_id,
		teacher_id: input.teacher_id,
		halaqah_id: input.halaqah_id,
		record_date: input.record_date,
		present: true,
		excused: false,
		late: false,
		excuse_reason: null,
		exam_from: null,
		exam_to: null,
		exam_from_line: null,
		exam_to_line: null,
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

/** Snapshot the editable fields as the "before" baseline for a change diff. */
function snapshotBaseline(r: DailyRecord): RecordBaseline {
	return {
		present: r.present,
		excused: r.excused,
		late: r.late,
		excuse_reason: r.excuse_reason,
		exam_from: r.exam_from,
		exam_to: r.exam_to,
		exam_from_line: r.exam_from_line,
		exam_to_line: r.exam_to_line,
		exam_total: r.exam_total,
		homework: r.homework,
		problems: r.problems,
		rating: r.rating,
		revision_lesson: r.revision_lesson,
		revision_rating: r.revision_rating,
		attitude: r.attitude,
		added_points: r.added_points,
		notes: r.notes
	};
}

async function buildCachedRecord(
	existing: CachedRecord | undefined,
	input: UpsertInput,
	scoring?: ScoringSettings | null
): Promise<CachedRecord> {
	const now = new Date().toISOString();
	const base = existing ?? blankRecord(input, now);
	const pick = <T>(v: T | undefined, fallback: T): T => (v !== undefined ? v : fallback);

	// Capture the server "before" state the first time a clean record is edited;
	// keep the original snapshot across further edits; null for locally-created rows.
	let baseline: RecordBaseline | null;
	if (!existing) baseline = null;
	else if (existing.dirty === 0) baseline = snapshotBaseline(existing);
	else baseline = existing.baseline ?? null;

	const rec: CachedRecord = {
		...base,
		present: pick(input.present, base.present),
		excused: pick(input.excused, base.excused),
		late: pick(input.late, base.late),
		excuse_reason: pick(input.excuse_reason, base.excuse_reason),
		exam_from: pick(input.exam_from, base.exam_from),
		exam_to: pick(input.exam_to, base.exam_to),
		exam_from_line: pick(input.exam_from_line, base.exam_from_line),
		exam_to_line: pick(input.exam_to_line, base.exam_to_line),
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
		localOnly: existing ? existing.localOnly : 1,
		baseline,
		// The teacher just changed something, so give the server another chance.
		syncError: null
	};

	if (input.problem_ids !== undefined) {
		rec.problem_ids = input.problem_ids;
		rec.tagged_problems = await tagsFor(input.problem_ids);
	} else {
		rec.problem_ids = base.problem_ids ?? base.tagged_problems.map((p) => p.id);
	}

	applyOptimisticScores(
		rec,
		scoring !== undefined ? scoring : await getScoringForStudent(rec.student_id)
	);
	return rec;
}

/** Deep plain copy — strips Svelte `$state` proxies (e.g. `form.problem_ids`), which
 * IndexedDB's structured-clone can't serialise (DataCloneError otherwise). */
function toPlain<T>(value: T): T {
	return JSON.parse(JSON.stringify(value)) as T;
}

/** Write a record, guaranteeing the unique [student_id+record_date] key isn't doubly
 * occupied (reuse the existing row's id so `put` updates instead of colliding). */
async function commitRecord(rec: CachedRecord): Promise<void> {
	const dup = await db.records
		.where('[student_id+record_date]')
		.equals([rec.student_id, rec.record_date])
		.first();
	if (dup && dup.id !== rec.id) {
		rec.id = dup.id;
		rec.localOnly = dup.localOnly;
		rec.created_at = dup.created_at;
	}
	await db.records.put(toPlain(rec));
}

/** Create-or-update a daily record by its natural key (student, date). */
export async function upsertDailyRecord(input: UpsertInput): Promise<CachedRecord> {
	const existing = await db.records
		.where('[student_id+record_date]')
		.equals([input.student_id, input.record_date])
		.first();
	const rec = await buildCachedRecord(existing, input);
	await commitRecord(rec);
	await refreshPending();
	void syncNow();
	return rec;
}

export interface AttendanceInput {
	halaqah_id: string;
	teacher_id: string;
	record_date: string;
	entries: {
		student_id: string;
		present: boolean;
		excused: boolean;
		late: boolean;
		excuse_reason: string | null;
	}[];
}

/** Mark attendance for a whole halaqah (keeps each record's assessment fields).
 *  Reads and writes the whole class in two bulk operations rather than a pair of
 *  IndexedDB round-trips per student — noticeably faster on a large halaqah. */
export async function setAttendance(input: AttendanceInput): Promise<void> {
	const keys = input.entries.map((e) => [e.student_id, input.record_date] as [string, string]);
	const existing = await db.records.where('[student_id+record_date]').anyOf(keys).toArray();
	const byStudent = new Map(existing.map((r) => [r.student_id, r]));

	const rows: CachedRecord[] = [];
	for (const e of input.entries) {
		// Resolved per student (not hoisted) — each may carry a different pricing preset.
		rows.push(
			await buildCachedRecord(byStudent.get(e.student_id), {
				student_id: e.student_id,
				teacher_id: input.teacher_id,
				halaqah_id: input.halaqah_id,
				record_date: input.record_date,
				present: e.present,
				excused: e.excused,
				late: e.late,
				excuse_reason: e.excuse_reason
			})
		);
	}
	await db.records.bulkPut(rows.map(toPlain));
	await refreshPending();
	void syncNow();
}

/** Discard a single un-uploaded change: delete locally-created rows, or revert an
 * edited row to the server's version (online) / its captured baseline (offline).
 * Only this record is affected; other pending changes are left untouched. */
export async function discardChange(id: string): Promise<void> {
	const rec = await db.records.get(id);
	if (!rec) return;

	if (rec.localOnly) {
		await db.records.delete(id);
	} else if (net.online) {
		try {
			const res = await dailyRecordsApi.list({
				student_id: rec.student_id,
				record_date: rec.record_date,
				limit: 1
			});
			const srv = res.items[0];
			await db.records.delete(id);
			if (srv) await db.records.put({ ...srv, dirty: 0, localOnly: 0 });
		} catch (e) {
			if (!isNetworkError(e)) throw e;
			await restoreFromBaseline(rec); // lost connection mid-way — fall back to the snapshot
		}
	} else {
		await restoreFromBaseline(rec);
	}
	await refreshPending();
}

/**
 * Un-mark a student's attendance for a day that already had a saved record: the
 * record is dropped locally right away, and — unless it only ever existed on this
 * device — queued for the server to drop it too on the next sync.
 */
export async function deleteRecord(id: string): Promise<void> {
	const rec = await db.records.get(id);
	if (!rec) return;
	await db.records.delete(id);
	if (!rec.localOnly) {
		await db.pendingDeletes.put({ id: rec.id, created_at: new Date().toISOString() });
	}
	await refreshPending();
	void syncNow();
}

/** Roll a dirty record back to its captured baseline (server values) and mark it clean. */
async function restoreFromBaseline(rec: CachedRecord): Promise<void> {
	if (rec.baseline) {
		Object.assign(rec, rec.baseline);
		applyOptimisticScores(rec, await getScoringForStudent(rec.student_id));
	}
	rec.dirty = 0;
	rec.baseline = null;
	await db.records.put(toPlain(rec));
}

// ------------------------------------------------- استدعاء ولي الأمر -------------

/** A summons the teacher raised, whether it has reached the server yet or not.
 *  Queued requests are shown with a «قيد الإرسال» status so the teacher can see
 *  their request exists even before it uploads. */
export interface SummonEntry {
	id: string;
	studentName: string;
	halaqahName: string;
	reason: string;
	statusLabel: string;
	status: 'queued' | ParentSummon['status'];
	adminResponse: string | null;
	createdAt: string;
	/** true = still in the outbox, not yet accepted by the server. */
	queued: boolean;
}

/**
 * Raise a «استدعاء ولي الأمر».
 *
 * Written to the outbox first and uploaded by the sync engine, so a teacher in a
 * classroom with no signal can still file one. Returns immediately.
 */
export async function requestParentSummon(input: {
	student_id: string;
	student_name: string;
	halaqah_id: string;
	reason: string;
}): Promise<void> {
	await db.pendingSummons.put({
		id: `local:${uid()}`,
		student_id: input.student_id,
		student_name: input.student_name,
		halaqah_id: input.halaqah_id,
		reason: input.reason.trim(),
		created_at: new Date().toISOString()
	});
	await refreshPending();
	void syncNow();
}

/** The teacher's own requests: everything queued locally, then the server's list. */
export async function listSummons(): Promise<SummonEntry[]> {
	const queued = await db.pendingSummons.orderBy('created_at').reverse().toArray();
	const local: SummonEntry[] = queued.map((q) => ({
		id: q.id,
		studentName: q.student_name,
		halaqahName: '',
		reason: q.reason,
		status: 'queued',
		statusLabel: 'قيد الإرسال',
		adminResponse: null,
		createdAt: q.created_at,
		queued: true
	}));

	let remote: SummonEntry[] = [];
	if (canReachNetwork()) {
		try {
			const res = await parentSummonsApi.list({ limit: 100 });
			remote = res.items.map((s) => ({
				id: s.id,
				studentName: s.student_name,
				halaqahName: s.halaqah_name,
				reason: s.reason,
				status: s.status,
				statusLabel: s.status_label,
				adminResponse: s.admin_response,
				createdAt: s.created_at,
				queued: false
			}));
			await metaSet(SUMMONS_KEY, remote);
		} catch (e) {
			if (!isNetworkError(e)) throw e;
			remote = (await metaGet<SummonEntry[]>(SUMMONS_KEY)) ?? [];
		}
	} else {
		remote = (await metaGet<SummonEntry[]>(SUMMONS_KEY)) ?? [];
	}
	return [...local, ...remote];
}
