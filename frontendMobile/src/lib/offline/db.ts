// On-device cache (IndexedDB via Dexie). Holds a mirror of the teacher's data so
// the app reads from here when offline, plus a "dirty" flag per daily-record that
// marks local edits awaiting upload. See [sync.ts] for the push engine.

import Dexie, { type Table } from 'dexie';
import type { DailyRecord, Halaqah, Problem, Student } from '$lib/api';

/** A daily record in the cache, with sync bookkeeping. */
export interface CachedRecord extends DailyRecord {
	/** 1 = has local changes not yet pushed to the server. */
	dirty: 0 | 1;
	/** 1 = created offline; no confirmed server id yet (id is a `local:` placeholder). */
	localOnly: 0 | 1;
	/** Selected difficulty ids for the next push (server returns `tagged_problems`). */
	problem_ids?: string[];
}

export interface MetaRow {
	key: string;
	value: unknown;
}

class TeacherDB extends Dexie {
	halaqahs!: Table<Halaqah, string>;
	students!: Table<Student, string>;
	records!: Table<CachedRecord, string>;
	problems!: Table<Problem, string>;
	meta!: Table<MetaRow, string>;

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

/** Wipe everything (on logout — the cache holds student PII). */
export async function clearOfflineData(): Promise<void> {
	await Promise.all([
		db.halaqahs.clear(),
		db.students.clear(),
		db.records.clear(),
		db.problems.clear(),
		db.meta.clear()
	]);
}
