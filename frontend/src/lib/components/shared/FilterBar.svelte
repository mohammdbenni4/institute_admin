<script lang="ts" module>
	import type { SelectOption } from '$lib/components/ui/Select.svelte';

	export interface FilterConfig {
		label: string;
		options: SelectOption[];
		value?: string;
		onChange?: (value: string) => void;
	}
</script>

<script lang="ts">
	import { Search, Filter, Download } from '@lucide/svelte';
	import Input from '$lib/components/ui/Input.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import Select from '$lib/components/ui/Select.svelte';
	import type { Snippet } from 'svelte';

	interface Props {
		searchPlaceholder?: string;
		searchValue?: string;
		filters?: FilterConfig[];
		onExport?: () => void;
		exportLabel?: string;
		children?: Snippet;
	}

	let {
		searchPlaceholder = 'بحث...',
		searchValue = $bindable(''),
		filters,
		onExport,
		exportLabel = 'تصدير',
		children
	}: Props = $props();
</script>

<div class="flex flex-col flex-wrap items-start gap-3 sm:flex-row sm:items-center">
	<div class="relative min-w-[200px] flex-1">
		<Search class="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
		<Input bind:value={searchValue} placeholder={searchPlaceholder} class="pr-9" />
	</div>

	{#if filters}
		{#each filters as filter, i (i)}
			<Select
				class="w-[160px]"
				placeholder={filter.label}
				value={filter.value ?? ''}
				onChange={filter.onChange}
				options={[{ value: 'all', label: 'الكل' }, ...filter.options]}
			>
				{#snippet icon()}
					<Filter class="h-3.5 w-3.5" />
				{/snippet}
			</Select>
		{/each}
	{/if}

	{#if onExport}
		<Button variant="outline" size="sm" onclick={onExport}>
			<Download class="h-4 w-4" />
			{exportLabel}
		</Button>
	{/if}

	{@render children?.()}
</div>
