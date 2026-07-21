<script lang="ts">
	import type { Component } from 'svelte';

	interface Props {
		title: string;
		value: string | number;
		icon: Component<{ class?: string }>;
		change?: string;
		changeType?: 'positive' | 'negative' | 'neutral';
		subtitle?: string;
	}

	let { title, value, icon: Icon, change, changeType = 'neutral', subtitle }: Props = $props();

	let changeColor = $derived(
		changeType === 'positive'
			? 'text-emerald-600'
			: changeType === 'negative'
				? 'text-red-500'
				: 'text-muted-foreground'
	);
</script>

<div class="kpi-card flex items-start justify-between gap-2">
	<div class="min-w-0 space-y-1.5">
		<p class="text-xs text-muted-foreground sm:text-sm">{title}</p>
		<p class="text-xl font-bold text-foreground sm:text-2xl">{value}</p>
		{#if change}<p class="text-xs font-medium {changeColor}">{change}</p>{/if}
		{#if subtitle}<p class="text-xs text-muted-foreground">{subtitle}</p>{/if}
	</div>
	<div class="shrink-0 rounded-xl bg-primary/10 p-2.5 text-primary sm:p-3">
		<Icon class="h-5 w-5" />
	</div>
</div>
