<script lang="ts">
	import { cn } from '$lib/utils';
	import { clickOutside } from '$lib/actions/clickOutside';
	import type { Snippet } from 'svelte';
	import { fade } from 'svelte/transition';

	interface Props {
		/** Alignment of the panel relative to the trigger. */
		align?: 'start' | 'end';
		class?: string;
		trigger: Snippet<[{ toggle: () => void; open: boolean }]>;
		children: Snippet<[{ close: () => void }]>;
	}

	let { align = 'end', class: className = '', trigger, children }: Props = $props();

	let open = $state(false);
	const toggle = () => (open = !open);
	const close = () => (open = false);
</script>

<div class="relative" use:clickOutside={close}>
	{@render trigger({ toggle, open })}

	{#if open}
		<div
			transition:fade={{ duration: 100 }}
			class={cn(
				'absolute z-50 mt-2 rounded-lg border border-border bg-popover text-popover-foreground shadow-md',
				align === 'end' ? 'left-0' : 'right-0',
				className
			)}
		>
			{@render children({ close })}
		</div>
	{/if}
</div>
