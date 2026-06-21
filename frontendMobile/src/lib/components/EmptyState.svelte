<script lang="ts">
	import Icon from './Icon.svelte';

	let {
		icon = 'inbox',
		title,
		hint = ''
	}: { icon?: string; title: string; hint?: string } = $props();
</script>

<div class="flex flex-col items-center justify-center gap-3 px-6 py-16 text-center">
	<div
		class="flex h-16 w-16 items-center justify-center rounded-full bg-surface-container-high text-primary/50"
	>
		<Icon name={icon} class="text-3xl" />
	</div>
	<p class="text-sm font-bold text-on-surface">{title}</p>
	{#if hint}<p class="max-w-xs text-xs text-on-surface-variant/70">{hint}</p>{/if}
</div>
