<script lang="ts">
	import { onMount } from 'svelte';
	import { Plus, Pencil, Trash2, ChevronDown, ChevronUp, AlertTriangle } from '@lucide/svelte';
	import { problemLevelsApi, problemsApi } from '$lib/api/resources';
	import type { Problem, ProblemLevel, UUID } from '$lib/api/types';

	// ----- state ---------------------------------------------------------------
	let levels = $state<ProblemLevel[]>([]);
	let problems = $state<Problem[]>([]);
	let loading = $state(true);
	let error = $state('');
	let success = $state('');

	// expanded level accordion
	let expandedLevels = $state<Set<UUID>>(new Set());

	// ----- level form ----------------------------------------------------------
	let showLevelForm = $state(false);
	let levelForm = $state({ id: '' as UUID | '', name: '' });
	let levelSubmitting = $state(false);

	// ----- problem form --------------------------------------------------------
	let showProblemForm = $state(false);
	let problemForm = $state({ id: '' as UUID | '', name: '', level_id: '' as UUID | '' });
	let problemSubmitting = $state(false);

	// ----- delete confirm -------------------------------------------------------
	let deleteTarget = $state<{ kind: 'level' | 'problem'; id: UUID; name: string } | null>(null);
	let deleteSubmitting = $state(false);

	// ----- derived: group problems by level ------------------------------------
	let problemsByLevel = $derived.by(() => {
		const map = new Map<UUID, Problem[]>();
		for (const lvl of levels) map.set(lvl.id, []);
		for (const p of problems) {
			const arr = map.get(p.level_id);
			if (arr) arr.push(p);
		}
		return map;
	});

	onMount(load);

	async function load() {
		loading = true;
		error = '';
		try {
			const [lvlRes, probRes] = await Promise.all([
				problemLevelsApi.list({ limit: 200 }),
				problemsApi.list({ limit: 500 })
			]);
			levels = lvlRes.items;
			problems = probRes.items;
			// expand all by default
			expandedLevels = new Set(levels.map((l) => l.id));
		} catch {
			error = 'فشل تحميل البيانات';
		} finally {
			loading = false;
		}
	}

	function flash(msg: string) {
		success = msg;
		setTimeout(() => (success = ''), 3000);
	}

	// ----- level CRUD ----------------------------------------------------------
	function openLevelCreate() {
		levelForm = { id: '', name: '' };
		showLevelForm = true;
	}

	function openLevelEdit(lvl: ProblemLevel) {
		levelForm = { id: lvl.id, name: lvl.name };
		showLevelForm = true;
	}

	async function submitLevel() {
		if (!levelForm.name.trim()) return;
		levelSubmitting = true;
		error = '';
		try {
			if (levelForm.id) {
				await problemLevelsApi.update(levelForm.id, { name: levelForm.name });
				flash('تم تحديث المستوى');
			} else {
				await problemLevelsApi.create({ name: levelForm.name });
				flash('تم إضافة المستوى');
			}
			showLevelForm = false;
			await load();
		} catch {
			error = 'فشل حفظ المستوى';
		} finally {
			levelSubmitting = false;
		}
	}

	// ----- problem CRUD --------------------------------------------------------
	function openProblemCreate(levelId?: UUID) {
		problemForm = { id: '', name: '', level_id: levelId ?? '' };
		showProblemForm = true;
	}

	function openProblemEdit(p: Problem) {
		problemForm = { id: p.id, name: p.name, level_id: p.level_id };
		showProblemForm = true;
	}

	async function submitProblem() {
		if (!problemForm.name.trim() || !problemForm.level_id) return;
		problemSubmitting = true;
		error = '';
		try {
			if (problemForm.id) {
				await problemsApi.update(problemForm.id, {
					name: problemForm.name,
					level_id: problemForm.level_id
				});
				flash('تم تحديث الصعوبة');
			} else {
				await problemsApi.create({ name: problemForm.name, level_id: problemForm.level_id });
				flash('تم إضافة الصعوبة');
			}
			showProblemForm = false;
			await load();
		} catch {
			error = 'فشل حفظ الصعوبة';
		} finally {
			problemSubmitting = false;
		}
	}

	// ----- delete --------------------------------------------------------------
	function confirmDelete(kind: 'level' | 'problem', id: UUID, name: string) {
		deleteTarget = { kind, id, name };
	}

	async function doDelete() {
		if (!deleteTarget) return;
		deleteSubmitting = true;
		error = '';
		try {
			if (deleteTarget.kind === 'level') {
				await problemLevelsApi.remove(deleteTarget.id);
				flash('تم حذف المستوى');
			} else {
				await problemsApi.remove(deleteTarget.id);
				flash('تم حذف الصعوبة');
			}
			deleteTarget = null;
			await load();
		} catch {
			error =
				deleteTarget?.kind === 'level' ? 'لا يمكن حذف مستوى يحتوي صعوبات' : 'فشل الحذف';
		} finally {
			deleteSubmitting = false;
		}
	}

	function toggleLevel(id: UUID) {
		const next = new Set(expandedLevels);
		if (next.has(id)) next.delete(id);
		else next.add(id);
		expandedLevels = next;
	}
</script>

<div class="space-y-6" dir="rtl">
	<!-- header -->
	<div class="flex items-center justify-between">
		<div class="flex items-center gap-3">
			<AlertTriangle class="h-6 w-6 text-warning" />
			<h1 class="text-2xl font-bold text-foreground">الصعوبات</h1>
		</div>
		<div class="flex gap-2">
			<button
				onclick={openLevelCreate}
				class="flex items-center gap-2 rounded-lg bg-secondary px-4 py-2 text-sm font-medium text-secondary-foreground hover:bg-secondary/80"
			>
				<Plus class="h-4 w-4" />
				مستوى جديد
			</button>
			<button
				onclick={() => openProblemCreate()}
				class="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
			>
				<Plus class="h-4 w-4" />
				صعوبة جديدة
			</button>
		</div>
	</div>

	<!-- feedback banners -->
	{#if error}
		<div class="rounded-lg bg-destructive/10 px-4 py-3 text-sm text-destructive">{error}</div>
	{/if}
	{#if success}
		<div class="rounded-lg bg-success/10 px-4 py-3 text-sm text-success">{success}</div>
	{/if}

	<!-- loading -->
	{#if loading}
		<div class="flex justify-center py-12">
			<div class="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent"></div>
		</div>
	{:else if levels.length === 0}
		<div class="rounded-xl border border-dashed border-border p-12 text-center text-muted-foreground">
			لا توجد مستويات. أضف مستوى أولاً ثم أضف الصعوبات تحته.
		</div>
	{:else}
		<div class="space-y-3">
			{#each levels as lvl (lvl.id)}
				{@const lvlProblems = problemsByLevel.get(lvl.id) ?? []}
				{@const expanded = expandedLevels.has(lvl.id)}
				<div class="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
					<!-- level header -->
					<div class="flex items-center gap-3 px-5 py-4">
						<button
							onclick={() => toggleLevel(lvl.id)}
							class="flex flex-1 items-center gap-2 text-right"
						>
							{#if expanded}
								<ChevronUp class="h-4 w-4 text-muted-foreground" />
							{:else}
								<ChevronDown class="h-4 w-4 text-muted-foreground" />
							{/if}
							<span class="font-semibold text-foreground">{lvl.name}</span>
							<span class="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
								{lvlProblems.length} صعوبة
							</span>
						</button>
						<div class="flex items-center gap-1">
							<button
								onclick={() => openProblemCreate(lvl.id)}
								class="rounded-md p-2 text-muted-foreground hover:bg-muted hover:text-foreground"
								title="إضافة صعوبة لهذا المستوى"
							>
								<Plus class="h-4 w-4" />
							</button>
							<button
								onclick={() => openLevelEdit(lvl)}
								class="rounded-md p-2 text-muted-foreground hover:bg-muted hover:text-foreground"
								title="تعديل المستوى"
							>
								<Pencil class="h-4 w-4" />
							</button>
							<button
								onclick={() => confirmDelete('level', lvl.id, lvl.name)}
								class="rounded-md p-2 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
								title="حذف المستوى"
							>
								<Trash2 class="h-4 w-4" />
							</button>
						</div>
					</div>

					<!-- problems list -->
					{#if expanded}
						{#if lvlProblems.length === 0}
							<div class="border-t border-border px-6 py-4 text-sm text-muted-foreground">
								لا توجد صعوبات في هذا المستوى بعد.
							</div>
						{:else}
							<ul class="divide-y divide-border border-t border-border">
								{#each lvlProblems as p (p.id)}
									<li class="flex items-center gap-3 px-6 py-3">
										<span class="flex-1 text-sm text-foreground">{p.name}</span>
										<button
											onclick={() => openProblemEdit(p)}
											class="rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
										>
											<Pencil class="h-3.5 w-3.5" />
										</button>
										<button
											onclick={() => confirmDelete('problem', p.id, p.name)}
											class="rounded-md p-1.5 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
										>
											<Trash2 class="h-3.5 w-3.5" />
										</button>
									</li>
								{/each}
							</ul>
						{/if}
					{/if}
				</div>
			{/each}
		</div>
	{/if}
</div>

<!-- ===== Level modal ===== -->
{#if showLevelForm}
	<div class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
		<div class="w-full max-w-md rounded-2xl bg-card p-6 shadow-xl" dir="rtl">
			<h2 class="mb-5 text-lg font-bold text-foreground">
				{levelForm.id ? 'تعديل المستوى' : 'إضافة مستوى جديد'}
			</h2>
			<label class="mb-1 block text-sm font-medium text-foreground">اسم المستوى</label>
			<input
				type="text"
				bind:value={levelForm.name}
				placeholder="مثال: صعب، متوسط، خفيف..."
				class="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
			/>
			<div class="mt-5 flex justify-end gap-2">
				<button
					onclick={() => (showLevelForm = false)}
					class="rounded-lg border border-border px-4 py-2 text-sm text-foreground hover:bg-muted"
				>
					إلغاء
				</button>
				<button
					onclick={submitLevel}
					disabled={levelSubmitting || !levelForm.name.trim()}
					class="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
				>
					{levelSubmitting ? 'جارٍ الحفظ...' : 'حفظ'}
				</button>
			</div>
		</div>
	</div>
{/if}

<!-- ===== Problem modal ===== -->
{#if showProblemForm}
	<div class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
		<div class="w-full max-w-md rounded-2xl bg-card p-6 shadow-xl" dir="rtl">
			<h2 class="mb-5 text-lg font-bold text-foreground">
				{problemForm.id ? 'تعديل الصعوبة' : 'إضافة صعوبة جديدة'}
			</h2>
			<div class="space-y-4">
				<div>
					<label class="mb-1 block text-sm font-medium text-foreground">المستوى</label>
					<select
						bind:value={problemForm.level_id}
						class="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
					>
						<option value="">-- اختر المستوى --</option>
						{#each levels as lvl (lvl.id)}
							<option value={lvl.id}>{lvl.name}</option>
						{/each}
					</select>
				</div>
				<div>
					<label class="mb-1 block text-sm font-medium text-foreground">اسم الصعوبة</label>
					<input
						type="text"
						bind:value={problemForm.name}
						placeholder="مثال: ضعف الحفظ، عدم الانتباه..."
						class="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
					/>
				</div>
			</div>
			<div class="mt-5 flex justify-end gap-2">
				<button
					onclick={() => (showProblemForm = false)}
					class="rounded-lg border border-border px-4 py-2 text-sm text-foreground hover:bg-muted"
				>
					إلغاء
				</button>
				<button
					onclick={submitProblem}
					disabled={problemSubmitting || !problemForm.name.trim() || !problemForm.level_id}
					class="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
				>
					{problemSubmitting ? 'جارٍ الحفظ...' : 'حفظ'}
				</button>
			</div>
		</div>
	</div>
{/if}

<!-- ===== Delete confirm modal ===== -->
{#if deleteTarget}
	<div class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
		<div class="w-full max-w-sm rounded-2xl bg-card p-6 shadow-xl" dir="rtl">
			<h2 class="mb-2 text-lg font-bold text-foreground">تأكيد الحذف</h2>
			<p class="mb-5 text-sm text-muted-foreground">
				هل تريد حذف
				<span class="font-semibold text-foreground">"{deleteTarget.name}"</span>؟
				{#if deleteTarget.kind === 'level'}
					<span class="text-destructive"> لا يمكن حذف مستوى يحتوي على صعوبات.</span>
				{/if}
			</p>
			<div class="flex justify-end gap-2">
				<button
					onclick={() => (deleteTarget = null)}
					class="rounded-lg border border-border px-4 py-2 text-sm text-foreground hover:bg-muted"
				>
					إلغاء
				</button>
				<button
					onclick={doDelete}
					disabled={deleteSubmitting}
					class="rounded-lg bg-destructive px-4 py-2 text-sm font-medium text-white hover:bg-destructive/90 disabled:opacity-50"
				>
					{deleteSubmitting ? 'جارٍ الحذف...' : 'حذف'}
				</button>
			</div>
		</div>
	</div>
{/if}
