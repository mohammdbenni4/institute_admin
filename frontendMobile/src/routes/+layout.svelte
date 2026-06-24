<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { auth, loadCurrentUser } from '$lib/api';
	import { initOffline } from '$lib/offline';
	import UnsyncedBanner from '$lib/components/UnsyncedBanner.svelte';

	let { children } = $props();
	let ready = $state(false);

	onMount(async () => {
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
		<span class="material-symbols-outlined animate-spin text-2xl text-white/80">
			progress_activity
		</span>
	</div>
{:else}
	{@render children()}
	{#if auth.teacher && !onLogin}
		<UnsyncedBanner />
	{/if}
{/if}
