<script lang="ts">
	import PageHeader from '$lib/components/shared/PageHeader.svelte';
	import FilterBar from '$lib/components/shared/FilterBar.svelte';
	import DataTable, { type Column } from '$lib/components/shared/DataTable.svelte';
	import ConfirmDialog from '$lib/components/shared/ConfirmDialog.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import Dialog from '$lib/components/ui/Dialog.svelte';
	import Input from '$lib/components/ui/Input.svelte';
	import Label from '$lib/components/ui/Label.svelte';
	import { ApiError, halaqahTypesApi, type HalaqahType } from '$lib/api';
	import { formatDate } from '$lib/labels';
	import { Pencil, Plus, Trash2 } from '@lucide/svelte';

	let types = $state<HalaqahType[]>([]);
	let loading = $state(true);
	let listError = $state('');
	let search = $state('');

	let dialogOpen = $state(false);
	let editing = $state<HalaqahType | null>(null);
	let saving = $state(false);
	let formError = $state('');
	let name = $state('');

	let deleteTarget = $state<HalaqahType | null>(null);
	let deleting = $state(false);

	let filtered = $derived(types.filter((t) => !search || t.name.includes(search)));

	const columns: Column[] = [
		{ key: 'name', label: 'الاسم' },
		{ key: 'created_at', label: 'تاريخ الإنشاء' },
		{ key: 'actions', label: 'إجراءات', class: 'w-px' }
	];

	async function load() {
		loading = true;
		listError = '';
		try {
			types = (await halaqahTypesApi.list({ limit: 200 })).items;
		} catch (err) {
			listError = err instanceof ApiError ? err.message : 'تعذّر تحميل أنواع الحلقات.';
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
		formError = '';
		dialogOpen = true;
	}

	function openEdit(type: HalaqahType) {
		editing = type;
		name = type.name;
		formError = '';
		dialogOpen = true;
	}

	async function save() {
		if (saving) return;
		saving = true;
		formError = '';
		try {
			if (editing) {
				await halaqahTypesApi.update(editing.id, { name });
			} else {
				await halaqahTypesApi.create({ name });
			}
			dialogOpen = false;
			await load();
		} catch (err) {
			formError = err instanceof ApiError ? err.message : 'تعذّر حفظ النوع.';
		} finally {
			saving = false;
		}
	}

	async function confirmDelete() {
		if (!deleteTarget) return;
		deleting = true;
		try {
			await halaqahTypesApi.remove(deleteTarget.id);
			deleteTarget = null;
			await load();
		} catch (err) {
			listError = err instanceof ApiError ? err.message : 'تعذّر حذف النوع.';
		} finally {
			deleting = false;
		}
	}
</script>

<div class="page-container">
	<PageHeader
		title="أنواع الحلقات"
		subtitle={`${types.length} نوع`}
		breadcrumbs={[{ label: 'لوحة التحكم' }, { label: 'أنواع الحلقات' }]}
	>
		{#snippet actions()}
			<Button onclick={openCreate}><Plus class="h-4 w-4" />إضافة نوع</Button>
		{/snippet}
	</PageHeader>

	<FilterBar searchPlaceholder="بحث بالاسم…" bind:searchValue={search} />

	{#if listError}
		<p class="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">{listError}</p>
	{/if}

	<DataTable {columns} rows={filtered} emptyMessage={loading ? 'جارٍ التحميل…' : 'لا توجد أنواع'}>
		{#snippet cell({ row, column, value })}
			{#if column.key === 'name'}
				<span class="font-medium">{row.name}</span>
			{:else if column.key === 'created_at'}
				{formatDate(row.created_at)}
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
			{:else}
				{value}
			{/if}
		{/snippet}
	</DataTable>

	<Dialog bind:open={dialogOpen} title={editing ? 'تعديل نوع' : 'إضافة نوع'} class="max-w-sm">
		<form
			class="space-y-4"
			onsubmit={(e) => {
				e.preventDefault();
				save();
			}}
		>
			<div class="space-y-2">
				<Label for="name">اسم النوع</Label>
				<Input id="name" bind:value={name} required />
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
		message={`سيتم حذف النوع «${deleteTarget?.name ?? ''}». لا يمكن التراجع.`}
		loading={deleting}
		onConfirm={confirmDelete}
		onCancel={() => (deleteTarget = null)}
	/>
</div>
