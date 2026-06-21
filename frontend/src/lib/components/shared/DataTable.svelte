<script lang="ts" module>
	export interface Column {
		key: string;
		label: string;
		class?: string;
	}
</script>

<script lang="ts">
	import { cn } from '$lib/utils';
	import type { Snippet } from 'svelte';

	interface Props {
		columns: Column[];
		rows: any[];
		emptyMessage?: string;
		onRowClick?: (row: any) => void;
		/**
		 * Optional custom cell renderer. When provided it is called for every cell;
		 * handle the special columns and fall back to `{value}` for the rest.
		 */
		cell?: Snippet<[{ row: any; column: Column; value: any }]>;
	}

	let { columns, rows, emptyMessage = 'لا توجد بيانات', onRowClick, cell }: Props = $props();
</script>

{#if rows.length === 0}
	<div class="glass-card p-12 text-center">
		<p class="text-muted-foreground">{emptyMessage}</p>
	</div>
{:else}
	<div class="glass-card overflow-hidden">
		<div class="overflow-x-auto">
			<table class="w-full caption-bottom text-sm">
				<thead>
					<tr class="border-b border-border bg-muted/50">
						{#each columns as col (col.key)}
							<th
								class={cn(
									'h-11 px-4 text-right align-middle font-semibold text-muted-foreground',
									col.class
								)}
							>
								{col.label}
							</th>
						{/each}
					</tr>
				</thead>
				<tbody>
					{#each rows as row, i (i)}
						<tr
							class={cn(
								'border-b border-border/50 transition-colors',
								onRowClick ? 'cursor-pointer hover:bg-muted/30' : 'hover:bg-muted/20'
							)}
							onclick={() => onRowClick?.(row)}
						>
							{#each columns as col (col.key)}
								<td class={cn('p-4 align-middle', col.class)}>
									{#if cell}
										{@render cell({ row, column: col, value: row[col.key] })}
									{:else}
										{row[col.key] ?? ''}
									{/if}
								</td>
							{/each}
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	</div>
{/if}
