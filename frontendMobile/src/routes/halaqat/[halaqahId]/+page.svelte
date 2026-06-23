<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import {
		ApiError,
		auth,
		dailyRecordsApi,
		halaqahsApi,
		studentsApi,
		type DailyRecord,
		type Halaqah,
		type Student
	} from '$lib/api';
	import { addDays, cn, dayOfMonth, formatDateArabic, monthRange, todayIso } from '$lib/utils';
	import TopBar from '$lib/components/TopBar.svelte';
	import BottomNav from '$lib/components/BottomNav.svelte';
	import Spinner from '$lib/components/Spinner.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import Icon from '$lib/components/Icon.svelte';

	const halaqahId = $derived($page.params.halaqahId ?? '');
	const today = todayIso();
	const month = monthRange(today);

	type AttStatus = 'present' | 'excused' | 'absent';
	type Tab = 'overview' | 'attendance' | 'recitation';

	let status = $state<'loading' | 'ready' | 'error'>('loading');
	let error = $state('');
	let halaqah = $state<Halaqah | null>(null);
	let students = $state<Student[]>([]);
	let monthRecords = $state<DailyRecord[]>([]);
	let tab = $state<Tab>('overview');
	let date = $state(today);

	function attStatus(r: DailyRecord): AttStatus {
		return r.present ? 'present' : r.excused ? 'excused' : 'absent';
	}

	const days = $derived(Array.from({ length: month.days }, (_, i) => i + 1));

	// studentId → day(1..n) → status, for the heatmap.
	const heat = $derived.by(() => {
		const m = new Map<string, Map<number, AttStatus>>();
		for (const r of monthRecords) {
			if (!m.has(r.student_id)) m.set(r.student_id, new Map());
			m.get(r.student_id)!.set(dayOfMonth(r.record_date), attStatus(r));
		}
		return m;
	});

	// Records for the selected recording date (status chips on the entry tabs).
	const dateRecords = $derived.by(() => {
		const m = new Map<string, DailyRecord>();
		for (const r of monthRecords) if (r.record_date === date) m.set(r.student_id, r);
		return m;
	});

	const stats = $derived.by(() => {
		const total = monthRecords.length;
		const present = monthRecords.filter((r) => r.present).length;
		const points = monthRecords.reduce((s, r) => s + r.total_points, 0);
		const todayCount = new Set(
			monthRecords.filter((r) => r.record_date === today).map((r) => r.student_id)
		).size;
		return { rate: total ? Math.round((present / total) * 100) : 0, points, todayCount, total };
	});

	onMount(load);

	// A month of records can exceed the API's 200-row cap, so page through them.
	async function fetchMonthRecords(): Promise<DailyRecord[]> {
		const PAGE = 200;
		let items: DailyRecord[] = [];
		let offset = 0;
		for (;;) {
			const res = await dailyRecordsApi.list({
				halaqah_id: halaqahId,
				date_from: month.from,
				date_to: month.to,
				limit: PAGE,
				offset
			});
			items = items.concat(res.items);
			offset += PAGE;
			if (items.length >= res.total || res.items.length === 0) break;
		}
		return items;
	}

	async function load() {
		if (!auth.teacher) return;
		status = 'loading';
		try {
			const [h, list, recs] = await Promise.all([
				halaqahsApi.get(halaqahId),
				studentsApi.list({ halaqah_id: halaqahId, limit: 200 }),
				fetchMonthRecords()
			]);
			halaqah = h;
			students = list.items;
			monthRecords = recs;
			status = 'ready';
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'تعذّر تحميل بيانات الحلقة';
			status = 'error';
		}
	}

	function shiftDay(delta: number) {
		const next = addDays(date, delta);
		if (next > today || next < month.from) return;
		date = next;
	}

	const cellClass: Record<string, string> = {
		present: 'bg-emerald-500',
		excused: 'bg-blue-500',
		absent: 'bg-red-400',
		empty: 'bg-surface-container-high'
	};

	const TABS: { key: Tab; label: string; icon: string }[] = [
		{ key: 'overview', label: 'نظرة عامة', icon: 'insights' },
		{ key: 'attendance', label: 'الحضور', icon: 'fact_check' },
		{ key: 'recitation', label: 'التسميع والمراجعة', icon: 'menu_book' }
	];
</script>

{#snippet dateBar()}
	<section
		class="flex items-center justify-between rounded-[2rem] border border-outline-variant/15 bg-surface-container-lowest p-2.5 shadow-sm"
	>
		<button
			onclick={() => shiftDay(-1)}
			class="flex h-9 w-9 items-center justify-center rounded-full bg-surface-container-low text-primary active:scale-95"
			aria-label="اليوم السابق"
		>
			<Icon name="chevron_right" />
		</button>
		<label class="flex cursor-pointer flex-col items-center">
			<span class="text-[14px] font-bold text-on-surface">{formatDateArabic(date)}</span>
			<span class="mt-0.5 flex items-center gap-1 text-[10px] text-primary">
				<Icon name="calendar_month" class="text-sm" /> تغيير التاريخ
			</span>
			<input
				type="date"
				bind:value={date}
				min={month.from}
				max={today}
				class="sr-only"
				aria-label="اختيار التاريخ"
			/>
		</label>
		<button
			onclick={() => shiftDay(1)}
			disabled={date >= today}
			class="flex h-9 w-9 items-center justify-center rounded-full bg-surface-container-low text-primary active:scale-95 disabled:opacity-30"
			aria-label="اليوم التالي"
		>
			<Icon name="chevron_left" />
		</button>
	</section>
{/snippet}

{#snippet statusChip(s: AttStatus | undefined)}
	{#if s === 'present'}
		<span class="rounded-full bg-emerald-500/10 px-2.5 py-1 text-[10px] font-bold text-emerald-700"
			>حاضر</span
		>
	{:else if s === 'excused'}
		<span class="rounded-full bg-blue-500/10 px-2.5 py-1 text-[10px] font-bold text-blue-700"
			>أذن</span
		>
	{:else if s === 'absent'}
		<span class="rounded-full bg-red-500/10 px-2.5 py-1 text-[10px] font-bold text-red-700"
			>غائب</span
		>
	{:else}
		<span
			class="rounded-full bg-surface-container-high px-2.5 py-1 text-[10px] font-medium text-on-surface-variant/60"
			>لم يُسجّل</span
		>
	{/if}
{/snippet}

<TopBar title={halaqah?.name ?? 'الحلقة'} subtitle="إدارة الحلقة" backHref="/halaqat" />

<main class="mx-auto max-w-2xl px-4 pb-28 pt-20" dir="rtl">
	{#if status === 'loading'}
		<Spinner label="جارٍ تحميل الحلقة…" />
	{:else if status === 'error'}
		<EmptyState icon="error" title="حدث خطأ" hint={error} />
	{:else}
		<!-- Tabs -->
		<div class="mb-4 flex gap-1 rounded-full bg-surface-container p-1">
			{#each TABS as t (t.key)}
				<button
					onclick={() => (tab = t.key)}
					class={cn(
						'flex flex-1 items-center justify-center gap-1 rounded-full py-2 text-[11px] font-bold transition active:scale-95',
						tab === t.key ? 'bg-primary text-on-primary shadow-sm' : 'text-on-surface-variant/70'
					)}
				>
					<Icon name={t.icon} class="text-sm" filled={tab === t.key} />
					{t.label}
				</button>
			{/each}
		</div>

		{#if students.length === 0}
			<EmptyState
				icon="person_off"
				title="لا يوجد طلاب"
				hint="لا يوجد طلاب مسجّلون في هذه الحلقة."
			/>
		{:else if tab === 'overview'}
			<!-- ===== Overview: stats + heatmap ===== -->
			<div class="space-y-4">
				<div class="grid grid-cols-2 gap-3">
					<div
						class="rounded-[1.5rem] border border-outline-variant/15 bg-surface-container-lowest p-4 shadow-sm"
					>
						<div class="flex items-center gap-1.5 text-[11px] text-on-surface-variant/70">
							<Icon name="group" class="text-sm text-primary" /> الطلاب
						</div>
						<p class="mt-1 font-jakarta text-2xl font-bold text-on-surface">{students.length}</p>
					</div>
					<div
						class="rounded-[1.5rem] border border-outline-variant/15 bg-surface-container-lowest p-4 shadow-sm"
					>
						<div class="flex items-center gap-1.5 text-[11px] text-on-surface-variant/70">
							<Icon name="event_available" class="text-sm text-primary" /> سُجِّل اليوم
						</div>
						<p class="mt-1 font-jakarta text-2xl font-bold text-on-surface">
							{stats.todayCount}/{students.length}
						</p>
					</div>
					<div
						class="rounded-[1.5rem] border border-outline-variant/15 bg-surface-container-lowest p-4 shadow-sm"
					>
						<div class="flex items-center gap-1.5 text-[11px] text-on-surface-variant/70">
							<Icon name="trending_up" class="text-sm text-primary" /> حضور الشهر
						</div>
						<p class="mt-1 font-jakarta text-2xl font-bold text-on-surface">{stats.rate}%</p>
					</div>
					<div
						class="rounded-[1.5rem] border border-outline-variant/15 bg-surface-container-lowest p-4 shadow-sm"
					>
						<div class="flex items-center gap-1.5 text-[11px] text-on-surface-variant/70">
							<Icon name="star" class="text-sm text-primary" /> نقاط الشهر
						</div>
						<p class="mt-1 font-jakarta text-2xl font-bold text-on-surface">{stats.points}</p>
					</div>
				</div>

				<!-- Heatmap -->
				<section
					class="rounded-[2rem] border border-outline-variant/15 bg-surface-container-lowest p-4 shadow-card"
				>
					<div class="mb-3 flex items-center justify-between">
						<h2 class="flex items-center gap-1.5 text-[13px] font-bold text-on-surface-variant">
							<Icon name="calendar_view_month" class="text-base text-primary" /> خريطة الحضور
						</h2>
						<div class="flex items-center gap-2 text-[9px] text-on-surface-variant/70">
							<span class="flex items-center gap-1"
								><span class="h-2.5 w-2.5 rounded-sm bg-emerald-500"></span>حاضر</span
							>
							<span class="flex items-center gap-1"
								><span class="h-2.5 w-2.5 rounded-sm bg-blue-500"></span>أذن</span
							>
							<span class="flex items-center gap-1"
								><span class="h-2.5 w-2.5 rounded-sm bg-red-400"></span>غائب</span
							>
						</div>
					</div>
					<div class="hide-scrollbar overflow-x-auto" dir="ltr">
						<div class="min-w-max space-y-1">
							<!-- day numbers -->
							<div class="flex items-center gap-0.5">
								<span class="w-20 shrink-0"></span>
								{#each days as d (d)}
									<span class="w-4 text-center text-[7px] text-on-surface-variant/50">{d}</span>
								{/each}
							</div>
							{#each students as s (s.id)}
								<div class="flex items-center gap-0.5">
									<span
										class="w-20 shrink-0 truncate text-[10px] font-medium text-on-surface"
										dir="rtl">{s.full_name}</span
									>
									{#each days as d (d)}
										{@const st = heat.get(s.id)?.get(d) ?? 'empty'}
										<span class={cn('h-4 w-4 rounded-sm', cellClass[st])}></span>
									{/each}
								</div>
							{/each}
						</div>
					</div>
				</section>
			</div>
		{:else if tab === 'attendance'}
			<!-- ===== Attendance: pick a student ===== -->
			<div class="space-y-3">
				{@render dateBar()}
				<a
					href={`/halaqat/${halaqahId}/attendance`}
					class="flex items-center justify-center gap-1.5 rounded-full border border-primary/20 bg-primary/5 py-2 text-xs font-bold text-primary active:scale-95"
				>
					<Icon name="checklist" class="text-base" /> تحضير سريع لكامل الحلقة
				</a>
				<ul class="space-y-2.5">
					{#each students as s (s.id)}
						{@const rec = dateRecords.get(s.id)}
						<li>
							<a
								href={`/halaqat/${halaqahId}/${s.id}/present?date=${date}`}
								class="flex items-center gap-3 rounded-[1.75rem] border border-outline-variant/12 bg-surface-container-lowest p-3.5 shadow-sm transition active:scale-[0.99]"
							>
								<span class="min-w-0 flex-1 truncate text-[15px] font-bold text-on-surface"
									>{s.full_name}</span
								>
								{@render statusChip(rec ? attStatus(rec) : undefined)}
								<Icon name="chevron_left" class="text-on-surface-variant/30" />
							</a>
						</li>
					{/each}
				</ul>
			</div>
		{:else}
			<!-- ===== Recitation & revision: pick a student ===== -->
			<div class="space-y-3">
				{@render dateBar()}
				<ul class="space-y-2.5">
					{#each students as s (s.id)}
						{@const rec = dateRecords.get(s.id)}
						{@const done =
							!!rec && (rec.rating != null || !!rec.revision_lesson || rec.exam_total != null)}
						<li>
							<a
								href={`/halaqat/${halaqahId}/${s.id}/recitation?date=${date}`}
								class="flex items-center gap-3 rounded-[1.75rem] border border-outline-variant/12 bg-surface-container-lowest p-3.5 shadow-sm transition active:scale-[0.99]"
							>
								<span class="min-w-0 flex-1 truncate text-[15px] font-bold text-on-surface"
									>{s.full_name}</span
								>
								{#if !rec}
									{@render statusChip(undefined)}
								{:else if !rec.present}
									{@render statusChip(attStatus(rec))}
								{:else if done}
									<span
										class="flex items-center gap-1 rounded-full bg-primary/10 px-2.5 py-1 text-[10px] font-bold text-primary"
									>
										<Icon name="check_circle" filled class="text-sm" /> تم
									</span>
								{:else}
									<span
										class="rounded-full bg-surface-container-high px-2.5 py-1 text-[10px] font-medium text-on-surface-variant/60"
										>بانتظار</span
									>
								{/if}
								<Icon name="chevron_left" class="text-on-surface-variant/30" />
							</a>
						</li>
					{/each}
				</ul>
			</div>
		{/if}
	{/if}
</main>

<BottomNav />
