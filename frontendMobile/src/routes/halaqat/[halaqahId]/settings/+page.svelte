<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { errorMessage, auth, type ScoringPreset, type Student, type StudentType } from '$lib/api';
	import { repo } from '$lib/offline';
	import TopBar from '$lib/components/TopBar.svelte';
	import Spinner from '$lib/components/Spinner.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import Dropdown from '$lib/components/Dropdown.svelte';

	const halaqahId = $derived($page.params.halaqahId ?? '');

	const TYPE_OPTIONS: { value: StudentType | ''; label: string }[] = [
		{ value: '', label: '—' },
		{ value: 'quran', label: 'قرآن' },
		{ value: 'rashidi', label: 'رشيدي' }
	];

	let status = $state<'loading' | 'ready' | 'error'>('loading');
	let error = $state('');
	let halaqahName = $state('الحلقة');
	let students = $state<Student[]>([]);
	let presets = $state<ScoringPreset[]>([]);
	// Editable copies keyed by student id — kept separate from `students` so a dropdown's
	// bound value never has to reconcile with `Student.student_type`'s `null` (Dropdown
	// only speaks `string | number | ''`).
	let typeSel = $state<Record<string, StudentType | ''>>({});
	let presetSel = $state<Record<string, string>>({});
	let savingId = $state<string | null>(null);
	let rowError = $state<Record<string, string>>({});

	const presetOptions = $derived([
		{ value: '', label: 'النظام الافتراضي' },
		...presets.map((p) => ({ value: p.id, label: p.name }))
	]);

	onMount(load);

	async function load(): Promise<void> {
		if (!auth.teacher) return;
		status = 'loading';
		try {
			const [halaqah, list, presetList] = await Promise.all([
				repo.getHalaqah(halaqahId),
				repo.listStudents(halaqahId),
				repo.listScoringPresets()
			]);
			halaqahName = halaqah.name;
			students = list;
			presets = presetList;
			typeSel = Object.fromEntries(list.map((s) => [s.id, s.student_type ?? '']));
			presetSel = Object.fromEntries(list.map((s) => [s.id, s.scoring_preset_id ?? '']));
			status = 'ready';
		} catch (e) {
			error = errorMessage(e, 'تعذّر تحميل بيانات الحلقة');
			status = 'error';
		}
	}

	async function saveType(student: Student): Promise<void> {
		const value = typeSel[student.id];
		await save(student, { student_type: value === '' ? null : value });
	}

	async function savePreset(student: Student): Promise<void> {
		const value = presetSel[student.id];
		await save(student, { scoring_preset_id: value === '' ? null : value });
	}

	async function save(
		student: Student,
		patch: { student_type?: StudentType | null; scoring_preset_id?: string | null }
	): Promise<void> {
		savingId = student.id;
		rowError = { ...rowError, [student.id]: '' };
		try {
			const updated = await repo.updateStudent(student.id, patch);
			students = students.map((s) => (s.id === updated.id ? updated : s));
		} catch (e) {
			rowError = { ...rowError, [student.id]: errorMessage(e, 'تعذّر الحفظ') };
			// Revert the dropdown to the last-saved value so it doesn't silently disagree
			// with what's actually stored.
			typeSel = { ...typeSel, [student.id]: student.student_type ?? '' };
			presetSel = { ...presetSel, [student.id]: student.scoring_preset_id ?? '' };
		} finally {
			savingId = null;
		}
	}
</script>

<TopBar title="إعدادات الحلقة" subtitle={halaqahName} backHref={`/halaqat/${halaqahId}`} />

<main class="mx-auto max-w-2xl space-y-3 px-3 pb-10 pt-20" dir="rtl">
	{#if status === 'loading'}
		<Spinner label="جارٍ التحميل…" />
	{:else if status === 'error'}
		<EmptyState icon="error" title="حدث خطأ" hint={error} />
	{:else if students.length === 0}
		<EmptyState icon="group" title="لا يوجد طلاب في هذه الحلقة" />
	{:else}
		<p class="px-1 text-[11px] text-on-surface-variant/60">
			نوع كل طالب ونظام تسعير نقاطه — يُحفظ كل تغيير فوراً.
		</p>
		<div class="space-y-2">
			{#each students as s (s.id)}
				<div
					class="space-y-2.5 rounded-3xl border border-outline-variant/15 bg-surface-container-lowest p-3.5 shadow-card"
				>
					<div class="flex items-center justify-between gap-2">
						<p class="min-w-0 flex-1 truncate text-[14px] font-bold text-on-surface">
							{s.full_name}
						</p>
						{#if savingId === s.id}
							<Spinner size="sm" />
						{/if}
					</div>
					<div class="grid grid-cols-2 gap-2">
						<div class="min-w-0 space-y-1">
							<span class="block pr-1 text-[10px] font-bold text-on-surface-variant/60"
								>نوع الطالب</span
							>
							<Dropdown
								bind:value={typeSel[s.id]}
								options={TYPE_OPTIONS}
								onchange={() => saveType(s)}
								class="px-2.5 py-2.5 text-[12px]"
							/>
						</div>
						<div class="min-w-0 space-y-1">
							<span class="block pr-1 text-[10px] font-bold text-on-surface-variant/60"
								>نظام تسعير النقاط</span
							>
							<Dropdown
								bind:value={presetSel[s.id]}
								options={presetOptions}
								onchange={() => savePreset(s)}
								class="px-2.5 py-2.5 text-[12px]"
							/>
						</div>
					</div>
					{#if rowError[s.id]}
						<p class="flex items-center gap-1 text-[11px] font-bold text-error">
							<Icon name="error" class="text-[13px]" />
							{rowError[s.id]}
						</p>
					{/if}
				</div>
			{/each}
		</div>
	{/if}
</main>
