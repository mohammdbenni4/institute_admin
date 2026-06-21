<script lang="ts">
	let { label = '' }: { label?: string } = $props();
</script>

<div class="flex flex-col items-center justify-center gap-3 py-16 text-on-surface-variant">
	<span class="material-symbols-outlined animate-spin text-3xl text-primary">progress_activity</span
	>
	{#if label}<span class="text-sm">{label}</span>{/if}
</div>
