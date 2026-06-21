<script lang="ts">
	import { cn } from '$lib/utils';
	import { ChevronDown, Check } from '@lucide/svelte';
	import { clickOutside } from '$lib/actions/clickOutside';
	import type { Snippet } from 'svelte';
	import { slide } from 'svelte/transition';

	export interface SelectOption {
		value: string;
		label: string;
	}

	interface Props {
		value?: string;
		placeholder?: string;
		options: SelectOption[];
		class?: string;
		disabled?: boolean;
		icon?: Snippet;
		onChange?: (value: string) => void;
	}

	let {
		value = $bindable(''),
		placeholder = 'اختر...',
		options,
		class: className = '',
		disabled = false,
		icon,
		onChange
	}: Props = $props();

	let open = $state(false);

	let selectedLabel = $derived(options.find((o) => o.value === value)?.label ?? '');

	function select(option: SelectOption) {
		value = option.value;
		onChange?.(option.value);
		open = false;
	}
</script>

<div class="relative" use:clickOutside={() => (open = false)}>
	<button
		type="button"
		{disabled}
		aria-haspopup="listbox"
		aria-expanded={open}
		onclick={() => (open = !open)}
		class={cn(
			'flex h-10 w-full items-center justify-between gap-2 rounded-lg border border-input bg-card px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50',
			className
		)}
	>
		<span class="flex items-center gap-1.5 truncate">
			{@render icon?.()}
			<span class={cn('truncate', selectedLabel ? 'text-foreground' : 'text-muted-foreground')}>
				{selectedLabel || placeholder}
			</span>
		</span>
		<ChevronDown class="h-4 w-4 shrink-0 opacity-50" />
	</button>

	{#if open}
		<div
			role="listbox"
			transition:slide={{ duration: 120 }}
			class="absolute z-50 mt-1 max-h-60 w-full min-w-[8rem] overflow-y-auto rounded-lg border border-border bg-popover p-1 text-popover-foreground shadow-md"
		>
			{#each options as option (option.value)}
				<button
					type="button"
					role="option"
					aria-selected={value === option.value}
					onclick={() => select(option)}
					class={cn(
						'flex w-full items-center justify-between gap-2 rounded-md px-2 py-1.5 text-right text-sm transition-colors hover:bg-accent hover:text-accent-foreground',
						value === option.value && 'bg-accent/50 font-medium'
					)}
				>
					<span class="truncate">{option.label}</span>
					{#if value === option.value}
						<Check class="h-4 w-4 shrink-0 text-primary" />
					{/if}
				</button>
			{/each}
		</div>
	{/if}
</div>
