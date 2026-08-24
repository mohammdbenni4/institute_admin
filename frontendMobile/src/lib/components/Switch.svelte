<script lang="ts">
	import { cn } from '$lib/utils';

	let {
		checked = $bindable(false),
		disabled = false,
		label = '',
		onchange
	}: {
		checked?: boolean;
		disabled?: boolean;
		label?: string;
		/** Fires after `checked` is toggled — for callers driving state from elsewhere
		 *  (e.g. membership in a Set) rather than a plain bound boolean. */
		onchange?: (checked: boolean) => void;
	} = $props();
</script>

<button
	type="button"
	role="switch"
	aria-checked={checked}
	aria-label={label}
	{disabled}
	onclick={() => {
		checked = !checked;
		onchange?.(checked);
	}}
	class={cn(
		'relative h-6 w-11 shrink-0 rounded-full transition-colors disabled:opacity-40',
		checked ? 'bg-primary' : 'bg-surface-container-high'
	)}
>
	<span
		class={cn(
			'absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-all',
			checked ? 'left-0.5' : 'right-0.5'
		)}
	></span>
</button>
