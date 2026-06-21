<script lang="ts">
	// A tiny dependency-free trend chart (line + soft area + dots).
	interface Props {
		values: number[];
		width?: number;
		height?: number;
		class?: string;
	}

	let { values, width = 320, height = 64, class: klass = '' }: Props = $props();

	const pad = 6;

	let geo = $derived.by(() => {
		const v = values;
		if (v.length === 0) return { line: '', area: '', dots: [] as { x: number; y: number }[] };
		const max = Math.max(...v);
		const min = Math.min(...v);
		const span = max - min || 1;
		const n = v.length;
		const stepX = n > 1 ? (width - pad * 2) / (n - 1) : 0;
		const pts = v.map((val, i) => {
			const x = pad + (n > 1 ? i * stepX : (width - pad * 2) / 2);
			const y = height - pad - ((val - min) / span) * (height - pad * 2);
			return { x, y };
		});
		const line = pts
			.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`)
			.join(' ');
		const area = `${line} L ${pts[pts.length - 1].x.toFixed(1)} ${height - pad} L ${pts[0].x.toFixed(1)} ${height - pad} Z`;
		return { line, area, dots: pts };
	});
</script>

{#if values.length === 0}
	<div class="flex h-16 items-center justify-center text-xs text-muted-foreground">
		لا توجد بيانات
	</div>
{:else}
	<svg viewBox={`0 0 ${width} ${height}`} class={klass} preserveAspectRatio="none" role="img">
		<path d={geo.area} class="fill-primary/10" />
		<path
			d={geo.line}
			class="fill-none stroke-primary"
			stroke-width="2.5"
			stroke-linecap="round"
			stroke-linejoin="round"
		/>
		{#each geo.dots as p (p.x)}
			<circle cx={p.x} cy={p.y} r="2.5" class="fill-primary" />
		{/each}
	</svg>
{/if}
