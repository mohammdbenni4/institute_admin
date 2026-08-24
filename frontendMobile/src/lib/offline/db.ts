// On-device cache (IndexedDB via Dexie). Holds a mirror of the teacher's data so
// the app reads from here when offline, plus a "dirty" flag per daily-record that
// marks local edits awaiting upload. See [sync.ts] for the push engine.

import Dexie, { type Table } from 'dexie';
import type { DailyRecord, Halaqah, Problem, Student } from '$lib/api';

/** A halaqah in the cache, with its membership flattened for the multiEntry index.
 *  Dexie can only index a plain array of keys, not `teachers[].id`. */
export interface CachedHalaqah extends Halaqah {
	teacher_ids: string[];
}

/** The editable fields captured before local edits began (server truth), used to
 * show an old→new diff and to revert a single un-uploaded change. `null` = the
 * record was created locally and has no server-side "before" state. */
export type RecordBaseline = Pick<
	DailyRecord,
	| 'present'
	| 'excused'
	| 'late'
	| 'excuse_reason'
	| 'exam_from'
	| 'exam_to'
	| 'exam_from_line'
	| 'exam_to_line'
	| 'exam_total'
	| 'homework'
	| 'problems'
	| 'rating'
	| 'revision_lesson'
	| 'revision_rating'
	| 'attitude'
	| 'added_points'
	| 'notes'
>;

/** A daily record in the cache, with sync bookkeeping. */
export interface CachedRecord extends DailyRecord {
	/** 1 = has local changes not yet pushed to the server. */
	dirty: 0 | 1;
	/** 1 = created offline; no confirmed server id yet (id is a `local:` placeholder). */
	localOnly: 0 | 1;
	/** Selected difficulty ids for the next push (server returns `tagged_problems`). */
	problem_ids?: string[];
	/** Server values before the current un-pushed edits (null for locally-created records). */
	baseline?: RecordBaseline | null;
	/**
	 * Why the server refused this record, in Arabic.
	 *
	 * A rejected record is *not* retried until the teacher edits it — replaying a
	 * payload the server has already judged invalid just fails identically every
	 * 60 seconds and leaves the outbox permanently stuck. Editing (or an explicit
	 * retry) clears this and puts it back in the queue.
	 */
	syncError?: string | null;
}

export interface MetaRow {
	key: string;
	value: unknown;
}

/** A daily record deleted on the device, waiting for the server to drop it too.
 *  Deletes are never edited, so — like summons — it's a fire-and-forget outbox. */
export interface PendingDelete {
	/** The server's record id (a `local:` row is dropped locally and never queued here). */
	id: string;
	created_at: string;
}

/** A «استدعاء ولي الأمر» raised on the device, waiting to reach the server.
 *
 *  Requests get their own outbox rather than riding on the daily-record one: they
 *  are created, never edited, so "send once and forget" is the whole lifecycle. */
export interface PendingSummon {
	/** Client-generated id; the server assigns its own on acceptance. */
	id: string;
	student_id: string;
	student_name: string;
	halaqah_id: string;
	reason: string;
	created_at: string;
	/** Set when the server rejected it outright, so the teacher can see why. */
	error?: string | null;
}

class TeacherDB extends Dexie {
	halaqahs!: Table<CachedHalaqah, string>;
	students!: Table<Student, string>;
	records!: Table<CachedRecord, string>;
	problems!: Table<Problem, string>;
	meta!: Table<MetaRow, string>;
	pendingSummons!: Table<PendingSummon, string>;
	pendingDeletes!: Table<PendingDelete, string>;

	constructor() {
		super('teacher-offline');
		this.version(1).stores({
			halaqahs: 'id, teacher_id',
			students: 'id, halaqah_id',
			// `&[student_id+record_date]` mirrors the server's UNIQUE(student, date) so
			// records upsert by natural key — no server id needed for offline writes.
			records: 'id, &[student_id+record_date], student_id, halaqah_id, record_date, dirty',
			problems: 'id',
			meta: 'key'
		});
		// v2 adds the summons outbox. Dexie migrates existing installs in place; the
		// tables above are repeated because a version's schema is the full picture.
		this.version(2).stores({
			halaqahs: 'id, teacher_id',
			students: 'id, halaqah_id',
			records: 'id, &[student_id+record_date], student_id, halaqah_id, record_date, dirty',
			problems: 'id',
			meta: 'key',
			pendingSummons: 'id, created_at'
		});
		// v3 adds the record-deletion outbox (un-marking an attendance status that had
		// already been saved).
		this.version(3).stores({
			halaqahs: 'id, teacher_id',
			students: 'id, halaqah_id',
			records: 'id, &[student_id+record_date], student_id, halaqah_id, record_date, dirty',
			problems: 'id',
			meta: 'key',
			pendingSummons: 'id, created_at',
			pendingDeletes: 'id, created_at'
		});
		// v4: a halaqah now has many teachers. `teacher_id` still names the responsible
		// one, so looking a teacher's halaqahs up by it would hide every halaqah they
		// merely assist with — invisible offline while working fine online, the worst
		// kind of bug. `*teacher_ids` is a multiEntry index: one entry per member, so
		// `.where('teacher_ids').equals(id)` finds a halaqah for any of its teachers.
		this.version(4)
			.stores({
				halaqahs: 'id, teacher_id, *teacher_ids',
				students: 'id, halaqah_id',
				records: 'id, &[student_id+record_date], student_id, halaqah_id, record_date, dirty',
				problems: 'id',
				meta: 'key',
				pendingSummons: 'id, created_at',
				pendingDeletes: 'id, created_at'
			})
			.upgrade(async (tx) => {
				// Existing cached halaqahs predate `teachers`; seed membership from the
				// responsible teacher so an offline upgrade keeps showing them until the
				// next successful refresh replaces them with the server's full list.
				await tx
					.table('halaqahs')
					.toCollection()
					.modify((h: { teacher_id?: string; teacher_ids?: string[] }) => {
						if (!h.teacher_ids?.length && h.teacher_id) h.teacher_ids = [h.teacher_id];
					});
			});
	}
}

export const db = new TeacherDB();

// --- meta key/value helpers (singletons: scoring settings, cached profile, …) ----
export async function metaGet<T>(key: string): Promise<T | undefined> {
	const row = await db.meta.get(key);
	return row?.value as T | undefined;
}

export async function metaSet(key: string, value: unknown): Promise<void> {
	await db.meta.put({ key, value });
}

/** Count of records with un-pushed local changes (drives the banner badge). */
export async function dirtyCount(): Promise<number> {
	return db.records.where('dirty').equals(1).count();
}

/** Records the server refused — they need the teacher to correct something. */
export async function rejectedCount(): Promise<number> {
	return db.records
		.where('dirty')
		.equals(1)
		.filter((r) => !!r.syncError)
		.count();
}

/** Count of «استدعاء ولي الأمر» requests still waiting to upload. */
export async function pendingSummonCount(): Promise<number> {
	return db.pendingSummons.count();
}

/** Count of record deletions still waiting to reach the server. */
export async function pendingDeleteCount(): Promise<number> {
	return db.pendingDeletes.count();
}

/** Wipe everything (on logout — the cache holds student PII). */
export async function clearOfflineData(): Promise<void> {
	await Promise.all([
		db.halaqahs.clear(),
		db.students.clear(),
		db.records.clear(),
		db.problems.clear(),
		db.meta.clear(),
		db.pendingSummons.clear(),
		db.pendingDeletes.clear()
	]);
}
