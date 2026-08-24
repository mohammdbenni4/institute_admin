<script lang="ts">
	// A compact select that opens a custom panel — same width as the trigger, taller than
	// native option lists, anchored directly under it — instead of the OS's native picker
	// (a full-screen wheel on iOS, an unstyled list on Android) which native <select> forces.
	import { cn } from '$lib/utils';
	import Icon from './Icon.svelte';

	let {
		value = $bindable<string | number | ''>(''),
		options,
		placeholder = '—',
		disabled = false,
		onchange,
		class: className = ''
	}: {
		value?: string | number | '';
		options: { value: string | number; label: string }[];
		placeholder?: string;
		disabled?: boolean;
		/** Fires after `value` is updated by a pick. */
		onchange?: () => void;
		class?: string;
	} = $props();

	let open = $state(false);
	let query = $state('');

	const selected = $derived(options.find((o) => String(o.value) === String(value)));
	const filtered = $derived(
		query.trim() ? options.filter((o) => o.label.includes(query.trim())) : options
	);

	function toggle(): void {
		if (disabled) return;
		open = !open;
		if (open) query = '';
	}

	function pick(v: string | number): void {
		value = v;
		open = false;
		query = '';
		onchange?.();
	}
</script>

<div class="relative min-w-0">
	<button
		type="button"
		onclick={toggle}
		{disabled}
		class={cn(
			'flex w-full items-center justify-between gap-1 rounded-xl border border-outline-variant/30 bg-surface-container-lowest text-on-surface focus:outline-none focus:ring-2 focus:ring-primary/20 disabled:opacity-40',
			className
		)}
	>
		<span class="min-w-0 flex-1 truncate">{selected ? selected.label : placeholder}</span>
		<Icon
			name={open ? 'expand_less' : 'expand_more'}
			class="shrink-0 text-[13px] text-on-surface-variant/40"
		/>
	</button>

	{#if open}
		<button
			type="button"
			class="fixed inset-0 z-40"
			aria-label="إغلاق"
			onclick={() => (open = false)}
		></button>
		<div
			class="absolute inset-x-0 top-full z-50 mt-1 overflow-hidden rounded-2xl border border-outline-variant/20 bg-surface-container-lowest shadow-2xl"
		>
			{#if options.length > 8}
				<input
					bind:value={query}
					placeholder="بحث…"
					class="w-full border-b border-outline-variant/15 bg-transparent px-3 py-2 text-[12px] text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none"
				/>
			{/if}
			<div class="max-h-64 overflow-y-auto overscroll-contain">
				{#each filtered as o (o.value)}
					<button
						type="button"
						onclick={() => pick(o.value)}
						class={cn(
							'block w-full px-3 py-2.5 text-right text-[12px] active:bg-primary/10',
							String(o.value) === String(value)
								? 'bg-primary/10 font-bold text-primary'
								: 'text-on-surface'
						)}
					>
						{o.label}
					</button>
				{:else}
					<p class="px-3 py-3 text-center text-[11px] text-on-surface-variant/50">لا نتائج</p>
				{/each}
			</div>
		</div>
	{/if}
</div>
