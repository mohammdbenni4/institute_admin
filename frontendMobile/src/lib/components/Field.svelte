<script lang="ts">
	import type { Snippet } from 'svelte';
	import Icon from './Icon.svelte';

	let {
		label,
		icon = '',
		hint = '',
		children
	}: { label: string; icon?: string; hint?: string; children: Snippet } = $props();
</script>

<div class="space-y-2">
	<div class="flex items-center gap-1.5 pr-1">
		{#if icon}<Icon name={icon} class="text-base text-primary" />{/if}
		<span class="text-[13px] font-bold text-on-surface-variant">{label}</span>
		{#if hint}<span class="text-[10px] text-on-surface-variant/50">{hint}</span>{/if}
	</div>
	{@render children()}
</div>
