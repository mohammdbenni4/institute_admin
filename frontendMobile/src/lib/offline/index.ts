// Public surface of the offline layer + one-time initialisation.

export { net } from './net.svelte';
export { syncState, refreshPending } from './state.svelte';
export { syncNow } from './sync';
export { clearOfflineData } from './db';
export { listPendingChanges, type PendingChange } from './pending';
export * as repo from './repo';

import { onReconnect, startNetworkWatch } from './net.svelte';
import { notifyPendingChanges, onNotificationTap } from './notify';
import { refreshPending, syncState } from './state.svelte';
import { syncNow } from './sync';

let inited = false;

/** Wire connectivity + notifications. Call once, after the teacher is authenticated. */
export async function initOffline(): Promise<void> {
	if (inited || typeof window === 'undefined') return;
	inited = true;

	await startNetworkWatch();
	await refreshPending();

	// On regaining connectivity with un-uploaded changes: nudge with an OS notification
	// (the teacher decides when to upload — banner button or notification tap).
	onReconnect(async () => {
		await refreshPending();
		if (syncState.pending > 0) await notifyPendingChanges(syncState.pending);
	});

	// Tapping the notification triggers the upload.
	await onNotificationTap(() => {
		void syncNow();
	});
}
