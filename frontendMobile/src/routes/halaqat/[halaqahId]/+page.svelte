<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import {
		errorMessage,
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
		addMonths,
		cn,
		dayOfMonth,
		formatDateArabic,
		formatMonthArabic,
		initials,
		monthInputValue,
		monthRange,
		nextSessionDate,
		todayIso,
		toLatinDigits
	} from '$lib/utils';

	/** "١٥ نقطة" / "١٠ نقاط" — rough Arabic pluralisation for the points pill. */
	function pointsLabel(n: number): string {
		const unit = n >= 3 && n <= 10 ? 'نقاط' : 'نقطة';
		return `${n} ${unit}`;
	}
	import TopBar from '$lib/components/TopBar.svelte';
	import BottomNav from '$lib/components/BottomNav.svelte';
	import Spinner from '$lib/components/Spinner.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import Loader from '$lib/components/Loader.svelte';

	const halaqahId = $derived($page.params.halaqahId ?? '');
	const today = todayIso();
	// Teachers may browse well into the past; cap the calendar at today (no future records).
	const historyMin = addMonths(today, -36);
	const currentMonthKey = today.slice(0, 7);

	// «متأخر» is a qualifier on attendance, not a fourth kind of absence — the server
	// stores it as present + late — but the teacher picks it as one of four buttons.
	type AttStatus = 'present' | 'late' | 'excused' | 'absent';
	type Tab = 'overview' | 'attendance' | 'recitation';

	let status = $state<'loading' | 'ready' | 'error'>('loading');
	let error = $state('');
	let halaqah = $state<Halaqah | null>(null);
	let students = $state<Student[]>([]);
	let monthRecordsRaw = $state<DailyRecord[]>([]);
	// Per-student «آخر تسميع» + «آخر واجب», resolved server-side with no date window so
	// a long-absent student's history still shows (it used to vanish past the lookback).
	let latest = $state<Map<string, repo.LatestRecitation>>(new Map());
	let recordsLoading = $state(false);
	let refreshing = $state(false);
	let loadedRange = $state('');
	// Seed the tab/date from the URL so returning from a sub-page lands on the right tab.
	const initialTab = $page.url.searchParams.get('tab');
	let tab = $state<Tab>(
		initialTab === 'attendance' || initialTab === 'recitation' ? initialTab : 'overview'
	);
	// `date` is the single source of truth; the viewed month is derived from it.
	let date = $state($page.url.searchParams.get('date') || today);

	const month = $derived(monthRange(date));
	const isCurrentMonth = $derived(monthInputValue(date) === currentMonthKey);
	/** The halaqah's next scheduled session after the selected day. */
	const nextSession = $derived(nextSessionDate(halaqah?.schedule, date));

	function attStatus(r: DailyRecord): AttStatus {
		if (r.present) return r.late ? 'late' : 'present';
		return r.excused ? 'excused' : 'absent';
	}

	const days = $derived(Array.from({ length: month.days }, (_, i) => i + 1));

	// Records inside the selected month (heatmap / stats / attendance).
	const monthRecords = $derived(
		monthRecordsRaw.filter((r) => r.record_date >= month.from && r.record_date <= month.to)
	);

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
		const recordedDays = new Set(monthRecords.map((r) => r.record_date)).size;
		return {
			rate: total ? Math.round((present / total) * 100) : 0,
			points,
			todayCount,
			recordedDays,
			total
		};
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
			bits.push(`من ${r.exam_from} إلى ${r.exam_to}`);
		} else if (r.exam_to != null) {
			bits.push(`إلى ${r.exam_to}`);
		} else if (r.exam_from != null) {
			bits.push(`من ${r.exam_from}`);
		} else if (r.exam_total != null) {
			bits.push(`${r.exam_total} صفحة`);
		}
		if (r.revision_lesson) bits.push('مراجعة');
		return bits.join(' · ') || '—';
	}

	const recitation = $derived.by(() => {
		const waiting: Recitation[] = [];
		const done: Recitation[] = [];
		const absent: Recitation[] = [];
		for (const s of students) {
			const todayRec = dateRecords.get(s.id) ?? null;
			const dayPoints = todayRec?.total_points ?? 0;
			const previous = latest.get(s.id);
			const lastRecit = previous?.record ?? null;
			const lastHw = previous?.homework ?? null;
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
	// No default choice: a student is only saved once the teacher picks a status.
	let attendance = $state<Record<string, AttStatus | undefined>>({});
	// «أذن» must carry a reason — the institute asked for it to be recorded.
	let excuseReasons = $state<Record<string, string>>({});
	let saving = $state(false);
	let feedback = $state<{ type: 'ok' | 'err'; text: string } | null>(null);
	let feedbackTimer: ReturnType<typeof setTimeout> | undefined;

	// Seed the selections from saved records for the chosen date; leave students with
	// no record unset (no default) so the teacher chooses explicitly.
	$effect(() => {
		const map: Record<string, AttStatus | undefined> = {};
		const reasons: Record<string, string> = {};
		for (const s of students) {
			const r = dateRecords.get(s.id);
			if (r) {
				map[s.id] = attStatus(r);
				if (r.excuse_reason) reasons[s.id] = r.excuse_reason;
			}
		}
		attendance = map;
		excuseReasons = reasons;
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
		// Only save students the teacher actually marked (no forced default).
		const marked = students.filter((s) => attendance[s.id] != null);
		if (marked.length === 0) {
			flash('err', 'لم تحدّد حضور أي طالب');
			return;
		}
		// A reason is mandatory for «أذن»; refuse rather than silently save without it.
		const missingReason = marked.find(
			(s) => attendance[s.id] === 'excused' && !(excuseReasons[s.id] ?? '').trim()
		);
		if (missingReason) {
			flash('err', `اكتب سبب الإذن للطالب ${missingReason.full_name}`);
			return;
		}
		const entries = marked.map((s) => {
			const st = attendance[s.id]!;
			return {
				student_id: s.id,
				present: st === 'present' || st === 'late',
				excused: st === 'excused',
				late: st === 'late',
				excuse_reason: st === 'excused' ? excuseReasons[s.id].trim() : null
			};
		});
		saving = true;
		try {
			await repo.setAttendance({
				halaqah_id: halaqahId,
				teacher_id: auth.teacher.id,
				record_date: date,
				entries
			});
			await reloadRecords();
			flash(
				'ok',
				net.online ? `تم حفظ الحضور (${entries.length} طالب)` : 'حُفظ محلياً — سيُرفع عند الاتصال'
			);
		} catch (e) {
			flash('err', errorMessage(e, 'تعذّر حفظ الحضور'));
		} finally {
			saving = false;
		}
	}

	onMount(load);

	async function load() {
		if (!auth.teacher) return;
		status = 'loading';
		try {
			// Cache-first: these resolve from the local mirror straight away and refresh
			// in the background, so a weak connection never leaves the screen blank.
			const [h, list] = await Promise.all([
				repo.getHalaqah(halaqahId, { onFresh: (v) => (halaqah = v) }),
				repo.listStudents(halaqahId, { onFresh: (v) => (students = v) })
			]);
			halaqah = h;
			students = list;
			status = 'ready';
			await Promise.all([reloadRecords(), reloadLatest()]);
		} catch (e) {
			error = errorMessage(e, 'تعذّر تحميل بيانات الحلقة');
			status = 'error';
		}
	}

	/** (Re)fetch the records of the currently-selected month. */
	async function reloadRecords(force = false) {
		const from = month.from;
		const to = month.to;
		recordsLoading = true;
		try {
			monthRecordsRaw = await repo.listMonthRecords(halaqahId, from, to, {
				force,
				onFresh: (v) => {
					if (loadedRange === `${from}..${to}`) monthRecordsRaw = v;
				}
			});
			loadedRange = `${from}..${to}`;
		} finally {
			recordsLoading = false;
		}
	}

	/** Per-student last recitation + last homework (no date window). */
	async function reloadLatest() {
		if (students.length === 0) return;
		latest = await repo.latestRecitations(
			students.map((s) => s.id),
			date
		);
	}

	// Pull fresh records whenever the viewed month changes (month bar, calendar jump,
	// or day chevrons crossing a month boundary).
	$effect(() => {
		const key = `${month.from}..${month.to}`;
		if (status !== 'ready' || loadedRange === key) return;
		void reloadRecords();
	});

	// «آخر تسميع» is relative to the day being viewed, so re-resolve when it moves.
	$effect(() => {
		void date;
		void students.length;
		if (status !== 'ready') return;
		void reloadLatest();
	});

	/** Manual "تحديث" — re-pull halaqah, students, and records from the server so
	 * newly-added students (with no local edits) show up without a re-login. */
	async function refresh() {
		if (refreshing || !auth.teacher) return;
		refreshing = true;
		try {
			const [h, list] = await Promise.all([
				repo.getHalaqah(halaqahId, { force: true }),
				repo.listStudents(halaqahId, { force: true })
			]);
			halaqah = h;
			students = list;
			await Promise.all([reloadRecords(true), reloadLatest()]);
			flash('ok', net.online ? 'تم التحديث' : 'لا يوجد اتصال — تعذّر التحديث');
		} catch (e) {
			flash('err', errorMessage(e, 'تعذّر التحديث'));
		} finally {
			refreshing = false;
		}
	}

	function goToMonth(anchorIso: string) {
		const r = monthRange(anchorIso);
		if (r.from > today) return; // no future months
		date = r.to < today ? r.to : today; // land on the month's last day (or today)
	}

	function shiftDay(delta: number) {
		const next = addDays(date, delta);
		if (next > today || next < historyMin) return;
		date = next;
	}

	const cellClass: Record<string, string> = {
		present: 'bg-emerald-500',
		late: 'bg-amber-500',
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
				min={historyMin}
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

{#snippet monthBar()}
	<section
		class="flex items-center justify-between rounded-[2rem] border border-outline-variant/15 bg-surface-container-lowest p-2.5 shadow-sm"
	>
		<button
			onclick={() => goToMonth(addMonths(month.from, -1))}
			class="flex h-9 w-9 items-center justify-center rounded-full bg-surface-container-low text-primary active:scale-95"
			aria-label="الشهر السابق"
		>
			<Icon name="chevron_right" />
		</button>
		<label class="flex cursor-pointer flex-col items-center">
			<span class="flex items-center gap-1.5 text-[14px] font-bold text-on-surface">
				{formatMonthArabic(month.from)}
				{#if recordsLoading}
					<Loader class="text-sm text-primary" />
				{/if}
			</span>
			<span class="mt-0.5 flex items-center gap-1 text-[10px] text-primary">
				<Icon name="calendar_month" class="text-sm" /> تغيير الشهر
			</span>
			<input
				type="month"
				value={monthInputValue(date)}
				min={monthInputValue(historyMin)}
				max={currentMonthKey}
				onchange={(e) => e.currentTarget.value && goToMonth(`${e.currentTarget.value}-01`)}
				class="sr-only"
				aria-label="اختيار الشهر"
			/>
		</label>
		<button
			onclick={() => goToMonth(addMonths(month.from, 1))}
			disabled={isCurrentMonth}
			class="flex h-9 w-9 items-center justify-center rounded-full bg-surface-container-low text-primary active:scale-95 disabled:opacity-30"
			aria-label="الشهر التالي"
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
			attendance[sid] === value
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
	{:else if s === 'late'}
		<span class="rounded-full bg-amber-500/10 px-2.5 py-1 text-[10px] font-bold text-amber-700"
			>متأخر</span
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
					{@render infoCol('الوظيفة الحالية', toLatinDigits(item.homework) || 'لا يوجد واجب')}
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
		<span class="ms-auto rounded-full bg-white/70 px-2 py-0.5 text-[11px]">{n}</span>
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

<TopBar title={halaqah?.name ?? 'الحلقة'} subtitle="إدارة الحلقة" backHref="/halaqat">
	{#snippet actions()}
		<button
			onclick={refresh}
			disabled={refreshing}
			class="rounded-full p-2 transition hover:bg-white/10 active:scale-95 disabled:opacity-60"
			aria-label="تحديث البيانات"
		>
			<Icon name="refresh" class={cn('text-2xl', refreshing && 'animate-spin')} />
		</button>
	{/snippet}
</TopBar>

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
			<!-- ===== Overview: month picker + stats + heatmap ===== -->
			<div class="space-y-4">
				{@render monthBar()}
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
							<Icon name="event_available" class="text-sm text-primary" />
							{isCurrentMonth ? 'سُجِّل اليوم' : 'أيام مُسجَّلة'}
						</div>
						<p class="mt-1 font-jakarta text-2xl font-bold text-on-surface">
							{#if isCurrentMonth}
								{stats.todayCount}/{students.length}
							{:else}
								{stats.recordedDays}
							{/if}
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
								><span class="h-2.5 w-2.5 rounded-sm bg-amber-500"></span>متأخر</span
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
							class="space-y-2 rounded-[1.75rem] border border-outline-variant/12 bg-surface-container-lowest p-3.5 shadow-sm"
						>
							<span class="block truncate text-[15px] font-bold text-on-surface">{s.full_name}</span
							>
							<div class="grid grid-cols-4 gap-1.5">
								{@render attBtn(
									s.id,
									'present',
									'حاضر',
									'border-emerald-500 bg-emerald-500 text-white shadow-sm'
								)}
								{@render attBtn(
									s.id,
									'late',
									'متأخر',
									'border-amber-500 bg-amber-500 text-white shadow-sm'
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
							<!-- «أذن» is only meaningful with a reason, so ask for it inline. -->
							{#if attendance[s.id] === 'excused'}
								<input
									bind:value={excuseReasons[s.id]}
									placeholder="سبب الإذن (مطلوب)"
									class="w-full rounded-xl bg-surface-container-low px-3 py-2 text-[13px] text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none focus:ring-2 focus:ring-primary/20"
								/>
							{/if}
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
						<Loader class="text-xl" /> جارٍ الحفظ…
					{:else}
						<Icon name="save" class="text-xl" /> حفظ الحضور
					{/if}
				</button>
			</div>
		{:else}
			<!-- ===== Recitation & revision: waiting / done / absent ===== -->
			<div class="space-y-6">
				{@render dateBar()}

				{#if nextSession}
					<div
						class="flex items-center gap-1.5 rounded-full border border-outline-variant/15 bg-primary/5 px-4 py-2 text-[11px]"
					>
						<Icon name="event_upcoming" class="text-[15px] text-primary" />
						<span class="text-on-surface-variant/60">التسميع القادم</span>
						<span class="font-bold text-on-surface">{formatDateArabic(nextSession)}</span>
					</div>
				{/if}

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
