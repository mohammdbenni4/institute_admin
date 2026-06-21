<script lang="ts">
	import PageHeader from '$lib/components/shared/PageHeader.svelte';
	import FilterBar from '$lib/components/shared/FilterBar.svelte';
	import DataTable, { type Column } from '$lib/components/shared/DataTable.svelte';
	import ConfirmDialog from '$lib/components/shared/ConfirmDialog.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import Dialog from '$lib/components/ui/Dialog.svelte';
	import Input from '$lib/components/ui/Input.svelte';
	import Label from '$lib/components/ui/Label.svelte';
	import Select from '$lib/components/ui/Select.svelte';
	import {
		ApiError,
		halaqahsApi,
		halaqahTypesApi,
		teachersApi,
		timesApi,
		type Halaqah,
		type HalaqahType,
		type Teacher,
		type Time
	} from '$lib/api';
	import { goto } from '$app/navigation';
	import { Pencil, Plus, Trash2 } from '@lucide/svelte';

	let halaqahs = $state<Halaqah[]>([]);
	let teachers = $state<Teacher[]>([]);
	let types = $state<HalaqahType[]>([]);
	let times = $state<Time[]>([]);
	let loading = $state(true);
	let listError = $state('');
	let search = $state('');
	let teacherFilter = $state('all');
	let typeFilter = $state('all');

	let dialogOpen = $state(false);
	let editing = $state<Halaqah | null>(null);
	let saving = $state(false);
	let formError = $state('');

	const emptyForm = () => ({
		name: '',
		teacher_id: '',
		halaqah_type_id: '',
		level: '',
		age: '',
		time_id: ''
	});
	let form = $state(emptyForm());

	let deleteTarget = $state<Halaqah | null>(null);
	let deleting = $state(false);

	let teacherOptions = $derived(teachers.map((t) => ({ value: t.id, label: t.full_name })));
	let typeOptions = $derived(types.map((t) => ({ value: t.id, label: t.name })));
	let timeOptions = $derived([
		{ value: '', label: 'بدون وقت' },
		...times.map((t) => ({ value: t.id, label: t.name }))
	]);

	let filtered = $derived(
		halaqahs.filter((h) => {
			if (teacherFilter !== 'all' && h.teacher_id !== teacherFilter) return false;
			if (typeFilter !== 'all' && h.halaqah_type_id !== typeFilter) return false;
			if (search && !h.name.includes(search) && !h.teacher_name.includes(search)) return false;
			return true;
		})
	);

	const columns: Column[] = [
		{ key: 'name', label: 'اسم الحلقة' },
		{ key: 'teacher_name', label: 'المعلم' },
		{ key: 'halaqah_type_name', label: 'النوع' },
		{ key: 'level', label: 'المستوى' },
		{ key: 'number_of_students', label: 'عدد الطلاب' },
		{ key: 'actions', label: 'إجراءات', class: 'w-px' }
	];

	async function load() {
		loading = true;
		listError = '';
		try {
			const [h, t, ty, ti] = await Promise.all([
				halaqahsApi.list({ limit: 200 }),
				teachersApi.list({ limit: 200 }),
				halaqahTypesApi.list({ limit: 200 }),
				timesApi.list({ limit: 200 })
			]);
			halaqahs = h.items;
			teachers = t.items;
			types = ty.items;
			times = ti.items;
		} catch (err) {
			listError = err instanceof ApiError ? err.message : 'تعذّر تحميل الحلقات.';
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		load();
	});

	function openCreate() {
		editing = null;
		form = emptyForm();
		formError = '';
		dialogOpen = true;
	}

	function openEdit(halaqah: Halaqah) {
		editing = halaqah;
		form = {
			name: halaqah.name,
			teacher_id: halaqah.teacher_id,
			halaqah_type_id: halaqah.halaqah_type_id,
			level: halaqah.level ?? '',
			age: halaqah.age ?? '',
			time_id: halaqah.time_id ?? ''
		};
		formError = '';
		dialogOpen = true;
	}

	async function save() {
		if (saving) return;
		if (!form.teacher_id || !form.halaqah_type_id) {
			formError = 'يرجى اختيار المعلم ونوع الحلقة.';
			return;
		}
		saving = true;
		formError = '';
		const payload = {
			name: form.name,
			teacher_id: form.teacher_id,
			halaqah_type_id: form.halaqah_type_id,
			level: form.level || null,
			age: form.age || null,
			time_id: form.time_id || null
		};
		try {
			if (editing) {
				await halaqahsApi.update(editing.id, payload);
			} else {
				await halaqahsApi.create(payload);
			}
			dialogOpen = false;
			await load();
		} catch (err) {
			formError = err instanceof ApiError ? err.message : 'تعذّر حفظ الحلقة.';
		} finally {
			saving = false;
		}
	}

	async function confirmDelete() {
		if (!deleteTarget) return;
		deleting = true;
		try {
			await halaqahsApi.remove(deleteTarget.id);
			deleteTarget = null;
			await load();
		} catch (err) {
			listError = err instanceof ApiError ? err.message : 'تعذّر حذف الحلقة.';
		} finally {
			deleting = false;
		}
	}
</script>

<div class="page-container">
	<PageHeader
		title="الحلقات"
		subtitle={`${halaqahs.length} حلقة`}
		breadcrumbs={[{ label: 'لوحة التحكم' }, { label: 'الحلقات' }]}
	>
		{#snippet actions()}
			<Button onclick={openCreate}><Plus class="h-4 w-4" />إضافة حلقة</Button>
		{/snippet}
	</PageHeader>

	<FilterBar
		searchPlaceholder="بحث باسم الحلقة أو المعلم…"
		bind:searchValue={search}
		filters={[
			{
				label: 'المعلم',
				options: teacherOptions,
				value: teacherFilter,
				onChange: (v) => (teacherFilter = v)
			},
			{
				label: 'النوع',
				options: typeOptions,
				value: typeFilter,
				onChange: (v) => (typeFilter = v)
			}
		]}
	/>

	{#if listError}
		<p class="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">{listError}</p>
	{/if}

	<DataTable
		{columns}
		rows={filtered}
		onRowClick={(row) => goto(`/admin/halaqahs/${row.id}`)}
		emptyMessage={loading ? 'جارٍ التحميل…' : 'لا توجد حلقات'}
	>
		{#snippet cell({ row, column, value })}
			{#if column.key === 'name'}
				<span class="font-medium text-primary">{row.name}</span>
			{:else if column.key === 'actions'}
				<div class="flex gap-1">
					<Button
						variant="ghost"
						size="icon"
						class="h-8 w-8"
						onclick={(e) => {
							e.stopPropagation();
							openEdit(row);
						}}
					>
						<Pencil class="h-3.5 w-3.5" />
					</Button>
					<Button
						variant="ghost"
						size="icon"
						class="h-8 w-8 text-destructive"
						onclick={(e) => {
							e.stopPropagation();
							deleteTarget = row;
						}}
					>
						<Trash2 class="h-3.5 w-3.5" />
					</Button>
				</div>
			{:else}
				{value ?? '—'}
			{/if}
		{/snippet}
	</DataTable>

	<Dialog bind:open={dialogOpen} title={editing ? 'تعديل حلقة' : 'إضافة حلقة'}>
		<form
			class="space-y-4"
			onsubmit={(e) => {
				e.preventDefault();
				save();
			}}
		>
			<div class="space-y-2">
				<Label for="name">اسم الحلقة</Label>
				<Input id="name" bind:value={form.name} required />
			</div>
			<div class="space-y-2">
				<Label>المعلم</Label>
				<Select bind:value={form.teacher_id} options={teacherOptions} placeholder="اختر المعلم" />
			</div>
			<div class="space-y-2">
				<Label>نوع الحلقة</Label>
				<Select bind:value={form.halaqah_type_id} options={typeOptions} placeholder="اختر النوع" />
			</div>
			<div class="grid grid-cols-2 gap-3">
				<div class="space-y-2">
					<Label for="level">المستوى</Label>
					<Input id="level" bind:value={form.level} />
				</div>
				<div class="space-y-2">
					<Label for="age">الفئة العمرية</Label>
					<Input id="age" bind:value={form.age} />
				</div>
			</div>
			<div class="space-y-2">
				<Label>الوقت</Label>
				<Select bind:value={form.time_id} options={timeOptions} placeholder="بدون وقت" />
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
		message={`سيتم حذف الحلقة «${deleteTarget?.name ?? ''}». لا يمكن التراجع.`}
		loading={deleting}
		onConfirm={confirmDelete}
		onCancel={() => (deleteTarget = null)}
	/>
</div>
