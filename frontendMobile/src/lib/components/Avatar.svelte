<script lang="ts">
	import { cn, initials } from '$lib/utils';

	let {
		name,
		size = 'md',
		class: klass = ''
	}: { name: string; size?: 'sm' | 'md' | 'lg'; class?: string } = $props();

	const sizes = {
		sm: 'w-10 h-10 text-sm',
		md: 'w-14 h-14 text-lg',
		lg: 'w-16 h-16 text-xl'
	} as const;
</script>

<div
	class={cn(
		'flex shrink-0 items-center justify-center rounded-full border-2 border-primary/10 bg-tertiary-fixed font-bold text-primary',
		sizes[size],
		klass
	)}
>
	{initials(name)}
</div>
