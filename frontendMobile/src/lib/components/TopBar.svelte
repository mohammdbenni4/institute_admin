<script lang="ts">
	import type { Snippet } from 'svelte';
	import { goto } from '$app/navigation';
	import Icon from './Icon.svelte';

	let {
		title,
		subtitle = '',
		backHref = '',
		actions
	}: { title: string; subtitle?: string; backHref?: string; actions?: Snippet } = $props();
</script>

<header class="app-gradient pt-safe fixed inset-x-0 top-0 z-50 text-white shadow-lg">
	<div class="flex h-16 items-center justify-between gap-3 px-3">
		<div class="flex min-w-0 items-center gap-1.5">
			{#if backHref}
				<button
					onclick={() => goto(backHref)}
					class="rounded-full p-2 transition hover:bg-white/10 active:scale-95"
					aria-label="رجوع"
				>
					<Icon name="chevron_right" class="text-2xl" />
				</button>
			{/if}
			<div class="flex min-w-0 flex-col">
				<span class="truncate text-sm font-bold leading-tight">{title}</span>
				{#if subtitle}
					<span class="truncate text-[11px] font-light text-white/80">{subtitle}</span>
				{/if}
			</div>
		</div>
		<div class="flex items-center gap-1">
			{@render actions?.()}
		</div>
	</div>
</header>
