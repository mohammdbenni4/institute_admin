<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import {
		ApiError,
		auth,
		dailyRecordsApi,
		halaqahsApi,
		studentsApi,
		type Halaqah,
		type Student
	} from '$lib/api';
	import { addDays, cn, formatDateArabic, todayIso } from '$lib/utils';
	import TopBar from '$lib/components/TopBar.svelte';
	import Spinner from '$lib/components/Spinner.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import Avatar from '$lib/components/Avatar.svelte';
	import Icon from '$lib/components/Icon.svelte';

	const halaqahId = $derived($page.params.halaqahId ?? '');
	const today = todayIso();

	let status = $state<'loading' | 'ready' | 'error'>('loading');
	let error = $state('');
	let halaqah = $state<Halaqah | null>(null);
	let students = $state<Student[]>([]);
	let present = $state<Record<string, boolean>>({});
	let date = $state(today);
	let saving = $state(false);
	let feedback = $state<{ type: 'ok' | 'err'; text: string } | null>(null);
	let feedbackTimer: ReturnType<typeof setTimeout> | undefined;

	const presentCount = $derived(students.filter((s) => present[s.id]).length);

	onMount(load);

	async function load() {
		if (!auth.teacher) return;
		status = 'loading';
		try {
			const [h, list] = await Promise.all([
				halaqahsApi.get(halaqahId),
				studentsApi.list({ halaqah_id: halaqahId, limit: 200 })
			]);
			halaqah = h;
			students = list.items;
			await loadAttendance();
			status = 'ready';
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'تعذّر تحميل البيانات';
			status = 'error';
		}
	}

	async function loadAttendance() {
		const recs = (
			await dailyRecordsApi.list({ halaqah_id: halaqahId, record_date: date, limit: 200 })
		).items;
		const byId = new Map(recs.map((r) => [r.student_id, r.present]));
		const map: Record<string, boolean> = {};
		for (const s of students) map[s.id] = byId.get(s.id) ?? true;
		present = map;
	}

	function setAll(value: boolean) {
		const map: Record<string, boolean> = {};
		for (const s of students) map[s.id] = value;
		present = map;
	}

	async function shiftDay(delta: number) {
		const next = addDays(date, delta);
		if (next > today) return;
		date = next;
		await loadAttendance();
	}

	function flash(type: 'ok' | 'err', text: string) {
		feedback = { type, text };
		clearTimeout(feedbackTimer);
		feedbackTimer = setTimeout(() => (feedback = null), 2800);
	}

	async function save() {
		if (saving || !auth.teacher) return;
		saving = true;
		try {
			const res = await dailyRecordsApi.bulkAttendance({
				halaqah_id: halaqahId,
				teacher_id: auth.teacher.id,
				record_date: date,
				entries: students.map((s) => ({ student_id: s.id, present: present[s.id] ?? true }))
			});
			flash('ok', `تم الحفظ (${res.created + res.updated} طالب)`);
		} catch (e) {
			flash('err', e instanceof ApiError ? e.message : 'تعذّر حفظ الحضور');
		} finally {
			saving = false;
		}
	}
</script>

<TopBar title="تسجيل الحضور" subtitle={halaqah?.name ?? ''} backHref={`/halaqat/${halaqahId}`} />

<main class="mx-auto max-w-2xl space-y-4 px-4 pb-32 pt-20" dir="rtl">
	{#if status === 'loading'}
		<Spinner label="جارٍ التحميل…" />
	{:else if status === 'error'}
		<EmptyState icon="error" title="حدث خطأ" hint={error} />
	{:else if students.length === 0}
		<EmptyState icon="person_off" title="لا يوجد طلاب" hint="لا يوجد طلاب في هذه الحلقة." />
	{:else}
		<!-- Date + quick actions -->
		<section
			class="flex items-center justify-between rounded-[2rem] border border-white/60 bg-surface-container-lowest p-3 shadow-sm"
		>
			<button
				onclick={() => shiftDay(-1)}
				class="flex h-10 w-10 items-center justify-center rounded-full bg-surface-container-low text-primary active:scale-95"
				aria-label="اليوم السابق"
			>
				<Icon name="chevron_right" />
			</button>
			<label class="flex cursor-pointer flex-col items-center">
				<span class="text-[15px] font-bold text-on-surface">{formatDateArabic(date)}</span>
				<span class="mt-0.5 text-[10px] text-primary">{presentCount}/{students.length} حاضر</span>
				<input
					type="date"
					bind:value={date}
					max={today}
					onchange={loadAttendance}
					class="sr-only"
					aria-label="اختيار التاريخ"
				/>
			</label>
			<button
				onclick={() => shiftDay(1)}
				disabled={date >= today}
				class="flex h-10 w-10 items-center justify-center rounded-full bg-surface-container-low text-primary active:scale-95 disabled:opacity-30"
				aria-label="اليوم التالي"
			>
				<Icon name="chevron_left" />
			</button>
		</section>

		<div class="flex gap-2">
			<button
				onclick={() => setAll(true)}
				class="flex-1 rounded-full border border-primary/20 bg-primary/5 py-2 text-xs font-bold text-primary active:scale-95"
			>
				تحديد الكل حاضر
			</button>
			<button
				onclick={() => setAll(false)}
				class="flex-1 rounded-full border border-error/20 bg-error/5 py-2 text-xs font-bold text-error active:scale-95"
			>
				تحديد الكل غائب
			</button>
		</div>

		<!-- Students -->
		<section
			class="divide-y divide-outline-variant/10 overflow-hidden rounded-[2rem] border border-outline-variant/10 bg-surface-container-lowest shadow-sm"
		>
			{#each students as s (s.id)}
				<div class="flex items-center gap-3 p-3">
					<Avatar name={s.full_name} size="sm" />
					<span class="min-w-0 flex-1 truncate text-[15px] font-bold text-on-surface">
						{s.full_name}
					</span>
					<div class="flex gap-1.5">
						<button
							onclick={() => (present[s.id] = true)}
							class={cn(
								'flex h-9 w-9 items-center justify-center rounded-xl border transition active:scale-95',
								present[s.id]
									? 'border-primary bg-primary text-on-primary'
									: 'border-outline-variant/20 text-on-surface-variant'
							)}
							aria-label="حاضر"
						>
							<Icon name="check" class="text-lg" filled={present[s.id]} />
						</button>
						<button
							onclick={() => (present[s.id] = false)}
							class={cn(
								'flex h-9 w-9 items-center justify-center rounded-xl border transition active:scale-95',
								!present[s.id]
									? 'border-error bg-error text-on-error'
									: 'border-outline-variant/20 text-on-surface-variant'
							)}
							aria-label="غائب"
						>
							<Icon name="close" class="text-lg" filled={!present[s.id]} />
						</button>
					</div>
				</div>
			{/each}
		</section>
	{/if}
</main>

{#if feedback}
	<div
		class={cn(
			'fixed inset-x-0 bottom-28 z-50 mx-auto flex w-fit items-center gap-2 rounded-full px-4 py-2.5 text-sm font-bold text-white shadow-lg',
			feedback.type === 'ok' ? 'bg-primary' : 'bg-error'
		)}
	>
		<Icon name={feedback.type === 'ok' ? 'check_circle' : 'error'} class="text-lg" />
		{feedback.text}
	</div>
{/if}

{#if status === 'ready'}
	<button
		onclick={save}
		disabled={saving}
		class="fixed bottom-8 left-6 z-50 flex h-16 w-16 items-center justify-center rounded-full bg-brand text-white shadow-fab transition active:scale-95 disabled:opacity-70"
		aria-label="حفظ الحضور"
	>
		{#if saving}
			<Icon name="progress_activity" class="animate-spin text-3xl" />
		{:else}
			<Icon name="save" class="text-3xl" />
		{/if}
	</button>
{/if}
