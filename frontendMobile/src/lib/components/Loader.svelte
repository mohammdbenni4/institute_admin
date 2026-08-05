<script lang="ts">
	// A bare spinning ring for inline use (inside buttons, chips, the splash screen).
	// Font-free by design: the Material Symbols version printed its ligature name as
	// text whenever the icon font was missing, so users saw a long word spinning.
	import { cn } from '$lib/utils';

	let { class: klass = '' }: { class?: string } = $props();
</script>

<span
	class={cn(
		'inline-block h-[1em] w-[1em] shrink-0 animate-spin rounded-full border-2 border-current/25 border-t-current align-[-0.125em]',
		klass
	)}
	role="status"
	aria-label="جارٍ التحميل"
></span>
