<script lang="ts">
	import PageHeader from '$lib/components/shared/PageHeader.svelte';
	import FilterBar from '$lib/components/shared/FilterBar.svelte';
	import DataTable, { type Column } from '$lib/components/shared/DataTable.svelte';
	import StatusBadge from '$lib/components/shared/StatusBadge.svelte';
	import ConfirmDialog from '$lib/components/shared/ConfirmDialog.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import Dialog from '$lib/components/ui/Dialog.svelte';
	import Input from '$lib/components/ui/Input.svelte';
	import Label from '$lib/components/ui/Label.svelte';
	import Switch from '$lib/components/ui/Switch.svelte';
	import { ApiError, teachersApi, type Teacher } from '$lib/api';
	import { goto } from '$app/navigation';
	import { Pencil, Plus, Trash2 } from '@lucide/svelte';

	let teachers = $state<Teacher[]>([]);
	let loading = $state(true);
	let listError = $state('');
	let search = $state('');

	let dialogOpen = $state(false);
	let editing = $state<Teacher | null>(null);
	let saving = $state(false);
	let formError = $state('');

	let form = $state({
		full_name: '',
		email: '',
		password: '',
		academic_study: '',
		islamic_study: '',
		is_assistant: false,
		date_of_birth: '',
		is_active: true
	});

	let deleteTarget = $state<Teacher | null>(null);
	let deleting = $state(false);

	let filtered = $derived(
		teachers.filter((t) => !search || t.full_name.includes(search) || t.email.includes(search))
	);

	// Mirrors the backend password policy (RawPassword): a typed password must be
	// at least 6 characters. Empty is allowed while editing (keeps the current one).
	const PASSWORD_MIN_LENGTH = 6;
	let passwordTooShort = $derived(
		form.password.length > 0 && form.password.length < PASSWORD_MIN_LENGTH
	);

	const columns: Column[] = [
		{ key: 'full_name', label: 'الاسم' },
		{ key: 'email', label: 'البريد الإلكتروني' },
		{ key: 'academic_study', label: 'المؤهل الأكاديمي' },
		{ key: 'islamic_study', label: 'المؤهل الشرعي' },
		{ key: 'is_assistant', label: 'مساعد' },
		{ key: 'is_active', label: 'الحالة' },
		{ key: 'actions', label: 'إجراءات', class: 'w-px' }
	];

	async function load() {
		loading = true;
		listError = '';
		try {
			teachers = (await teachersApi.list({ limit: 200 })).items;
		} catch (err) {
			listError = err instanceof ApiError ? err.message : 'تعذّر تحميل المعلمين.';
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		load();
	});

	function openCreate() {
		editing = null;
		form = {
			full_name: '',
			email: '',
			password: '',
			academic_study: '',
			islamic_study: '',
			is_assistant: false,
			date_of_birth: '',
			is_active: true
		};
		formError = '';
		dialogOpen = true;
	}

	function openEdit(teacher: Teacher) {
		editing = teacher;
		form = {
			full_name: teacher.full_name,
			email: teacher.email,
			password: '',
			academic_study: teacher.academic_study,
			islamic_study: teacher.islamic_study,
			is_assistant: teacher.is_assistant,
			date_of_birth: teacher.date_of_birth ?? '',
			is_active: teacher.is_active
		};
		formError = '';
		dialogOpen = true;
	}

	async function save() {
		if (saving) return;
		if (passwordTooShort) {
			formError = `كلمة المرور قصيرة جدًا؛ يجب أن تتكون من ${PASSWORD_MIN_LENGTH} أحرف على الأقل.`;
			return;
		}
		saving = true;
		formError = '';
		try {
			const dob = form.date_of_birth || null;
			if (editing) {
				await teachersApi.update(editing.id, {
					full_name: form.full_name,
					email: form.email,
					academic_study: form.academic_study,
					islamic_study: form.islamic_study,
					is_assistant: form.is_assistant,
					date_of_birth: dob,
					is_active: form.is_active,
					...(form.password ? { password: form.password } : {})
				});
			} else {
				await teachersApi.create({
					full_name: form.full_name,
					email: form.email,
					password: form.password,
					academic_study: form.academic_study,
					islamic_study: form.islamic_study,
					is_assistant: form.is_assistant,
					date_of_birth: dob
				});
			}
			dialogOpen = false;
			await load();
		} catch (err) {
			formError = err instanceof ApiError ? err.message : 'تعذّر حفظ المعلم.';
		} finally {
			saving = false;
		}
	}

	async function confirmDelete() {
		if (!deleteTarget) return;
		deleting = true;
		try {
			await teachersApi.remove(deleteTarget.id);
			deleteTarget = null;
			await load();
		} catch (err) {
			listError = err instanceof ApiError ? err.message : 'تعذّر حذف المعلم.';
		} finally {
			deleting = false;
		}
	}
</script>

<div class="page-container">
	<PageHeader
		title="المعلمون"
		subtitle={`${teachers.length} معلم`}
		breadcrumbs={[{ label: 'لوحة التحكم' }, { label: 'المعلمون' }]}
	>
		{#snippet actions()}
			<Button onclick={openCreate}><Plus class="h-4 w-4" />إضافة معلم</Button>
		{/snippet}
	</PageHeader>

	<FilterBar searchPlaceholder="بحث بالاسم أو البريد…" bind:searchValue={search} />

	{#if listError}
		<p class="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">{listError}</p>
	{/if}

	<DataTable
		{columns}
		rows={filtered}
		onRowClick={(row) => goto(`/admin/teachers/${row.id}`)}
		emptyMessage={loading ? 'جارٍ التحميل…' : 'لا يوجد معلمون'}
	>
		{#snippet cell({ row, column, value })}
			{#if column.key === 'full_name'}
				<span class="font-medium text-primary">{row.full_name}</span>
			{:else if column.key === 'is_assistant'}
				<StatusBadge
					label={row.is_assistant ? 'نعم' : 'لا'}
					tone={row.is_assistant ? 'info' : 'neutral'}
				/>
			{:else if column.key === 'is_active'}
				<StatusBadge
					label={row.is_active ? 'نشط' : 'موقوف'}
					tone={row.is_active ? 'success' : 'neutral'}
				/>
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
				{value}
			{/if}
		{/snippet}
	</DataTable>

	<Dialog bind:open={dialogOpen} title={editing ? 'تعديل معلم' : 'إضافة معلم'}>
		<form
			class="space-y-4"
			onsubmit={(e) => {
				e.preventDefault();
				save();
			}}
		>
			<div class="space-y-2">
				<Label for="full_name">الاسم الكامل</Label>
				<Input id="full_name" bind:value={form.full_name} required />
			</div>
			<div class="space-y-2">
				<Label for="email">البريد الإلكتروني</Label>
				<Input id="email" type="email" bind:value={form.email} required />
			</div>
			<div class="space-y-2">
				<Label for="password">كلمة المرور {editing ? '(اتركها فارغة لإبقائها)' : ''}</Label>
				<Input
					id="password"
					type="password"
					bind:value={form.password}
					required={!editing}
					placeholder="••••••••"
					aria-invalid={passwordTooShort}
				/>
				{#if passwordTooShort}
					<p class="text-xs text-destructive">
						كلمة المرور قصيرة جدًا؛ يجب أن تتكون من {PASSWORD_MIN_LENGTH} أحرف على الأقل.
					</p>
				{:else}
					<p class="text-xs text-muted-foreground">{PASSWORD_MIN_LENGTH} أحرف على الأقل.</p>
				{/if}
			</div>
			<div class="grid grid-cols-2 gap-3">
				<div class="space-y-2">
					<Label for="academic">المؤهل الأكاديمي</Label>
					<Input id="academic" bind:value={form.academic_study} required />
				</div>
				<div class="space-y-2">
					<Label for="islamic">المؤهل الشرعي</Label>
					<Input id="islamic" bind:value={form.islamic_study} required />
				</div>
			</div>
			<div class="space-y-2">
				<Label for="dob">تاريخ الميلاد</Label>
				<Input id="dob" type="date" bind:value={form.date_of_birth} />
			</div>
			<div class="flex items-center justify-between rounded-lg bg-muted/30 px-3 py-2">
				<Label>معلم مساعد</Label>
				<Switch bind:checked={form.is_assistant} />
			</div>
			{#if editing}
				<div class="flex items-center justify-between rounded-lg bg-muted/30 px-3 py-2">
					<Label>الحساب نشط</Label>
					<Switch bind:checked={form.is_active} />
				</div>
			{/if}

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
		message={`سيتم حذف المعلم «${deleteTarget?.full_name ?? ''}». لا يمكن التراجع.`}
		loading={deleting}
		onConfirm={confirmDelete}
		onCancel={() => (deleteTarget = null)}
	/>
</div>
