<script lang="ts">
	import { cn } from '$lib/utils';

	let {
		value = $bindable(),
		options,
		allowNull = true,
		compact = false,
		class: klass = ''
	}: {
		value: number | null;
		options: { value: number; label: string }[];
		allowNull?: boolean;
		/** Smaller padding/text, for squeezing the group onto the same line as its label. */
		compact?: boolean;
		class?: string;
	} = $props();

	function pick(v: number) {
		value = allowNull && value === v ? null : v;
	}
</script>

<div
	class={cn('grid gap-2', klass)}
	style={`grid-template-columns: repeat(${options.length}, minmax(0, 1fr));`}
>
	{#each options as opt (String(opt.value))}
		<button
			type="button"
			onclick={() => pick(opt.value)}
			class={cn(
				'rounded-full border font-bold transition active:scale-95',
				compact ? 'py-1.5 text-[10px]' : 'py-2.5 text-xs',
				value === opt.value
					? 'border-primary bg-primary text-on-primary shadow-sm'
					: 'border-outline-variant/30 bg-white/70 text-on-surface-variant hover:border-primary/30'
			)}
		>
			{opt.label}
		</button>
	{/each}
</div>
