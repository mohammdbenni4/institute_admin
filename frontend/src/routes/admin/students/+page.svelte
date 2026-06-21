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
		studentsApi,
		type Halaqah,
		type OrphanStatus,
		type Student
	} from '$lib/api';
	import { ORPHAN_LABELS, formatDate } from '$lib/labels';
	import { whatsappLink } from '$lib/utils';
	import { goto } from '$app/navigation';
	import { MessageCircle, Pencil, Plus, Trash2 } from '@lucide/svelte';

	function contactParent(student: Student) {
		const link = whatsappLink(
			student.father_number,
			`السلام عليكم ورحمة الله، بخصوص الطالب ${student.full_name} في حلقة القرآن.`
		);
		if (link) window.open(link, '_blank', 'noopener');
	}

	const orphanOptions = [
		{ value: '', label: 'غير يتيم' },
		...(Object.keys(ORPHAN_LABELS) as OrphanStatus[]).map((value) => ({
			value,
			label: ORPHAN_LABELS[value]
		}))
	];

	let students = $state<Student[]>([]);
	let halaqahs = $state<Halaqah[]>([]);
	let loading = $state(true);
	let listError = $state('');
	let search = $state('');
	let halaqahFilter = $state('all');

	let dialogOpen = $state(false);
	let editing = $state<Student | null>(null);
	let saving = $state(false);
	let formError = $state('');

	const emptyForm = () => ({
		full_name: '',
		father_name: '',
		father_number: '',
		mother_number: '',
		date_of_birth: '',
		orphan_of: '' as OrphanStatus | '',
		residential_area: '',
		accepted_at: '',
		notes: '',
		halaqah_id: ''
	});
	let form = $state(emptyForm());

	let deleteTarget = $state<Student | null>(null);
	let deleting = $state(false);

	let halaqahName = $derived((id: string | null) => halaqahs.find((h) => h.id === id)?.name ?? '—');
	let halaqahOptions = $derived([
		{ value: '', label: 'بدون حلقة' },
		...halaqahs.map((h) => ({ value: h.id, label: h.name }))
	]);

	let filtered = $derived(
		students.filter((s) => {
			if (halaqahFilter !== 'all' && (s.halaqah_id ?? '') !== halaqahFilter) return false;
			if (search && !s.full_name.includes(search) && !s.father_name.includes(search)) return false;
			return true;
		})
	);

	const columns: Column[] = [
		{ key: 'full_name', label: 'اسم الطالب' },
		{ key: 'father_name', label: 'اسم الأب' },
		{ key: 'father_number', label: 'جوال الأب' },
		{ key: 'halaqah_id', label: 'الحلقة' },
		{ key: 'accepted_at', label: 'تاريخ القبول' },
		{ key: 'actions', label: 'إجراءات', class: 'w-px' }
	];

	async function load() {
		loading = true;
		listError = '';
		try {
			const [studentPage, halaqahPage] = await Promise.all([
				studentsApi.list({ limit: 200 }),
				halaqahsApi.list({ limit: 200 })
			]);
			students = studentPage.items;
			halaqahs = halaqahPage.items;
		} catch (err) {
			listError = err instanceof ApiError ? err.message : 'تعذّر تحميل الطلاب.';
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

	function openEdit(student: Student) {
		editing = student;
		form = {
			full_name: student.full_name,
			father_name: student.father_name,
			father_number: student.father_number,
			mother_number: student.mother_number ?? '',
			date_of_birth: student.date_of_birth ?? '',
			orphan_of: student.orphan_of ?? '',
			residential_area: student.residential_area ?? '',
			accepted_at: student.accepted_at ?? '',
			notes: student.notes ?? '',
			halaqah_id: student.halaqah_id ?? ''
		};
		formError = '';
		dialogOpen = true;
	}

	async function save() {
		if (saving) return;
		saving = true;
		formError = '';
		const payload = {
			full_name: form.full_name,
			father_name: form.father_name,
			father_number: form.father_number,
			mother_number: form.mother_number || null,
			date_of_birth: form.date_of_birth || null,
			orphan_of: form.orphan_of || null,
			residential_area: form.residential_area || null,
			accepted_at: form.accepted_at || null,
			notes: form.notes || null,
			halaqah_id: form.halaqah_id || null
		};
		try {
			if (editing) {
				await studentsApi.update(editing.id, payload);
			} else {
				await studentsApi.create(payload);
			}
			dialogOpen = false;
			await load();
		} catch (err) {
			formError = err instanceof ApiError ? err.message : 'تعذّر حفظ الطالب.';
		} finally {
			saving = false;
		}
	}

	async function confirmDelete() {
		if (!deleteTarget) return;
		deleting = true;
		try {
			await studentsApi.remove(deleteTarget.id);
			deleteTarget = null;
			await load();
		} catch (err) {
			listError = err instanceof ApiError ? err.message : 'تعذّر حذف الطالب.';
		} finally {
			deleting = false;
		}
	}
</script>

<div class="page-container">
	<PageHeader
		title="الطلاب"
		subtitle={`${students.length} طالب`}
		breadcrumbs={[{ label: 'لوحة التحكم' }, { label: 'الطلاب' }]}
	>
		{#snippet actions()}
			<Button onclick={openCreate}><Plus class="h-4 w-4" />إضافة طالب</Button>
		{/snippet}
	</PageHeader>

	<FilterBar
		searchPlaceholder="بحث باسم الطالب أو الأب…"
		bind:searchValue={search}
		filters={[
			{
				label: 'الحلقة',
				options: halaqahs.map((h) => ({ value: h.id, label: h.name })),
				value: halaqahFilter,
				onChange: (v) => (halaqahFilter = v)
			}
		]}
	/>

	{#if listError}
		<p class="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">{listError}</p>
	{/if}

	<DataTable
		{columns}
		rows={filtered}
		onRowClick={(row) => goto(`/admin/students/${row.id}`)}
		emptyMessage={loading ? 'جارٍ التحميل…' : 'لا يوجد طلاب'}
	>
		{#snippet cell({ row, column, value })}
			{#if column.key === 'full_name'}
				<span class="font-medium text-primary">{row.full_name}</span>
			{:else if column.key === 'halaqah_id'}
				{halaqahName(row.halaqah_id)}
			{:else if column.key === 'accepted_at'}
				{formatDate(row.accepted_at)}
			{:else if column.key === 'actions'}
				<div class="flex gap-1">
					<Button
						variant="ghost"
						size="icon"
						class="h-8 w-8 text-emerald-600"
						title="تواصل مع الأهل"
						disabled={!row.father_number}
						onclick={(e) => {
							e.stopPropagation();
							contactParent(row);
						}}
					>
						<MessageCircle class="h-3.5 w-3.5" />
					</Button>
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

	<Dialog bind:open={dialogOpen} title={editing ? 'تعديل طالب' : 'إضافة طالب'} class="max-w-2xl">
		<form
			class="space-y-4"
			onsubmit={(e) => {
				e.preventDefault();
				save();
			}}
		>
			<div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
				<div class="space-y-2">
					<Label for="full_name">اسم الطالب</Label>
					<Input id="full_name" bind:value={form.full_name} required />
				</div>
				<div class="space-y-2">
					<Label for="father_name">اسم الأب</Label>
					<Input id="father_name" bind:value={form.father_name} required />
				</div>
				<div class="space-y-2">
					<Label for="father_number">جوال الأب</Label>
					<Input id="father_number" bind:value={form.father_number} required />
				</div>
				<div class="space-y-2">
					<Label for="mother_number">جوال الأم</Label>
					<Input id="mother_number" bind:value={form.mother_number} />
				</div>
				<div class="space-y-2">
					<Label for="dob">تاريخ الميلاد</Label>
					<Input id="dob" type="date" bind:value={form.date_of_birth} />
				</div>
				<div class="space-y-2">
					<Label for="accepted">تاريخ القبول</Label>
					<Input id="accepted" type="date" bind:value={form.accepted_at} />
				</div>
				<div class="space-y-2">
					<Label>حالة اليتم</Label>
					<Select bind:value={form.orphan_of} options={orphanOptions} />
				</div>
				<div class="space-y-2">
					<Label>الحلقة</Label>
					<Select bind:value={form.halaqah_id} options={halaqahOptions} placeholder="بدون حلقة" />
				</div>
				<div class="space-y-2 sm:col-span-2">
					<Label for="area">منطقة السكن</Label>
					<Input id="area" bind:value={form.residential_area} />
				</div>
				<div class="space-y-2 sm:col-span-2">
					<Label for="notes">ملاحظات</Label>
					<Input id="notes" bind:value={form.notes} />
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
		message={`سيتم حذف الطالب «${deleteTarget?.full_name ?? ''}». لا يمكن التراجع.`}
		loading={deleting}
		onConfirm={confirmDelete}
		onCancel={() => (deleteTarget = null)}
	/>
</div>
