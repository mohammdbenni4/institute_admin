<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Breadcrumb {
		label: string;
		href?: string;
	}

	interface Props {
		title: string;
		subtitle?: string;
		breadcrumbs?: Breadcrumb[];
		actions?: Snippet;
	}

	let { title, subtitle = '', breadcrumbs, actions }: Props = $props();
</script>

<div class="space-y-2">
	{#if breadcrumbs && breadcrumbs.length > 0}
		<nav class="flex items-center gap-1.5 text-sm text-muted-foreground">
			{#each breadcrumbs as crumb, i (i)}
				<span class="flex items-center gap-1.5">
					{#if i > 0}<span>/</span>{/if}
					<span class={i === breadcrumbs.length - 1 ? 'font-medium text-foreground' : ''}>
						{crumb.label}
					</span>
				</span>
			{/each}
		</nav>
	{/if}
	<div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
		<div>
			<h1 class="text-xl font-bold text-foreground md:text-2xl">{title}</h1>
			{#if subtitle}<p class="mt-0.5 text-sm text-muted-foreground">{subtitle}</p>{/if}
		</div>
		{#if actions}
			<div class="flex flex-wrap items-center gap-2">{@render actions()}</div>
		{/if}
	</div>
</div>
