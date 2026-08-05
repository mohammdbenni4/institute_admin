// Reactive sync status for the UI (the unsynced-changes banner reads this).

import { dirtyCount, pendingSummonCount, rejectedCount } from './db';

export const syncState = $state<{
	pending: number; // everything awaiting upload: record edits + summons requests
	pendingRecords: number;
	pendingSummons: number;
	/** Records the server refused; they need the teacher to correct something. */
	rejected: number;
	syncing: boolean;
	lastError: string | null;
	lastSyncedAt: number | null;
}>({
	pending: 0,
	pendingRecords: 0,
	pendingSummons: 0,
	rejected: 0,
	syncing: false,
	lastError: null,
	lastSyncedAt: null
});

/** Recompute the pending badge from the cache. */
export async function refreshPending(): Promise<void> {
	const [records, summons, rejected] = await Promise.all([
		dirtyCount(),
		pendingSummonCount(),
		rejectedCount()
	]);
	syncState.pendingRecords = records;
	syncState.pendingSummons = summons;
	syncState.rejected = rejected;
	syncState.pending = records + summons;
}
