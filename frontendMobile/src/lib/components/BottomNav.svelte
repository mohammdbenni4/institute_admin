<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { logout } from '$lib/api';
	import { syncNow, syncState } from '$lib/offline';
	import { cn } from '$lib/utils';
	import Icon from './Icon.svelte';
	import ConfirmDialog from './ConfirmDialog.svelte';

	let onHome = $derived($page.url.pathname.startsWith('/halaqat'));
	let onSummons = $derived($page.url.pathname.startsWith('/estidaa'));

	// Both nav actions are irreversible, so neither fires on a single tap.
	let confirmingLogout = $state(false);
	let confirmingQuit = $state(false);
	let uploading = $state(false);

	// Signing out clears the on-device cache (it holds student data), which would take
	// any un-uploaded work with it — so the sheet says so, and offers to upload first.
	const pending = $derived(syncState.pending);

	function doLogout() {
		logout();
		goto('/login');
	}

	async function uploadThenLogout() {
		uploading = true;
		try {
			await syncNow();
		} finally {
			uploading = false;
		}
		if (syncState.pending === 0) {
			confirmingLogout = false;
			doLogout();
		}
	}

	/** Close the app entirely (native only); logout stays a separate action. */
	async function quitApp() {
		try {
			const { Capacitor } = await import('@capacitor/core');
			if (Capacitor.isNativePlatform()) {
				const { App } = await import('@capacitor/app');
				await App.exitApp();
				return;
			}
		} catch {
			/* not running inside a Capacitor shell */
		}
		// Web fallback: best-effort (browsers only allow closing script-opened tabs).
		window.close();
	}
</script>

<nav
	class="pb-safe fixed inset-x-0 bottom-0 z-50 flex items-center justify-around rounded-t-[2rem] bg-brand-wash/90 px-4 pb-5 pt-3 shadow-[0_-10px_30px_rgba(10,92,63,0.06)] backdrop-blur-xl"
>
	<a
		href="/halaqat"
		class={cn(
			'flex flex-col items-center gap-0.5 rounded-full px-4 py-1 transition active:scale-110',
			onHome ? 'bg-brand-tint text-brand-deep' : 'text-brand-dark/60 hover:text-brand-deep'
		)}
	>
		<Icon name="dashboard" filled={onHome} />
		<span class="text-[10px] font-medium">الرئيسية</span>
	</a>
	<a
		href="/estidaa"
		class={cn(
			'flex flex-col items-center gap-0.5 rounded-full px-4 py-1 transition active:scale-110',
			onSummons ? 'bg-brand-tint text-brand-deep' : 'text-brand-dark/60 hover:text-brand-deep'
		)}
	>
		<Icon name="groups" filled={onSummons} />
		<span class="text-[10px] font-medium">استدعاء</span>
	</a>
	<button
		onclick={() => (confirmingLogout = true)}
		class="relative flex flex-col items-center gap-0.5 px-4 py-1 text-brand-dark/60 transition hover:text-error active:scale-110"
	>
		<Icon name="logout" />
		<span class="text-[10px] font-medium">خروج</span>
		{#if pending > 0}
			<span class="absolute -top-0.5 left-2 h-2 w-2 rounded-full bg-amber-500" aria-hidden="true"
			></span>
		{/if}
	</button>
	<button
		onclick={() => (confirmingQuit = true)}
		class="flex flex-col items-center gap-0.5 px-4 py-1 text-brand-dark/60 transition hover:text-error active:scale-110"
	>
		<Icon name="power_settings_new" />
		<span class="text-[10px] font-medium">إغلاق</span>
	</button>
</nav>

<ConfirmDialog
	bind:open={confirmingLogout}
	title="تسجيل الخروج؟"
	message="سيتم مسح البيانات المحفوظة على الجهاز، وستحتاج إلى الاتصال بالإنترنت لتسجيل الدخول مرة أخرى."
	confirmLabel="تسجيل الخروج"
	tone="danger"
	icon="logout"
	onConfirm={doLogout}
>
	{#snippet extra()}
		{#if pending > 0}
			<div class="space-y-2 rounded-2xl border border-amber-300 bg-amber-50 p-3">
				<p class="text-[12px] font-bold leading-relaxed text-amber-800">
					تنبيه: لديك {pending} تغيير لم يُرفع بعد. تسجيل الخروج الآن سيحذفها نهائياً.
				</p>
				<button
					type="button"
					onclick={uploadThenLogout}
					disabled={uploading}
					class="w-full rounded-full bg-amber-500 py-2.5 text-[13px] font-bold text-white active:scale-[0.98] disabled:opacity-60"
				>
					{uploading ? 'جارٍ الرفع…' : 'ارفع التغييرات أولاً'}
				</button>
			</div>
		{/if}
	{/snippet}
</ConfirmDialog>

<ConfirmDialog
	bind:open={confirmingQuit}
	title="إغلاق التطبيق؟"
	message="سيتم إغلاق التطبيق. تبقى بياناتك محفوظة على الجهاز ولن تفقد شيئاً."
	confirmLabel="إغلاق"
	icon="power_settings_new"
	onConfirm={quitApp}
/>
