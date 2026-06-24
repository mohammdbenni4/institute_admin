// Connectivity state. Uses the Capacitor Network plugin on a device (reliable in a
// WebView) and falls back to the browser's online/offline events on the web/dev.

import { Capacitor } from '@capacitor/core';
import { Network } from '@capacitor/network';

export const net = $state<{ online: boolean }>({ online: true });

let started = false;
const reconnectCbs = new Set<() => void>();

/** Run `cb` each time connectivity is regained. Returns an unsubscribe fn. */
export function onReconnect(cb: () => void): () => void {
	reconnectCbs.add(cb);
	return () => reconnectCbs.delete(cb);
}

function setOnline(value: boolean): void {
	const was = net.online;
	net.online = value;
	if (value && !was) for (const cb of reconnectCbs) cb();
}

/** Begin watching connectivity (idempotent; browser only). */
export async function startNetworkWatch(): Promise<void> {
	if (started || typeof window === 'undefined') return;
	started = true;

	if (Capacitor.isNativePlatform()) {
		const status = await Network.getStatus();
		net.online = status.connected;
		await Network.addListener('networkStatusChange', (s) => setOnline(s.connected));
	} else {
		net.online = navigator.onLine;
		window.addEventListener('online', () => setOnline(true));
		window.addEventListener('offline', () => setOnline(false));
	}
}
