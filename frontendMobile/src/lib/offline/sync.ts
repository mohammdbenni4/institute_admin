// Push engine: drains records flagged `dirty` to the server. Pull (refresh) happens
// lazily through the read-through repo. One teacher owns their data, so the conflict
// policy is simply last-write-wins keyed by (student, date).

import { ApiError, dailyRecordsApi, type DailyRecord } from '$lib/api';
import { db, type CachedRecord } from './db';
import { net } from './net.svelte';
import { clearPendingNotification } from './notify';
import { refreshPending, syncState } from './state.svelte';

/** fetch() rejects (vs. an HTTP error) when offline — treat that as "try later". */
export function isNetworkError(e: unknown): boolean {
	return !(e instanceof ApiError);
}

/** The editable fields, sent as a full overwrite (last-write-wins). */
function toApiFields(rec: CachedRecord) {
	return {
		present: rec.present,
		excused: rec.excused,
		exam_from: rec.exam_from,
		exam_to: rec.exam_to,
		exam_total: rec.exam_total,
		homework: rec.homework,
		problems: rec.problems,
		rating: rec.rating,
		revision_lesson: rec.revision_lesson,
		revision_rating: rec.revision_rating,
		attitude: rec.attitude,
		added_points: rec.added_points,
		notes: rec.notes,
		problem_ids: rec.problem_ids ?? rec.tagged_problems.map((p) => p.id)
	};
}

async function pushOne(rec: CachedRecord): Promise<void> {
	const fields = toApiFields(rec);
	let saved: DailyRecord;
	if (rec.localOnly) {
		// Created offline: it may already exist on the server (natural key), so upsert.
		const found = await dailyRecordsApi.list({
			student_id: rec.student_id,
			record_date: rec.record_date,
			limit: 1
		});
		const existing = found.items[0];
		saved = existing
			? await dailyRecordsApi.update(existing.id, fields)
			: await dailyRecordsApi.create({
					student_id: rec.student_id,
					teacher_id: rec.teacher_id,
					halaqah_id: rec.halaqah_id,
					record_date: rec.record_date,
					...fields
				});
	} else {
		saved = await dailyRecordsApi.update(rec.id, fields);
	}
	// Replace the local row with the server's authoritative version.
	if (saved.id !== rec.id) await db.records.delete(rec.id);
	await db.records.put({ ...saved, dirty: 0, localOnly: 0 });
}

/** Upload every dirty record in order. Stops cleanly if the connection drops. */
export async function pushDirty(): Promise<void> {
	const dirty = await db.records.where('dirty').equals(1).toArray();
	for (const rec of dirty) {
		try {
			await pushOne(rec);
		} catch (e) {
			if (isNetworkError(e)) return; // lost connection mid-sync — keep the rest dirty
			// Server rejected this one (e.g. validation): leave it dirty, note it, continue.
			syncState.lastError = e instanceof ApiError ? e.message : 'تعذّرت مزامنة أحد السجلات';
		}
	}
}

/** Push pending changes now (no-op offline or while already syncing). */
export async function syncNow(): Promise<void> {
	if (!net.online || syncState.syncing) return;
	syncState.syncing = true;
	syncState.lastError = null;
	try {
		await pushDirty();
		syncState.lastSyncedAt = Date.now();
	} finally {
		syncState.syncing = false;
		await refreshPending();
		if (syncState.pending === 0) await clearPendingNotification();
	}
}
