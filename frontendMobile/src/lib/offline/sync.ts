// Push engine: drains records flagged `dirty` to the server. Pull (refresh) happens
// lazily through the read-through repo. One teacher owns their data, so the conflict
// policy is simply last-write-wins keyed by (student, date).

import {
	ApiError,
	dailyRecordsApi,
	parentSummonsApi,
	type BulkUpsertItem,
	type DailyRecord
} from '$lib/api';
import { db, type CachedRecord } from './db';
import { net } from './net.svelte';
import { clearPendingNotification } from './notify';
import { refreshPending, syncState } from './state.svelte';

/** fetch() rejects (vs. an HTTP error) when offline — treat that as "try later". */
export function isNetworkError(e: unknown): boolean {
	return !(e instanceof ApiError);
}

/** The server accepts at most this many records per bulk call. */
const BATCH_SIZE = 100;

/** The editable fields, sent as a full overwrite (last-write-wins). */
function toApiFields(rec: CachedRecord): BulkUpsertItem {
	return {
		student_id: rec.student_id,
		record_date: rec.record_date,
		present: rec.present,
		excused: rec.excused,
		late: rec.late,
		excuse_reason: rec.excuse_reason,
		exam_from: rec.exam_from,
		exam_to: rec.exam_to,
		// Rashidi students record a line *within* the page. Omitting these here meant a
		// record round-tripped through the server came back with the lines erased.
		exam_from_line: rec.exam_from_line,
		exam_to_line: rec.exam_to_line,
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

/** Replace the local rows with the server's authoritative versions. */
async function adoptServerRecords(batch: CachedRecord[], saved: DailyRecord[]): Promise<void> {
	const savedKeys = new Set(saved.map((r) => `${r.student_id}|${r.record_date}`));
	// A locally-created row carries a `local:` id the server never used; drop it once
	// the server has answered with the real record for the same natural key.
	const orphans = batch
		.filter((r) => savedKeys.has(`${r.student_id}|${r.record_date}`))
		.filter((r) => !saved.some((s) => s.id === r.id))
		.map((r) => r.id);
	if (orphans.length) await db.records.bulkDelete(orphans);
	// The teacher may have deleted the record while this very upload was in flight —
	// don't let the server's answer for the old save resurrect it.
	const pendingDeleteIds = new Set((await db.pendingDeletes.toArray()).map((d) => d.id));
	const toAdopt = saved.filter((r) => !pendingDeleteIds.has(r.id));
	await db.records.bulkPut(
		toAdopt.map((r) => ({ ...r, dirty: 0 as const, localOnly: 0 as const }))
	);
}

/**
 * Upload every dirty record. Records are grouped by halaqah and sent in batches
 * through the idempotent bulk endpoint — one request per batch instead of the old
 * "list, then create-or-patch" pair *per record*, which is what made uploading a
 * class of 20 on a weak connection take dozens of sequential round trips.
 *
 * Stops cleanly if the connection drops; anything not yet confirmed stays dirty and
 * is retried on the next sync (replaying is safe — the endpoint is idempotent).
 */
export async function pushDirty(): Promise<void> {
	// Skip records the server has already rejected: they cannot succeed unchanged,
	// and retrying them every sync only re-raises the same error forever.
	const dirty = (await db.records.where('dirty').equals(1).toArray()).filter((r) => !r.syncError);
	if (dirty.length === 0) return;

	const byHalaqah = new Map<string, CachedRecord[]>();
	for (const rec of dirty) {
		const group = byHalaqah.get(rec.halaqah_id);
		if (group) group.push(rec);
		else byHalaqah.set(rec.halaqah_id, [rec]);
	}

	for (const [halaqahId, records] of byHalaqah) {
		for (let i = 0; i < records.length; i += BATCH_SIZE) {
			const batch = records.slice(i, i + BATCH_SIZE);
			try {
				const res = await dailyRecordsApi.bulkUpsert({
					halaqah_id: halaqahId,
					teacher_id: batch[0].teacher_id,
					records: batch.map(toApiFields)
				});
				await adoptServerRecords(batch, res.items);
			} catch (e) {
				if (isNetworkError(e)) return; // lost connection mid-sync — keep the rest dirty
				// The server rejected the batch (e.g. validation). Fall back to one-by-one
				// so a single bad record cannot block everyone else's changes.
				await pushIndividually(halaqahId, batch);
			}
		}
	}
}

/** Retry a rejected batch record by record, isolating the one the server dislikes.
 *  The reason is stored *on that record* so the sync sheet can point the teacher at
 *  the exact student and field instead of showing one global error. */
async function pushIndividually(halaqahId: string, batch: CachedRecord[]): Promise<void> {
	for (const rec of batch) {
		try {
			const res = await dailyRecordsApi.bulkUpsert({
				halaqah_id: halaqahId,
				teacher_id: rec.teacher_id,
				records: [toApiFields(rec)]
			});
			await adoptServerRecords([rec], res.items);
		} catch (e) {
			if (isNetworkError(e)) return;
			const reason = e instanceof ApiError ? e.message : 'تعذّرت مزامنة هذا السجل';
			await db.records.update(rec.id, { syncError: reason });
			syncState.lastError = reason;
		}
	}
}

/** Put a rejected record back in the queue (the teacher asked to try again). */
export async function retryRecord(id: string): Promise<void> {
	await db.records.update(id, { syncError: null });
	await refreshPending();
	await syncNow();
}

/**
 * Drain the record-deletion outbox (un-marking an attendance status that had
 * already reached the server). Each entry is a bare record id — nothing to edit,
 * so like summons it is "send once and forget".
 */
export async function pushDeletes(): Promise<void> {
	const queued = await db.pendingDeletes.orderBy('created_at').toArray();
	for (const item of queued) {
		try {
			await dailyRecordsApi.remove(item.id);
			await db.pendingDeletes.delete(item.id);
		} catch (e) {
			if (isNetworkError(e)) return; // try again on the next sync
			// 404 (already gone) or any other rejection: nothing left to retry for.
			await db.pendingDeletes.delete(item.id);
		}
	}
}

/**
 * Drain the «استدعاء ولي الأمر» outbox.
 *
 * A request is created once and never edited, so the whole lifecycle is
 * "send, then forget". A request the server refuses outright (410/404/422 — the
 * student left the halaqah, say) is dropped with its reason recorded rather than
 * retried forever; anything else is left queued.
 */
export async function pushSummons(): Promise<void> {
	const queued = await db.pendingSummons.orderBy('created_at').toArray();
	for (const item of queued) {
		try {
			await parentSummonsApi.create({
				student_id: item.student_id,
				halaqah_id: item.halaqah_id,
				reason: item.reason
			});
			await db.pendingSummons.delete(item.id);
		} catch (e) {
			if (isNetworkError(e)) return; // try again on the next sync
			const status = e instanceof ApiError ? e.status : 0;
			if (status >= 400 && status < 500) {
				await db.pendingSummons.delete(item.id);
				syncState.lastError = e instanceof ApiError ? e.message : 'تعذّر إرسال طلب الاستدعاء';
			} else {
				return; // server trouble — keep it queued
			}
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
		await pushSummons();
		await pushDeletes();
		syncState.lastSyncedAt = Date.now();
	} finally {
		syncState.syncing = false;
		await refreshPending();
		if (syncState.pending === 0) await clearPendingNotification();
	}
}
