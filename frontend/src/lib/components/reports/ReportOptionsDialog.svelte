<script lang="ts">
	// Chooses *what* goes into a report and *over which period*, before printing or
	// exporting. Every block of the printed sheet is a switch so an admin can leave
	// out anything the month does not need.
	import Dialog from '$lib/components/ui/Dialog.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import Input from '$lib/components/ui/Input.svelte';
	import Label from '$lib/components/ui/Label.svelte';
	import Switch from '$lib/components/ui/Switch.svelte';
	import { FileSpreadsheet, Printer } from '@lucide/svelte';
	import { SECTION_LABELS, type ReportPeriod, type ReportSections } from '$lib/reports/options';

	let {
		open = $bindable(false),
		sections = $bindable(),
		period = $bindable(),
		busy = false,
		onPrint,
		onExport
	}: {
		open?: boolean;
		sections: ReportSections;
		period: ReportPeriod;
		busy?: boolean;
		onPrint: () => void;
		onExport: () => void;
	} = $props();

	const rangeInvalid = $derived(
		period.mode === 'range' && (!period.from || !period.to || period.from > period.to)
	);
</script>

<Dialog bind:open title="خيارات التقرير" class="max-w-2xl">
	<div class="space-y-5" dir="rtl">
		<!-- ── Period ── -->
		<section class="space-y-3">
			<p class="text-sm font-bold text-foreground">الفترة الزمنية</p>
			<div class="flex gap-2">
				<button
					type="button"
					onclick={() => (period.mode = 'month')}
					class={'flex-1 rounded-lg border px-3 py-2 text-xs font-medium transition ' +
						(period.mode === 'month'
							? 'border-primary bg-primary/10 text-primary'
							: 'border-border text-muted-foreground hover:bg-muted')}
				>
					شهر كامل
				</button>
				<button
					type="button"
					onclick={() => (period.mode = 'range')}
					class={'flex-1 rounded-lg border px-3 py-2 text-xs font-medium transition ' +
						(period.mode === 'range'
							? 'border-primary bg-primary/10 text-primary'
							: 'border-border text-muted-foreground hover:bg-muted')}
				>
					من تاريخ إلى تاريخ
				</button>
			</div>

			{#if period.mode === 'month'}
				<div class="space-y-1.5">
					<Label for="report-month">الشهر</Label>
					<Input id="report-month" type="month" bind:value={period.month} class="w-48" />
				</div>
			{:else}
				<div class="flex flex-wrap gap-3">
					<div class="space-y-1.5">
						<Label for="report-from">من</Label>
						<Input id="report-from" type="date" bind:value={period.from} class="w-44" />
					</div>
					<div class="space-y-1.5">
						<Label for="report-to">إلى</Label>
						<Input id="report-to" type="date" bind:value={period.to} class="w-44" />
					</div>
				</div>
				{#if rangeInvalid}
					<p class="text-xs text-destructive">حدّد تاريخ بداية ونهاية صحيحين.</p>
				{/if}
			{/if}
		</section>

		<!-- ── Sections ── -->
		<section class="space-y-3">
			<p class="text-sm font-bold text-foreground">البيانات المُصدَّرة</p>
			<div class="grid gap-2 sm:grid-cols-2">
				{#each SECTION_LABELS as item (item.key)}
					<label
						class="flex cursor-pointer items-center justify-between gap-3 rounded-lg border border-border px-3 py-2.5 hover:bg-muted/50"
					>
						<span class="min-w-0">
							<span class="block text-xs font-medium text-foreground">{item.label}</span>
							{#if item.hint}
								<span class="block text-[10px] text-muted-foreground">{item.hint}</span>
							{/if}
						</span>
						<Switch bind:checked={sections[item.key]} />
					</label>
				{/each}
			</div>
		</section>

		<!-- ── Actions ── -->
		<div class="flex flex-wrap justify-end gap-2 border-t border-border pt-4">
			<Button variant="outline" onclick={onExport} disabled={busy || rangeInvalid}>
				<FileSpreadsheet class="h-4 w-4" />تصدير Excel
			</Button>
			<Button onclick={onPrint} disabled={busy || rangeInvalid}>
				<Printer class="h-4 w-4" />{busy ? 'جارٍ التحضير…' : 'طباعة التقرير'}
			</Button>
		</div>
	</div>
</Dialog>
