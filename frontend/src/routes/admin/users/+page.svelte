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
	import Select from '$lib/components/ui/Select.svelte';
	import Switch from '$lib/components/ui/Switch.svelte';
	import { ApiError, usersApi, type User, type UserRole } from '$lib/api';
	import { ROLE_LABELS, formatDate } from '$lib/labels';
	import { Pencil, Plus, Trash2 } from '@lucide/svelte';

	const roleOptions = (Object.keys(ROLE_LABELS) as UserRole[]).map((value) => ({
		value,
		label: ROLE_LABELS[value]
	}));

	let users = $state<User[]>([]);
	let loading = $state(true);
	let listError = $state('');
	let search = $state('');
	let roleFilter = $state('all');

	let dialogOpen = $state(false);
	let editing = $state<User | null>(null);
	let saving = $state(false);
	let formError = $state('');

	let form = $state({
		full_name: '',
		email: '',
		password: '',
		role: 'teacher' as UserRole,
		date_of_birth: '',
		is_active: true
	});

	let deleteTarget = $state<User | null>(null);
	let deleting = $state(false);

	let filtered = $derived(
		users.filter((u) => {
			if (roleFilter !== 'all' && u.role !== roleFilter) return false;
			if (search && !u.full_name.includes(search) && !u.email.includes(search)) return false;
			return true;
		})
	);

	const columns: Column[] = [
		{ key: 'full_name', label: 'الاسم' },
		{ key: 'email', label: 'البريد الإلكتروني' },
		{ key: 'role', label: 'الدور' },
		{ key: 'date_of_birth', label: 'تاريخ الميلاد' },
		{ key: 'is_active', label: 'الحالة' },
		{ key: 'actions', label: 'إجراءات', class: 'w-px' }
	];

	async function load() {
		loading = true;
		listError = '';
		try {
			users = (await usersApi.list({ limit: 200 })).items;
		} catch (err) {
			listError = err instanceof ApiError ? err.message : 'تعذّر تحميل المستخدمين.';
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
			role: 'teacher',
			date_of_birth: '',
			is_active: true
		};
		formError = '';
		dialogOpen = true;
	}

	function openEdit(user: User) {
		editing = user;
		form = {
			full_name: user.full_name,
			email: user.email,
			password: '',
			role: user.role,
			date_of_birth: user.date_of_birth ?? '',
			is_active: user.is_active
		};
		formError = '';
		dialogOpen = true;
	}

	async function save() {
		if (saving) return;
		saving = true;
		formError = '';
		try {
			const dob = form.date_of_birth || null;
			if (editing) {
				await usersApi.update(editing.id, {
					full_name: form.full_name,
					email: form.email,
					role: form.role,
					date_of_birth: dob,
					is_active: form.is_active,
					...(form.password ? { password: form.password } : {})
				});
			} else {
				await usersApi.create({
					full_name: form.full_name,
					email: form.email,
					password: form.password,
					role: form.role,
					date_of_birth: dob,
					is_active: form.is_active
				});
			}
			dialogOpen = false;
			await load();
		} catch (err) {
			formError = err instanceof ApiError ? err.message : 'تعذّر حفظ المستخدم.';
		} finally {
			saving = false;
		}
	}

	async function confirmDelete() {
		if (!deleteTarget) return;
		deleting = true;
		try {
			await usersApi.remove(deleteTarget.id);
			deleteTarget = null;
			await load();
		} catch (err) {
			listError = err instanceof ApiError ? err.message : 'تعذّر حذف المستخدم.';
		} finally {
			deleting = false;
		}
	}
</script>

<div class="page-container">
	<PageHeader
		title="المستخدمون"
		subtitle={`${users.length} مستخدم`}
		breadcrumbs={[{ label: 'لوحة التحكم' }, { label: 'المستخدمون' }]}
	>
		{#snippet actions()}
			<Button onclick={openCreate}><Plus class="h-4 w-4" />إضافة مستخدم</Button>
		{/snippet}
	</PageHeader>

	<FilterBar
		searchPlaceholder="بحث بالاسم أو البريد…"
		bind:searchValue={search}
		filters={[
			{ label: 'الدور', options: roleOptions, value: roleFilter, onChange: (v) => (roleFilter = v) }
		]}
	/>

	{#if listError}
		<p class="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">{listError}</p>
	{/if}

	<DataTable
		{columns}
		rows={filtered}
		emptyMessage={loading ? 'جارٍ التحميل…' : 'لا يوجد مستخدمون'}
	>
		{#snippet cell({ row, column, value })}
			{#if column.key === 'full_name'}
				<span class="font-medium">{row.full_name}</span>
			{:else if column.key === 'role'}
				{ROLE_LABELS[row.role as UserRole]}
			{:else if column.key === 'date_of_birth'}
				{formatDate(row.date_of_birth)}
			{:else if column.key === 'is_active'}
				<StatusBadge
					label={row.is_active ? 'نشط' : 'موقوف'}
					tone={row.is_active ? 'success' : 'neutral'}
				/>
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

	<Dialog bind:open={dialogOpen} title={editing ? 'تعديل مستخدم' : 'إضافة مستخدم'}>
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
				/>
			</div>
			<div class="grid grid-cols-2 gap-3">
				<div class="space-y-2">
					<Label>الدور</Label>
					<Select bind:value={form.role} options={roleOptions} />
				</div>
				<div class="space-y-2">
					<Label for="dob">تاريخ الميلاد</Label>
					<Input id="dob" type="date" bind:value={form.date_of_birth} />
				</div>
			</div>
			<div class="flex items-center justify-between rounded-lg bg-muted/30 px-3 py-2">
				<Label>الحساب نشط</Label>
				<Switch bind:checked={form.is_active} />
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
		message={`سيتم حذف المستخدم «${deleteTarget?.full_name ?? ''}». لا يمكن التراجع.`}
		loading={deleting}
		onConfirm={confirmDelete}
		onCancel={() => (deleteTarget = null)}
	/>
</div>
