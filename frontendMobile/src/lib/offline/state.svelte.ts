// Reactive sync status for the UI (the unsynced-changes banner reads this).

import { dirtyCount } from './db';

export const syncState = $state<{
	pending: number; // records with un-pushed local edits
	syncing: boolean;
	lastError: string | null;
	lastSyncedAt: number | null;
}>({
	pending: 0,
	syncing: false,
	lastError: null,
	lastSyncedAt: null
});

/** Recompute the pending badge from the cache. */
export async function refreshPending(): Promise<void> {
	syncState.pending = await dirtyCount();
}
