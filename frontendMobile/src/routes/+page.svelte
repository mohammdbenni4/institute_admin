<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';

	// Entry point: the layout guard sends unauthenticated users to /login.
	onMount(() => {
		goto('/halaqat', { replaceState: true });
	});
</script>
