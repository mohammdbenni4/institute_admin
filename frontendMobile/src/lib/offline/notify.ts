// OS local notifications (Capacitor). Used to nudge the teacher when connectivity
// returns and there are still un-uploaded changes. No-op on the web.

import { Capacitor } from '@capacitor/core';
import { LocalNotifications } from '@capacitor/local-notifications';

const PENDING_NOTIF_ID = 1001;

async function ensurePermission(): Promise<boolean> {
	if (!Capacitor.isNativePlatform()) return false;
	const current = await LocalNotifications.checkPermissions();
	if (current.display === 'granted') return true;
	const requested = await LocalNotifications.requestPermissions();
	return requested.display === 'granted';
}

/** Fire a notification telling the teacher they have `count` changes to upload. */
export async function notifyPendingChanges(count: number): Promise<void> {
	if (count <= 0 || !Capacitor.isNativePlatform()) return;
	if (!(await ensurePermission())) return;
	await LocalNotifications.schedule({
		notifications: [
			{
				id: PENDING_NOTIF_ID,
				title: 'صرح القرآن — المعلم',
				body: `لديك ${count} تغييرات غير مرفوعة. اضغط للرفع الآن.`,
				extra: { action: 'sync' }
			}
		]
	});
}

/** Clear the pending notification (e.g. after a successful sync). */
export async function clearPendingNotification(): Promise<void> {
	if (!Capacitor.isNativePlatform()) return;
	await LocalNotifications.cancel({ notifications: [{ id: PENDING_NOTIF_ID }] }).catch(() => {});
}

/** Run `cb` when the teacher taps the notification. Returns nothing (lives for the session). */
export async function onNotificationTap(cb: () => void): Promise<void> {
	if (!Capacitor.isNativePlatform()) return;
	await LocalNotifications.addListener('localNotificationActionPerformed', (event) => {
		if (event.notification.extra?.action === 'sync') cb();
	});
}
