// Public surface of the offline layer + one-time initialisation.

export { net } from './net.svelte';
export { syncState, refreshPending } from './state.svelte';
export { syncNow, pushSummons, retryRecord } from './sync';
export { clearOfflineData, type PendingSummon } from './db';
export { listPendingChanges, type PendingChange } from './pending';
export { discardChange } from './repo';
export * as repo from './repo';

import { App } from '@capacitor/app';
import { onReconnect, startNetworkWatch } from './net.svelte';
import { notifyPendingChanges, onNotificationTap } from './notify';
import { refreshPending, syncState } from './state.svelte';
import { syncNow } from './sync';

let inited = false;

/** How often to retry while the app is open and something is still queued. */
const RETRY_MS = 60_000;

/** Wire connectivity + notifications. Call once, after the teacher is authenticated. */
export async function initOffline(): Promise<void> {
	if (inited || typeof window === 'undefined') return;
	inited = true;

	await startNetworkWatch();
	await refreshPending();

	// Upload as soon as the connection is back.
	//
	// This used to only raise a notification and wait for the teacher to tap it, which
	// is why edits could sit on the device indefinitely: walk back into coverage,
	// ignore the notification, close the app — and nothing was ever sent. The
	// notification is now a *report* that work is pending, not the trigger for it.
	onReconnect(async () => {
		await syncNow();
		await refreshPending();
		if (syncState.pending > 0) await notifyPendingChanges(syncState.pending);
	});

	// Coming back to the app is the other moment worth retrying: the device may have
	// regained connectivity while the app was in the background, where no listener runs.
	App.addListener('appStateChange', ({ isActive }) => {
		if (isActive) void syncNow();
	}).catch(() => {
		/* not on a device — the browser has no app lifecycle */
	});

	// Backstop while the app is open: one failed attempt should not be the end of it.
	setInterval(() => {
		if (syncState.pending > 0 && !syncState.syncing) void syncNow();
	}, RETRY_MS);

	// Tapping the notification uploads immediately rather than waiting for the timer.
	await onNotificationTap(() => {
		void syncNow();
	});

	// Anything queued from a previous session goes up as soon as we start.
	void syncNow();
}
