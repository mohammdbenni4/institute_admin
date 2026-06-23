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
		studentsApi,
		teachersApi,
		type Halaqah,
		type OrphanStatus,
		type Student
	} from '$lib/api';
	import { ORPHAN_LABELS, formatDate } from '$lib/labels';
	import { whatsappLink } from '$lib/utils';
	import {
		ignoreUnmatchedHalaqahs,
		parseStudentsSheet,
		resolveHalaqahs,
		toCreatePayload,
		type ParseResult
	} from '$lib/import/students';
	import { goto } from '$app/navigation';
	import {
		AlertTriangle,
		CheckCircle2,
		FileSpreadsheet,
		Loader2,
		MessageCircle,
		Pencil,
		Plus,
		Trash2,
		Upload
	} from '@lucide/svelte';

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

	// ─── Excel import ──────────────────────────────────────────────────────────
	let fileInput = $state<HTMLInputElement | null>(null);
	let importOpen = $state(false);
	let importFileName = $state('');
	let importParsing = $state(false);
	let importResult = $state<ParseResult | null>(null);
	let importing = $state(false);
	let importError = $state('');
	let importedCount = $state(0);
	let creatingHalaqahs = $state(false);

	const canImport = $derived(
		!!importResult &&
			importResult.rows.length > 0 &&
			importResult.unmatchedHalaqahs.length === 0 &&
			!importing &&
			!creatingHalaqahs
	);

	function openImport() {
		fileInput?.click();
	}

	async function onFileChange(e: Event) {
		const input = e.currentTarget as HTMLInputElement;
		const file = input.files?.[0];
		input.value = ''; // allow re-selecting the same file
		if (!file) return;

		importError = '';
		importedCount = 0;
		importResult = null;
		importFileName = file.name;
		importOpen = true;
		importParsing = true;
		try {
			importResult = await parseStudentsSheet(file, halaqahs);
		} catch {
			importError = 'تعذّر قراءة الملف. تأكد أنه ملف Excel صالح يحتوي ورقة الطلاب.';
		} finally {
			importParsing = false;
		}
	}

	/** Treat unmatched halaqahs as "no halaqah" so the import can proceed. */
	function ignoreMissingHalaqahs() {
		if (!importResult) return;
		importResult = {
			...importResult,
			rows: ignoreUnmatchedHalaqahs(importResult.rows),
			unmatchedHalaqahs: []
		};
	}

	/** Create every missing halaqah (placeholder teacher + type), then re-resolve. */
	async function createMissingHalaqahs() {
		if (!importResult || importResult.unmatchedHalaqahs.length === 0) return;
		creatingHalaqahs = true;
		importError = '';
		try {
			const [teacherPage, typePage] = await Promise.all([
				teachersApi.list({ limit: 1 }),
				halaqahTypesApi.list({ limit: 1 })
			]);
			const teacher = teacherPage.items[0];
			const type = typePage.items[0];
			if (!teacher || !type) {
				importError = 'يجب إنشاء معلم واحد ونوع حلقة واحد على الأقل قبل إنشاء الحلقات.';
				return;
			}
			for (const name of importResult.unmatchedHalaqahs) {
				await halaqahsApi.create({
					name,
					teacher_id: teacher.id,
					halaqah_type_id: type.id
				});
			}
			// Refresh halaqahs, then re-match the parsed rows against the new list.
			halaqahs = (await halaqahsApi.list({ limit: 200 })).items;
			const resolved = resolveHalaqahs(importResult.rows, halaqahs);
			importResult = {
				...importResult,
				rows: resolved.rows,
				unmatchedHalaqahs: resolved.unmatchedHalaqahs
			};
		} catch (err) {
			importError = err instanceof ApiError ? err.message : 'تعذّر إنشاء الحلقات المفقودة.';
		} finally {
			creatingHalaqahs = false;
		}
	}

	async function confirmImport() {
		if (!importResult || !canImport) return;
		importing = true;
		importError = '';
		try {
			const items = importResult.rows.map(toCreatePayload);
			const res = await studentsApi.importBulk(items);
			importedCount = res.created;
			importResult = null;
			await load();
		} catch (err) {
			importError = err instanceof ApiError ? err.message : 'تعذّر استيراد الطلاب.';
		} finally {
			importing = false;
		}
	}

	function closeImport() {
		importOpen = false;
		importResult = null;
		importError = '';
		importedCount = 0;
		importFileName = '';
		creatingHalaqahs = false;
	}

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

	async function fetchAllStudents(): Promise<Student[]> {
		const PAGE = 200;
		const first = await studentsApi.list({ limit: PAGE, offset: 0 });
		let items = first.items;
		let offset = PAGE;
		while (items.length < first.total && offset < 5000) {
			const next = await studentsApi.list({ limit: PAGE, offset });
			if (next.items.length === 0) break;
			items = items.concat(next.items);
			offset += PAGE;
		}
		return items;
	}

	async function load() {
		loading = true;
		listError = '';
		try {
			const [studentList, halaqahPage] = await Promise.all([
				fetchAllStudents(),
				halaqahsApi.list({ limit: 200 })
			]);
			students = studentList;
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
			<Button variant="outline" onclick={openImport}>
				<FileSpreadsheet class="h-4 w-4" />استيراد من Excel
			</Button>
			<Button onclick={openCreate}><Plus class="h-4 w-4" />إضافة طالب</Button>
		{/snippet}
	</PageHeader>

	<input
		bind:this={fileInput}
		type="file"
		accept=".xlsx,.xls"
		class="hidden"
		onchange={onFileChange}
	/>

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

	<!-- ═══ Excel import preview ═══ -->
	<Dialog
		bind:open={importOpen}
		title="استيراد الطلاب من Excel"
		class="max-w-5xl"
		onOpenChange={(o) => !o && closeImport()}
	>
		{#if importParsing}
			<div class="flex items-center justify-center gap-2 py-12 text-muted-foreground">
				<Loader2 class="h-5 w-5 animate-spin" />
				جارٍ قراءة الملف…
			</div>
		{:else if importedCount > 0}
			<!-- success -->
			<div class="flex flex-col items-center gap-3 py-10 text-center">
				<CheckCircle2 class="h-12 w-12 text-emerald-500" />
				<p class="text-lg font-bold text-foreground">تم استيراد {importedCount} طالب بنجاح</p>
				<Button onclick={closeImport}>تم</Button>
			</div>
		{:else if importResult}
			{@const res = importResult}
			<div class="space-y-4">
				<!-- file + summary -->
				<div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
					<span class="flex items-center gap-1.5 font-medium text-foreground">
						<FileSpreadsheet class="h-4 w-4 text-primary" />{importFileName}
					</span>
					<span class="text-muted-foreground">
						{res.rows.length} صف جاهز للاستيراد
						{#if res.skippedNoName > 0}· تم تجاهل {res.skippedNoName} صف بلا اسم{/if}
					</span>
				</div>

				<!-- placeholder note -->
				{#if res.placeholderFatherName > 0 || res.placeholderFatherNumber > 0}
					<div
						class="flex items-start gap-2 rounded-lg bg-amber-500/10 px-3 py-2 text-xs text-amber-700 dark:text-amber-300"
					>
						<AlertTriangle class="mt-0.5 h-3.5 w-3.5 shrink-0" />
						<span>
							سيتم استخدام «—» كقيمة مؤقتة لـ
							{#if res.placeholderFatherName > 0}{res.placeholderFatherName} اسم أب{/if}
							{#if res.placeholderFatherName > 0 && res.placeholderFatherNumber > 0}
								و
							{/if}
							{#if res.placeholderFatherNumber > 0}{res.placeholderFatherNumber} رقم أب{/if}
							غير متوفرة في الملف.
						</span>
					</div>
				{/if}

				<!-- unmatched halaqahs (blocks import until resolved) -->
				{#if res.unmatchedHalaqahs.length > 0}
					<div
						class="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2.5 text-sm text-destructive"
					>
						<div class="flex items-center gap-1.5 font-semibold">
							<AlertTriangle class="h-4 w-4" />
							{res.unmatchedHalaqahs.length} حلقة غير موجودة في النظام
						</div>
						<div class="mt-2 flex flex-wrap gap-1.5">
							{#each res.unmatchedHalaqahs as name (name)}
								<span class="rounded-full bg-destructive/15 px-2 py-0.5 text-xs">{name}</span>
							{/each}
						</div>
						<div class="mt-3 flex flex-wrap gap-2">
							<Button size="sm" disabled={creatingHalaqahs} onclick={createMissingHalaqahs}>
								{#if creatingHalaqahs}
									<Loader2 class="h-3.5 w-3.5 animate-spin" />جارٍ إنشاء الحلقات…
								{:else}
									<Plus class="h-3.5 w-3.5" />إنشاء الحلقات المفقودة ({res.unmatchedHalaqahs
										.length})
								{/if}
							</Button>
							<Button
								size="sm"
								variant="outline"
								disabled={creatingHalaqahs}
								onclick={ignoreMissingHalaqahs}
							>
								تجاهل وحفظ الطلاب بدون حلقة
							</Button>
						</div>
						<p class="mt-2 text-xs text-destructive/80">
							الإنشاء يستخدم أول معلم ونوع حلقة كقيم مؤقتة — يمكنك تعديلها لاحقاً من صفحة الحلقات.
						</p>
					</div>
				{/if}

				<!-- preview table -->
				<div class="max-h-[45vh] overflow-auto rounded-xl border border-border">
					<table class="w-full border-collapse text-sm">
						<thead class="sticky top-0 bg-muted/80 backdrop-blur">
							<tr class="text-right text-xs text-muted-foreground">
								<th class="px-3 py-2 font-semibold">الطالب</th>
								<th class="px-3 py-2 font-semibold">الأب</th>
								<th class="px-3 py-2 font-semibold">الجوال</th>
								<th class="px-3 py-2 font-semibold">الحلقة</th>
								<th class="px-3 py-2 font-semibold">الميلاد</th>
								<th class="px-3 py-2 font-semibold">المنطقة</th>
							</tr>
						</thead>
						<tbody>
							{#each res.rows as row, i (i)}
								<tr class="border-t border-border">
									<td class="px-3 py-1.5 font-medium text-foreground">{row.full_name}</td>
									<td
										class={'px-3 py-1.5 ' +
											(row.fatherNamePlaceholder ? 'text-muted-foreground/50' : 'text-foreground')}
									>
										{row.father_name}
									</td>
									<td
										class={'px-3 py-1.5 ' +
											(row.fatherNumberPlaceholder
												? 'text-muted-foreground/50'
												: 'text-foreground')}
										dir="ltr"
									>
										{row.father_number}
									</td>
									<td class="px-3 py-1.5">
										{#if !row.halaqahMatched}
											<span
												class="rounded bg-destructive/10 px-1.5 py-0.5 text-xs text-destructive"
											>
												{row.halaqahName} (غير موجودة)
											</span>
										{:else if row.halaqah_id === null}
											<span class="text-muted-foreground/60">بدون حلقة</span>
										{:else}
											<span class="text-foreground">{row.halaqahName}</span>
										{/if}
									</td>
									<td class="px-3 py-1.5 text-muted-foreground" dir="ltr"
										>{row.date_of_birth ?? '—'}</td
									>
									<td
										class="max-w-[160px] truncate px-3 py-1.5 text-muted-foreground"
										title={row.residential_area ?? ''}
									>
										{row.residential_area ?? '—'}
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>

				{#if importError}
					<p class="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">
						{importError}
					</p>
				{/if}

				<div class="flex items-center justify-between gap-2 pt-1">
					<p class="text-xs text-muted-foreground">
						{#if res.unmatchedHalaqahs.length > 0}
							لا يمكن الاستيراد حتى تُنشأ الحلقات المفقودة.
						{:else}
							سيتم إنشاء {res.rows.length} طالب.
						{/if}
					</p>
					<div class="flex gap-2">
						<Button variant="outline" onclick={closeImport}>إلغاء</Button>
						<Button disabled={!canImport} onclick={confirmImport}>
							{#if importing}
								<Loader2 class="h-4 w-4 animate-spin" />جارٍ الاستيراد…
							{:else}
								<Upload class="h-4 w-4" />استيراد {res.rows.length} طالب
							{/if}
						</Button>
					</div>
				</div>
			</div>
		{:else if importError}
			<div class="space-y-4">
				<p class="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">{importError}</p>
				<div class="flex justify-start">
					<Button variant="outline" onclick={closeImport}>إغلاق</Button>
				</div>
			</div>
		{/if}
	</Dialog>
</div>
