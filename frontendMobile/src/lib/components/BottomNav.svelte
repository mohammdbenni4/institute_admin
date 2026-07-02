<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { logout } from '$lib/api';
	import { cn } from '$lib/utils';
	import Icon from './Icon.svelte';

	let onHome = $derived($page.url.pathname.startsWith('/halaqat'));

	function doLogout() {
		logout();
		goto('/login');
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
	<button
		onclick={doLogout}
		class="flex flex-col items-center gap-0.5 px-4 py-1 text-brand-dark/60 transition hover:text-error active:scale-110"
	>
		<Icon name="logout" />
		<span class="text-[10px] font-medium">خروج</span>
	</button>
	<button
		onclick={quitApp}
		class="flex flex-col items-center gap-0.5 px-4 py-1 text-brand-dark/60 transition hover:text-error active:scale-110"
	>
		<Icon name="power_settings_new" />
		<span class="text-[10px] font-medium">إغلاق</span>
	</button>
</nav>
