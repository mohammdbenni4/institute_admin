<script lang="ts">
	import { cn } from '$lib/utils';

	let {
		name,
		filled = false,
		class: klass = ''
	}: { name: string; filled?: boolean; class?: string } = $props();
</script>

<span
	class={cn('material-symbols-outlined select-none', filled && 'filled', klass)}
	aria-hidden="true">{name}</span
>
