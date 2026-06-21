<script lang="ts">
	import { cn } from '$lib/utils';

	type Tone = 'success' | 'danger' | 'neutral' | 'info';

	interface Props {
		label: string;
		tone?: Tone;
		class?: string;
	}

	let { label, tone = 'neutral', class: className = '' }: Props = $props();

	const tones: Record<Tone, string> = {
		success: 'bg-emerald-100 text-emerald-700',
		danger: 'bg-red-100 text-red-700',
		neutral: 'bg-muted text-muted-foreground',
		info: 'bg-primary/10 text-primary'
	};
</script>

<span
	class={cn(
		'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
		tones[tone],
		className
	)}
>
	{label}
</span>
