<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import {
		ApiError,
		auth,
		type DailyRecord,
		type Halaqah,
		type Rating,
		type Student
	} from '$lib/api';
	import { net, repo } from '$lib/offline';
	import { ratingLabel } from '$lib/labels';
	import {
		addDays,
		arabicNum,
		cn,
		dayOfMonth,
		formatDateArabic,
		initials,
		monthRange,
		todayIso
	} from '$lib/utils';

	/** "١٥ نقطة" / "١٠ نقاط" — rough Arabic pluralisation for the points pill. */
	function pointsLabel(n: number): string {
		const unit = n >= 3 && n <= 10 ? 'نقاط' : 'نقطة';
		return `${arabicNum(n)} ${unit}`;
	}
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

	// ===== التسميع والمراجعة tab: split students into waiting / done / absent =====
	type RecKind = 'waiting' | 'done' | 'absent';
	type Recitation = {
		student: Student;
		kind: RecKind;
		status: AttStatus | null; // attendance for the selected date
		points: number; // points earned on the selected date (0 if no record)
		rating: Rating | null; // today's (done) or latest exam rating (waiting)
		examText: string; // today's (done) or latest recitation summary
		homework: string | null; // most recent assigned homework
	};

	/** A record counts as a recitation once it carries an exam, rating, or revision. */
	function hasRecitation(r: DailyRecord): boolean {
		return r.rating != null || !!r.revision_lesson || r.exam_total != null || r.exam_to != null;
	}

	/** A short Arabic summary of what was recited (exam range and/or revision). */
	function recitationText(r: DailyRecord): string {
		const bits: string[] = [];
		if (r.exam_from != null && r.exam_to != null) {
			bits.push(`من ${arabicNum(r.exam_from)} إلى ${arabicNum(r.exam_to)}`);
		} else if (r.exam_to != null) {
			bits.push(`إلى ${arabicNum(r.exam_to)}`);
		} else if (r.exam_from != null) {
			bits.push(`من ${arabicNum(r.exam_from)}`);
		} else if (r.exam_total != null) {
			bits.push(`${arabicNum(r.exam_total)} صفحة`);
		}
		if (r.revision_lesson) bits.push('مراجعة');
		return bits.join(' · ') || '—';
	}

	const recitation = $derived.by(() => {
		// Records per student, newest first, so "latest" lookups are just `.find`.
		const byStudent = new Map<string, DailyRecord[]>();
		for (const r of monthRecords) {
			const arr = byStudent.get(r.student_id);
			if (arr) arr.push(r);
			else byStudent.set(r.student_id, [r]);
		}
		for (const arr of byStudent.values())
			arr.sort((a, b) => b.record_date.localeCompare(a.record_date));

		const waiting: Recitation[] = [];
		const done: Recitation[] = [];
		const absent: Recitation[] = [];
		for (const s of students) {
			const recs = byStudent.get(s.id) ?? [];
			const todayRec = recs.find((r) => r.record_date === date) ?? null;
			const dayPoints = todayRec?.total_points ?? 0;
			const lastRecit = recs.find(hasRecitation) ?? null;
			const lastHw = recs.find((r) => r.homework && r.homework.trim() !== '')?.homework ?? null;
			const st = todayRec ? attStatus(todayRec) : null;

			if (todayRec && (st === 'absent' || st === 'excused')) {
				absent.push({
					student: s,
					kind: 'absent',
					status: st,
					points: dayPoints,
					rating: lastRecit?.rating ?? null,
					examText: lastRecit ? recitationText(lastRecit) : 'لم يُسجّل تسميع بعد',
					homework: lastHw
				});
			} else if (todayRec && hasRecitation(todayRec)) {
				done.push({
					student: s,
					kind: 'done',
					status: st,
					points: dayPoints,
					rating: todayRec.rating,
					examText: recitationText(todayRec),
					homework: todayRec.homework
				});
			} else {
				waiting.push({
					student: s,
					kind: 'waiting',
					status: st,
					points: dayPoints,
					rating: lastRecit?.rating ?? null,
					examText: lastRecit ? recitationText(lastRecit) : 'لم يُسجّل تسميع بعد',
					homework: lastHw
				});
			}
		}
		return { waiting, done, absent };
	});

	// ===== Fast attendance (الحضور tab) =====
	let attendance = $state<Record<string, AttStatus>>({});
	let saving = $state(false);
	let feedback = $state<{ type: 'ok' | 'err'; text: string } | null>(null);
	let feedbackTimer: ReturnType<typeof setTimeout> | undefined;

	// Seed/refresh the selections from the saved records for the chosen date.
	$effect(() => {
		const map: Record<string, AttStatus> = {};
		for (const s of students) {
			const r = dateRecords.get(s.id);
			map[s.id] = r ? attStatus(r) : 'present';
		}
		attendance = map;
	});

	function setAllAttendance(value: AttStatus) {
		const map: Record<string, AttStatus> = {};
		for (const s of students) map[s.id] = value;
		attendance = map;
	}

	function flash(type: 'ok' | 'err', text: string) {
		feedback = { type, text };
		clearTimeout(feedbackTimer);
		feedbackTimer = setTimeout(() => (feedback = null), 2600);
	}

	async function saveAttendance() {
		if (saving || !auth.teacher || students.length === 0) return;
		saving = true;
		try {
			await repo.setAttendance({
				halaqah_id: halaqahId,
				teacher_id: auth.teacher.id,
				record_date: date,
				entries: students.map((s) => {
					const st = attendance[s.id] ?? 'present';
					return { student_id: s.id, present: st === 'present', excused: st === 'excused' };
				})
			});
			monthRecords = await repo.listMonthRecords(halaqahId, month.from, month.to);
			flash(
				'ok',
				net.online ? `تم حفظ الحضور (${students.length} طالب)` : 'حُفظ محلياً — سيُرفع عند الاتصال'
			);
		} catch (e) {
			flash('err', e instanceof ApiError ? e.message : 'تعذّر حفظ الحضور');
		} finally {
			saving = false;
		}
	}

	onMount(load);

	async function load() {
		if (!auth.teacher) return;
		status = 'loading';
		try {
			const [h, list, recs] = await Promise.all([
				repo.getHalaqah(halaqahId),
				repo.listStudents(halaqahId),
				repo.listMonthRecords(halaqahId, month.from, month.to)
			]);
			halaqah = h;
			students = list;
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

{#snippet attBtn(sid: string, value: AttStatus, label: string, activeClass: string)}
	<button
		type="button"
		onclick={() => (attendance[sid] = value)}
		class={cn(
			'rounded-full border py-2 text-[11px] font-bold transition active:scale-95',
			(attendance[sid] ?? 'present') === value
				? activeClass
				: 'border-outline-variant/30 bg-surface-container-low text-on-surface-variant'
		)}
	>
		{label}
	</button>
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

{#snippet infoCol(label: string, value: string)}
	<div class="min-w-0 flex-1">
		<p class="text-[11px] font-medium text-on-surface-variant/45">{label}</p>
		<p class="truncate text-[13px] font-bold text-primary">{value}</p>
	</div>
{/snippet}

{#snippet recitationCard(item: Recitation)}
	<a
		href={`/halaqat/${halaqahId}/${item.student.id}/recitation?date=${date}`}
		class="flex items-center gap-3 px-4 py-3.5 transition active:bg-surface-container-low"
	>
		<!-- avatar -->
		<div
			class="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-brand to-brand-deep text-sm font-bold text-white shadow-sm"
		>
			{initials(item.student.full_name)}
		</div>

		<div class="min-w-0 flex-1">
			<!-- line 1: name + points (+ rating) -->
			<div class="flex items-center gap-2">
				<h3 class="min-w-0 flex-1 truncate text-[16px] font-bold text-on-surface">
					{item.student.full_name}
				</h3>
				<span
					class="inline-flex shrink-0 items-center gap-1 rounded-full bg-brand-tint px-2.5 py-1 text-[11px] font-bold text-brand-deep"
				>
					<Icon name="star" filled class="text-[12px]" />
					{pointsLabel(item.points)}
				</span>
				{#if item.kind !== 'absent' && item.rating != null}
					<span
						class="shrink-0 rounded-full bg-brand-tint px-2.5 py-1 text-[11px] font-bold text-brand-deep"
						>{ratingLabel(item.rating)}</span
					>
				{/if}
			</div>

			<!-- line 2: two columns split by a vertical line -->
			<div class="mt-2 flex items-stretch gap-3">
				{#if item.kind === 'done'}
					<div class="min-w-0 flex-1">
						<p class="text-[11px] font-medium text-on-surface-variant/45">الحالة</p>
						<p class="flex items-center gap-1 truncate text-[13px] font-bold text-primary">
							<Icon name="check_circle" filled class="text-[14px]" /> تم الرصد بنجاح
						</p>
					</div>
					<div class="w-px self-stretch bg-outline-variant/30"></div>
					{@render infoCol('أتمّ التسميع', item.examText)}
				{:else if item.kind === 'absent'}
					<div class="min-w-0 flex-1">
						<p class="text-[11px] font-medium text-on-surface-variant/45">الحالة</p>
						<div class="pt-0.5">{@render statusChip(item.status ?? undefined)}</div>
					</div>
					<div class="w-px self-stretch bg-outline-variant/30"></div>
					{@render infoCol('آخر تسميع', item.examText)}
				{:else}
					{@render infoCol('الوظيفة الحالية', item.homework ?? 'لا يوجد واجب')}
					<div class="w-px self-stretch bg-outline-variant/30"></div>
					{@render infoCol('آخر تسميع', item.examText)}
				{/if}
			</div>
		</div>
	</a>
{/snippet}

{#snippet sectionHeader(icon: string, label: string, n: number, tone: string)}
	<div class={cn('flex items-center gap-2 rounded-full px-4 py-2 text-[14px] font-bold', tone)}>
		<Icon name={icon} filled class="text-lg" />
		<span>{label}</span>
		<span class="ms-auto rounded-full bg-white/70 px-2 py-0.5 text-[11px]">{arabicNum(n)}</span>
	</div>
{/snippet}

{#snippet recitationSection(icon: string, label: string, items: Recitation[], tone: string)}
	<div class="space-y-2.5">
		{@render sectionHeader(icon, label, items.length, tone)}
		<div
			class="divide-y divide-outline-variant/10 overflow-hidden rounded-[1.75rem] border border-outline-variant/10 bg-surface-container-lowest shadow-card"
		>
			{#each items as item (item.student.id)}
				{@render recitationCard(item)}
			{/each}
		</div>
	</div>
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
								<span class="sticky left-0 z-10 w-20 shrink-0 bg-surface-container-lowest"></span>
								{#each days as d (d)}
									<span class="w-4 text-center text-[7px] text-on-surface-variant/50">{d}</span>
								{/each}
							</div>
							{#each students as s (s.id)}
								<div class="flex items-center gap-0.5">
									<span
										class="sticky left-0 z-10 w-20 shrink-0 truncate bg-surface-container-lowest pl-1 text-[10px] font-medium text-on-surface"
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
			<!-- ===== Fast attendance: 3-state per student ===== -->
			<div class="space-y-3">
				{@render dateBar()}
				<div class="flex gap-2">
					<button
						onclick={() => setAllAttendance('present')}
						class="flex-1 rounded-full border border-emerald-500/30 bg-emerald-500/10 py-2 text-xs font-bold text-emerald-700 active:scale-95"
					>
						تحديد الكل حاضر
					</button>
					<button
						onclick={() => setAllAttendance('absent')}
						class="flex-1 rounded-full border border-error/20 bg-error/5 py-2 text-xs font-bold text-error active:scale-95"
					>
						تحديد الكل غائب
					</button>
				</div>
				<ul class="space-y-2.5">
					{#each students as s (s.id)}
						<li
							class="flex items-center gap-3 rounded-[1.75rem] border border-outline-variant/12 bg-surface-container-lowest p-3.5 shadow-sm"
						>
							<span class="min-w-0 flex-1 truncate text-[15px] font-bold text-on-surface"
								>{s.full_name}</span
							>
							<div class="grid w-44 shrink-0 grid-cols-3 gap-1.5">
								{@render attBtn(
									s.id,
									'present',
									'حاضر',
									'border-emerald-500 bg-emerald-500 text-white shadow-sm'
								)}
								{@render attBtn(
									s.id,
									'excused',
									'أذن',
									'border-blue-500 bg-blue-500 text-white shadow-sm'
								)}
								{@render attBtn(
									s.id,
									'absent',
									'غائب',
									'border-error bg-error text-on-error shadow-sm'
								)}
							</div>
						</li>
					{/each}
				</ul>

				<!-- Inline save — sits under the last student, never covers a row -->
				<button
					onclick={saveAttendance}
					disabled={saving}
					class="flex w-full items-center justify-center gap-2 rounded-full bg-brand py-3.5 text-sm font-bold text-white shadow-fab transition active:scale-[0.98] disabled:opacity-70"
				>
					{#if saving}
						<Icon name="progress_activity" class="animate-spin text-xl" /> جارٍ الحفظ…
					{:else}
						<Icon name="save" class="text-xl" /> حفظ الحضور
					{/if}
				</button>
			</div>
		{:else}
			<!-- ===== Recitation & revision: waiting / done / absent ===== -->
			<div class="space-y-6">
				{@render dateBar()}

				{#if recitation.waiting.length > 0}
					{@render recitationSection(
						'pending_actions',
						'طلاب بانتظار التسميع',
						recitation.waiting,
						'bg-brand-tint text-brand-deep'
					)}
				{/if}

				{#if recitation.done.length > 0}
					{@render recitationSection(
						'task_alt',
						'طلاب أتمّوا التسميع',
						recitation.done,
						'bg-emerald-500/15 text-emerald-700'
					)}
				{/if}

				{#if recitation.absent.length > 0}
					{@render recitationSection(
						'event_busy',
						'الطلاب الغائبون',
						recitation.absent,
						'bg-error/10 text-error'
					)}
				{/if}
			</div>
		{/if}
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

<BottomNav />
