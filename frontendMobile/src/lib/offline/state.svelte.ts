// Reactive sync status for the UI (the unsynced-changes banner reads this).

import { dirtyCount, pendingDeleteCount, pendingSummonCount, rejectedCount } from './db';

export const syncState = $state<{
	pending: number; // everything awaiting upload: record edits + summons requests + deletes
	pendingRecords: number;
	pendingSummons: number;
	pendingDeletes: number;
	/** Records the server refused; they need the teacher to correct something. */
	rejected: number;
	syncing: boolean;
	lastError: string | null;
	lastSyncedAt: number | null;
}>({
	pending: 0,
	pendingRecords: 0,
	pendingSummons: 0,
	pendingDeletes: 0,
	rejected: 0,
	syncing: false,
	lastError: null,
	lastSyncedAt: null
});

/** Recompute the pending badge from the cache. */
export async function refreshPending(): Promise<void> {
	const [records, summons, deletes, rejected] = await Promise.all([
		dirtyCount(),
		pendingSummonCount(),
		pendingDeleteCount(),
		rejectedCount()
	]);
	syncState.pendingRecords = records;
	syncState.pendingSummons = summons;
	syncState.pendingDeletes = deletes;
	syncState.rejected = rejected;
	syncState.pending = records + summons + deletes;
}
