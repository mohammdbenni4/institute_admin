<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { auth, loadCurrentUser } from '$lib/api';

	let { children } = $props();
	let ready = $state(false);

	onMount(async () => {
		await loadCurrentUser();
		ready = true;
	});

	// Route guard: only authenticated teachers may leave /login.
	$effect(() => {
		if (!ready) return;
		const onLogin = $page.url.pathname === '/login';
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
{/if}
