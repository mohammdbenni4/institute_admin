<script lang="ts">
	import { cn } from '$lib/utils';
	import { X } from '@lucide/svelte';
	import type { Snippet } from 'svelte';
	import { fade, scale } from 'svelte/transition';

	interface Props {
		open?: boolean;
		title?: string;
		class?: string;
		onOpenChange?: (open: boolean) => void;
		children?: Snippet;
		header?: Snippet;
	}

	let {
		open = $bindable(false),
		title = '',
		class: className = '',
		onOpenChange,
		children,
		header
	}: Props = $props();

	function close() {
		open = false;
		onOpenChange?.(false);
	}

	function onKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') close();
	}
</script>

<svelte:window on:keydown={onKeydown} />

{#if open}
	<div class="fixed inset-0 z-50 flex items-center justify-center p-4">
		<!-- Overlay -->
		<div
			class="absolute inset-0 bg-foreground/40 backdrop-blur-sm"
			role="presentation"
			onclick={close}
			transition:fade={{ duration: 150 }}
		></div>

		<!-- Content -->
		<div
			class={cn(
				'relative z-10 w-full max-w-lg rounded-2xl border border-border bg-card p-6 shadow-lg',
				className
			)}
			role="dialog"
			aria-modal="true"
			transition:scale={{ duration: 150, start: 0.96 }}
		>
			<div class="mb-4 flex items-start justify-between gap-4">
				{#if header}
					{@render header()}
				{:else if title}
					<h2 class="text-lg font-bold text-foreground">{title}</h2>
				{:else}
					<span></span>
				{/if}
				<button
					type="button"
					onclick={close}
					class="rounded-md p-1 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
					aria-label="إغلاق"
				>
					<X class="h-4 w-4" />
				</button>
			</div>
			{@render children?.()}
		</div>
	</div>
{/if}
