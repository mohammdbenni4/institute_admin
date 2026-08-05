<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { auth, loadCurrentUser } from '$lib/api';
	import { initOffline } from '$lib/offline';
	import SyncStatus from '$lib/components/SyncStatus.svelte';
	import Loader from '$lib/components/Loader.svelte';

	let { children } = $props();
	let ready = $state(false);

	/** Reveal icons only once the bundled icon font is really loaded — see the
	 *  `.material-symbols-outlined` rule in app.css for why. Older WebViews without
	 *  the Font Loading API just get the icons straight away. */
	function markFontsReady(): void {
		const show = () => document.documentElement.classList.add('fonts-ready');
		if (!document.fonts) return show();
		void document.fonts.load('24px "Material Symbols Outlined"').finally(show);
	}

	onMount(async () => {
		markFontsReady();
		await loadCurrentUser();
		await initOffline();
		ready = true;
	});

	const onLogin = $derived($page.url.pathname === '/login');

	// Route guard: only authenticated teachers may leave /login.
	$effect(() => {
		if (!ready) return;
		if (!auth.teacher && !onLogin) goto('/login');
		else if (auth.teacher && onLogin) goto('/halaqat');
	});
</script>

{#if !ready}
	<div class="app-gradient flex min-h-dvh flex-col items-center justify-center gap-4 text-white">
		<span class="material-symbols-outlined text-6xl">menu_book</span>
		<p class="text-lg font-bold">صرح القرآن</p>
		<Loader class="text-2xl text-white/80" />
	</div>
{:else}
	{@render children()}
	{#if auth.teacher && !onLogin}
		<SyncStatus />
	{/if}
{/if}
