<script lang="ts">
	import PageHeader from '$lib/components/shared/PageHeader.svelte';
	import FilterBar from '$lib/components/shared/FilterBar.svelte';
	import DataTable, { type Column } from '$lib/components/shared/DataTable.svelte';
	import ConfirmDialog from '$lib/components/shared/ConfirmDialog.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import Dialog from '$lib/components/ui/Dialog.svelte';
	import Input from '$lib/components/ui/Input.svelte';
	import Label from '$lib/components/ui/Label.svelte';
	import Switch from '$lib/components/ui/Switch.svelte';
	import { ApiError, timesApi, type DayTime, type Time, type Weekday } from '$lib/api';
	import { ORDERED_WEEKDAYS, WEEKDAY_LABELS } from '$lib/labels';
	import { Pencil, Plus, Trash2 } from '@lucide/svelte';

	interface DayForm {
		enabled: boolean;
		from: string;
		to: string;
	}

	let times = $state<Time[]>([]);
	let loading = $state(true);
	let listError = $state('');
	let search = $state('');

	let dialogOpen = $state(false);
	let editing = $state<Time | null>(null);
	let saving = $state(false);
	let formError = $state('');

	let name = $state('');
	let days = $state<Record<Weekday, DayForm>>(blankDays());

	let deleteTarget = $state<Time | null>(null);
	let deleting = $state(false);

	function blankDays(): Record<Weekday, DayForm> {
		return Object.fromEntries(
			ORDERED_WEEKDAYS.map((d) => [d, { enabled: false, from: '16:00', to: '18:00' }])
		) as Record<Weekday, DayForm>;
	}

	function activeDays(time: Time): string {
		const labels = ORDERED_WEEKDAYS.filter((d) => time[d]).map((d) => WEEKDAY_LABELS[d]);
		return labels.length ? labels.join('، ') : '—';
	}

	let filtered = $derived(times.filter((t) => !search || t.name.includes(search)));

	const columns: Column[] = [
		{ key: 'name', label: 'الاسم' },
		{ key: 'days', label: 'الأيام' },
		{ key: 'actions', label: 'إجراءات', class: 'w-px' }
	];

	async function load() {
		loading = true;
		listError = '';
		try {
			times = (await timesApi.list({ limit: 200 })).items;
		} catch (err) {
			listError = err instanceof ApiError ? err.message : 'تعذّر تحميل الأوقات.';
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		load();
	});

	function openCreate() {
		editing = null;
		name = '';
		days = blankDays();
		formError = '';
		dialogOpen = true;
	}

	function openEdit(time: Time) {
		editing = time;
		name = time.name;
		const next = blankDays();
		for (const d of ORDERED_WEEKDAYS) {
			const window = time[d];
			if (window) next[d] = { enabled: true, from: window.from, to: window.to };
		}
		days = next;
		formError = '';
		dialogOpen = true;
	}

	async function save() {
		if (saving) return;
		saving = true;
		formError = '';
		const schedule = Object.fromEntries(
			ORDERED_WEEKDAYS.map((d) => {
				const day = days[d];
				const value: DayTime | null =
					day.enabled && day.from && day.to ? { from: day.from, to: day.to } : null;
				return [d, value];
			})
		) as Record<Weekday, DayTime | null>;

		try {
			if (editing) {
				await timesApi.update(editing.id, { name, ...schedule });
			} else {
				await timesApi.create({ name, ...schedule });
			}
			dialogOpen = false;
			await load();
		} catch (err) {
			formError = err instanceof ApiError ? err.message : 'تعذّر حفظ الوقت.';
		} finally {
			saving = false;
		}
	}

	async function confirmDelete() {
		if (!deleteTarget) return;
		deleting = true;
		try {
			await timesApi.remove(deleteTarget.id);
			deleteTarget = null;
			await load();
		} catch (err) {
			listError = err instanceof ApiError ? err.message : 'تعذّر حذف الوقت.';
		} finally {
			deleting = false;
		}
	}
</script>

<div class="page-container">
	<PageHeader
		title="الأوقات"
		subtitle={`${times.length} وقت`}
		breadcrumbs={[{ label: 'لوحة التحكم' }, { label: 'الأوقات' }]}
	>
		{#snippet actions()}
			<Button onclick={openCreate}><Plus class="h-4 w-4" />إضافة وقت</Button>
		{/snippet}
	</PageHeader>

	<FilterBar searchPlaceholder="بحث بالاسم…" bind:searchValue={search} />

	{#if listError}
		<p class="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">{listError}</p>
	{/if}

	<DataTable {columns} rows={filtered} emptyMessage={loading ? 'جارٍ التحميل…' : 'لا توجد أوقات'}>
		{#snippet cell({ row, column })}
			{#if column.key === 'name'}
				<span class="font-medium">{row.name}</span>
			{:else if column.key === 'days'}
				<span class="text-sm text-muted-foreground">{activeDays(row)}</span>
			{:else if column.key === 'actions'}
				<div class="flex gap-1">
					<Button variant="ghost" size="icon" class="h-8 w-8" onclick={() => openEdit(row)}>
						<Pencil class="h-3.5 w-3.5" />
					</Button>
					<Button
						variant="ghost"
						size="icon"
						class="h-8 w-8 text-destructive"
						onclick={() => (deleteTarget = row)}
					>
						<Trash2 class="h-3.5 w-3.5" />
					</Button>
				</div>
			{/if}
		{/snippet}
	</DataTable>

	<Dialog bind:open={dialogOpen} title={editing ? 'تعديل وقت' : 'إضافة وقت'} class="max-w-xl">
		<form
			class="space-y-4"
			onsubmit={(e) => {
				e.preventDefault();
				save();
			}}
		>
			<div class="space-y-2">
				<Label for="name">اسم الوقت</Label>
				<Input id="name" bind:value={name} required placeholder="مثال: الفترة المسائية" />
			</div>

			<div class="space-y-2">
				<Label>أوقات الأيام</Label>
				<div class="space-y-1.5 rounded-lg border border-border p-2">
					{#each ORDERED_WEEKDAYS as day (day)}
						<div class="flex items-center gap-3 rounded-md px-2 py-1.5">
							<div class="flex w-28 items-center gap-2">
								<Switch bind:checked={days[day].enabled} />
								<span class="text-sm font-medium">{WEEKDAY_LABELS[day]}</span>
							</div>
							<div class="flex flex-1 items-center gap-2">
								<Input
									type="time"
									bind:value={days[day].from}
									disabled={!days[day].enabled}
									class="flex-1"
								/>
								<span class="text-muted-foreground">—</span>
								<Input
									type="time"
									bind:value={days[day].to}
									disabled={!days[day].enabled}
									class="flex-1"
								/>
							</div>
						</div>
					{/each}
				</div>
			</div>

			{#if formError}
				<p class="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">{formError}</p>
			{/if}

			<div class="flex justify-start gap-2 pt-2">
				<Button type="submit" disabled={saving}>{saving ? 'جارٍ الحفظ…' : 'حفظ'}</Button>
				<Button type="button" variant="outline" onclick={() => (dialogOpen = false)}>إلغاء</Button>
			</div>
		</form>
	</Dialog>

	<ConfirmDialog
		open={deleteTarget !== null}
		message={`سيتم حذف الوقت «${deleteTarget?.name ?? ''}». لا يمكن التراجع.`}
		loading={deleting}
		onConfirm={confirmDelete}
		onCancel={() => (deleteTarget = null)}
	/>
</div>
