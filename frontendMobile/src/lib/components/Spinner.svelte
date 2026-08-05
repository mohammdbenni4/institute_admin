<script lang="ts">
	// A pure-CSS ring — deliberately *not* a Material Symbols icon. The icon version
	// rendered its ligature name as plain text whenever the font was unavailable, so a
	// poor connection produced the word "progress_activity" rotating on screen.
	let { label = '', size = 'md' }: { label?: string; size?: 'sm' | 'md' } = $props();

	const dims = $derived(size === 'sm' ? 'h-5 w-5 border-2' : 'h-8 w-8 border-[3px]');
</script>

<div
	class={size === 'sm'
		? 'flex items-center justify-center'
		: 'flex flex-col items-center justify-center gap-3 py-16 text-on-surface-variant'}
>
	<span
		class={`inline-block animate-spin rounded-full border-primary/25 border-t-primary ${dims}`}
		role="status"
		aria-label={label || 'جارٍ التحميل'}
	></span>
	{#if label && size !== 'sm'}<span class="text-sm">{label}</span>{/if}
</div>
