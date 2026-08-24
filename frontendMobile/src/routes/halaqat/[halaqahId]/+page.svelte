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
	import { pageFullLabel } from '$lib/quran';
	import { rashidiFullLabel } from '$lib/rashidi';
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
		todayIso,
		toLatinDigits
	} from '$lib/utils';

	/** "١٥ نقطة" / "١٠ نقاط" — rough Arabic pluralisation for the points pill. */
	function pointsLabel(n: number): string {
		const unit = n >= 3 && n <= 10 ? 'نقاط' : 'نقطة';
		return `${n} ${unit}`;
	}

	/** جزء/صفحة/سورة (أو مرحلة/صفحة/سطر لطلاب رشيدي) لصفحة طالب معيّن، أو رقمها وحده. */
	function examFieldLabel(
		isRashidiStudent: boolean,
		page: number | null,
		line: number | null
	): string {
		if (page == null) return '—';
		if (isRashidiStudent) return rashidiFullLabel(page, line) ?? String(page);
		return pageFullLabel(page) ?? String(page);
	}
	import TopBar from '$lib/components/TopBar.svelte';
	import BottomNav from '$lib/components/BottomNav.svelte';
	import Spinner from '$lib/components/Spinner.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import Loader from '$lib/components/Loader.svelte';
	import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';
	import ExportReportModal from '$lib/components/ExportReportModal.svelte';

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
		initialTab === 'attendance' || initialTab === 'overview' ? initialTab : 'recitation'
	);
	// `date` is the single source of truth; the viewed month is derived from it.
	let date = $state($page.url.searchParams.get('date') || today);

	const month = $derived(monthRange(date));
	const isCurrentMonth = $derived(monthInputValue(date) === currentMonthKey);

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
	// Each group is its own collapsible box; all start open.
	let sectionOpen = $state<Record<RecKind, boolean>>({ waiting: true, done: true, absent: true });
	type Recitation = {
		student: Student;
		kind: RecKind;
		status: AttStatus | null; // attendance for the selected date
		points: number; // points earned on the selected date (0 if no record)
		rating: Rating | null; // today's (done) or latest exam rating (waiting)
		examFrom: number | null; // today's (done) or latest exam start page (waiting/absent)
		examTo: number | null; // today's (done) or latest exam end page (waiting/absent)
		// السطر داخل examFrom/examTo — لطلاب رشيدي فقط (انظر src/lib/rashidi.ts).
		examFromLine: number | null;
		examToLine: number | null;
		homework: string | null; // most recent assigned homework
	};

	/** A record counts as a recitation once it carries an exam, rating, or revision. */
	function hasRecitation(r: DailyRecord): boolean {
		return r.rating != null || !!r.revision_lesson || r.exam_total != null || r.exam_to != null;
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
					examFrom: lastRecit?.exam_from ?? null,
					examTo: lastRecit?.exam_to ?? null,
					examFromLine: lastRecit?.exam_from_line ?? null,
					examToLine: lastRecit?.exam_to_line ?? null,
					homework: lastHw
				});
			} else if (todayRec && hasRecitation(todayRec)) {
				done.push({
					student: s,
					kind: 'done',
					status: st,
					points: dayPoints,
					rating: todayRec.rating,
					examFrom: todayRec.exam_from ?? null,
					examTo: todayRec.exam_to ?? null,
					examFromLine: todayRec.exam_from_line ?? null,
					examToLine: todayRec.exam_to_line ?? null,
					homework: todayRec.homework
				});
			} else {
				waiting.push({
					student: s,
					kind: 'waiting',
					status: st,
					points: dayPoints,
					rating: lastRecit?.rating ?? null,
					examFrom: lastRecit?.exam_from ?? null,
					examTo: lastRecit?.exam_to ?? null,
					examFromLine: lastRecit?.exam_from_line ?? null,
					examToLine: lastRecit?.exam_to_line ?? null,
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

	// حذف سجل اليوم لكل الطلاب
	let deleteAllOpen = $state(false);
	let deletingAll = $state(false);

	// ===== ملاحظة عامة لكل الطلاب (تبويب التسميع) =====
	let generalNoteOpen = $state(false);
	let generalNoteText = $state('');
	let generalNoteError = $state('');
	let savingGeneralNote = $state(false);

	// ===== تقرير مصغّر لفترة محددة (تبويب نظرة عامة) =====
	interface ReportRow {
		student: Student;
		totalPoints: number;
		firstPage: number | null;
		lastPage: number | null;
		presentCount: number;
		absentCount: number;
		excusedCount: number;
		behaviorPct: number;
	}
	let reportOpen = $state(false);
	let reportFrom = $state('');
	let reportTo = $state('');
	let reportLoading = $state(false);
	let reportGenerated = $state(false);
	let reportRows = $state<ReportRow[]>([]);

	// ===== تصدير تقرير (نافذة منبثقة، أزرها في شريط العنوان) =====
	let exportOpen = $state(false);

	/** Aggregate every student's records within [reportFrom, reportTo] into one row each. */
	async function generateReport(): Promise<void> {
		if (!reportFrom || !reportTo || reportLoading) return;
		reportLoading = true;
		reportGenerated = false;
		try {
			const records = await repo.listMonthRecords(halaqahId, reportFrom, reportTo, { force: true });
			const byStudent = new Map<string, DailyRecord[]>();
			for (const r of records) {
				const arr = byStudent.get(r.student_id);
				if (arr) arr.push(r);
				else byStudent.set(r.student_id, [r]);
			}
			reportRows = students.map((s) => {
				const recs = (byStudent.get(s.id) ?? [])
					.slice()
					.sort((a, b) => a.record_date.localeCompare(b.record_date));
				const first = recs.find((r) => r.exam_from != null || r.exam_to != null);
				const last = [...recs].reverse().find((r) => r.exam_to != null || r.exam_from != null);
				const withAttitude = recs.filter((r) => r.attitude != null);
				const behaviorPct = withAttitude.length
					? Math.round(
							(withAttitude.reduce((sum, r) => sum + (r.attitude ?? 0), 0) /
								(withAttitude.length * 3)) *
								100
						)
					: 0;
				return {
					student: s,
					totalPoints: recs.reduce((sum, r) => sum + r.total_points, 0),
					firstPage: first ? (first.exam_from ?? first.exam_to) : null,
					lastPage: last ? (last.exam_to ?? last.exam_from) : null,
					presentCount: recs.filter((r) => r.present).length,
					absentCount: recs.filter((r) => !r.present && !r.excused).length,
					excusedCount: recs.filter((r) => r.excused).length,
					behaviorPct
				};
			});
			reportGenerated = true;
		} finally {
			reportLoading = false;
		}
	}

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
		// Un-marked students who already had a saved record for this date: tapping the
		// active status again clears it, and that should delete the record entirely
		// rather than silently leaving the old status in place.
		const unmarked = students.filter((s) => attendance[s.id] == null && dateRecords.has(s.id));
		if (marked.length === 0 && unmarked.length === 0) {
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
			if (entries.length > 0) {
				await repo.setAttendance({
					halaqah_id: halaqahId,
					teacher_id: auth.teacher.id,
					record_date: date,
					entries
				});
			}
			for (const s of unmarked) {
				await repo.deleteRecord(dateRecords.get(s.id)!.id);
			}
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

	/** Delete every saved daily record (attendance + recitation) for the selected date,
	 *  across the whole halaqah. */
	async function deleteAllToday() {
		if (deletingAll) return;
		const ids = [...dateRecords.values()].map((r) => r.id);
		if (ids.length === 0) return;
		deletingAll = true;
		try {
			for (const id of ids) await repo.deleteRecord(id);
			attendance = {};
			excuseReasons = {};
			await reloadRecords();
			flash(
				'ok',
				net.online ? `تم حذف سجل ${ids.length} طالب` : 'حُذف محلياً — سيُحذف من الخادم عند الاتصال'
			);
		} catch (e) {
			flash('err', errorMessage(e, 'تعذّر حذف السجل'));
		} finally {
			deletingAll = false;
		}
	}

	/** Append one shared note to every student's daily record for the selected date.
	 *  Only students who already have a record today are touched — there is nothing
	 *  to attach a note to for a student whose attendance hasn't been taken yet. */
	async function applyGeneralNote() {
		if (savingGeneralNote || !auth.teacher) return;
		const text = generalNoteText.trim();
		if (!text) {
			generalNoteError = 'اكتب نص الملاحظة';
			return;
		}
		const targets = students.filter((s) => dateRecords.has(s.id));
		if (targets.length === 0) {
			generalNoteError = 'لا يوجد سجل محفوظ لهذا اليوم لإضافة الملاحظة إليه';
			return;
		}
		generalNoteError = '';
		savingGeneralNote = true;
		try {
			for (const s of targets) {
				const rec = dateRecords.get(s.id)!;
				const merged = rec.notes && rec.notes.trim() ? `${rec.notes.trim()}\n${text}` : text;
				await repo.upsertDailyRecord({
					student_id: s.id,
					teacher_id: auth.teacher.id,
					halaqah_id: halaqahId,
					record_date: date,
					notes: merged
				});
			}
			await reloadRecords();
			generalNoteText = '';
			generalNoteOpen = false;
			const skipped = students.length - targets.length;
			flash(
				'ok',
				skipped > 0
					? `أُضيفت الملاحظة لـ ${targets.length} طالب (تخطّينا ${skipped} بلا سجل لهذا اليوم)`
					: `أُضيفت الملاحظة لـ ${targets.length} طالب`
			);
		} catch (e) {
			generalNoteError = errorMessage(e, 'تعذّر إضافة الملاحظة');
		} finally {
			savingGeneralNote = false;
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
		{ key: 'recitation', label: 'التسميع', icon: 'menu_book' },
		{ key: 'attendance', label: 'الحضور', icon: 'fact_check' },
		{ key: 'overview', label: 'نظرة عامة', icon: 'insights' }
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
		onclick={() => (attendance[sid] = attendance[sid] === value ? undefined : value)}
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

{#snippet infoLine(label: string, value: string)}
	<p class="truncate text-[11px]">
		<span class="font-medium text-on-surface-variant/45">{label}:</span>
		<span class="font-bold text-primary">{value}</span>
	</p>
{/snippet}

{#snippet recitationCard(item: Recitation)}
	<a
		href={`/halaqat/${halaqahId}/${item.student.id}/recitation?date=${date}`}
		class="flex items-center gap-2.5 px-4 py-2.5 transition active:bg-surface-container-low"
	>
		<!-- avatar -->
		<div
			class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-brand to-brand-deep text-[11px] font-bold text-white shadow-sm"
		>
			{initials(item.student.full_name)}
		</div>

		<!-- name, with points + rating stacked right underneath it -->
		<div class="min-w-0 flex-1">
			<h3 class="truncate text-[13px] font-bold text-on-surface">{item.student.full_name}</h3>
			<div class="mt-1 flex items-center gap-1.5">
				<span
					class="inline-flex shrink-0 items-center gap-1 rounded-full bg-brand-tint px-2 py-0.5 text-[10px] font-bold text-brand-deep"
				>
					<Icon name="star" filled class="text-[10px]" />
					{pointsLabel(item.points)}
				</span>
				{#if item.kind !== 'absent' && item.rating != null}
					<span
						class="shrink-0 rounded-full bg-brand-tint px-2 py-0.5 text-[10px] font-bold text-brand-deep"
						>{ratingLabel(item.rating)}</span
					>
				{/if}
			</div>
		</div>

		<!-- من / إلى / وظيفة — نفس فكرة بطاقة "آخر جلسة" في صفحة التسميع -->
		<div class="w-[38%] shrink-0 space-y-0.5">
			{#if item.kind === 'absent'}
				<div class="flex justify-end">{@render statusChip(item.status ?? undefined)}</div>
			{/if}
			{@render infoLine(
				'من',
				toLatinDigits(
					examFieldLabel(item.student.student_type === 'rashidi', item.examFrom, item.examFromLine)
				)
			)}
			{@render infoLine(
				'إلى',
				toLatinDigits(
					examFieldLabel(item.student.student_type === 'rashidi', item.examTo, item.examToLine)
				)
			)}
			{@render infoLine('وظيفة', toLatinDigits(item.homework) || '—')}
		</div>
	</a>
{/snippet}

{#snippet recitationSection(
	kind: RecKind,
	icon: string,
	label: string,
	items: Recitation[],
	tone: string
)}
	<div
		class="overflow-hidden rounded-[1.75rem] border border-outline-variant/10 bg-surface-container-lowest shadow-card"
	>
		<button
			type="button"
			onclick={() => (sectionOpen[kind] = !sectionOpen[kind])}
			class={cn(
				'flex w-full items-center justify-between gap-2 px-4 py-3 text-[14px] font-bold',
				tone
			)}
		>
			<span class="flex min-w-0 items-center gap-2">
				<Icon name={icon} filled class="shrink-0 text-lg" />
				<span class="truncate">{label}</span>
				<span class="shrink-0 rounded-full bg-white/70 px-2 py-0.5 text-[11px]">{items.length}</span
				>
			</span>
			<Icon name={sectionOpen[kind] ? 'expand_less' : 'expand_more'} class="shrink-0 text-xl" />
		</button>
		{#if sectionOpen[kind]}
			<div class="divide-y divide-outline-variant/10 border-t border-outline-variant/10">
				{#each items as item (item.student.id)}
					{@render recitationCard(item)}
				{/each}
			</div>
		{/if}
	</div>
{/snippet}

<TopBar title={halaqah?.name ?? 'الحلقة'} subtitle="إدارة الحلقة" backHref="/halaqat">
	{#snippet actions()}
		<a
			href={`/halaqat/${halaqahId}/settings`}
			class="rounded-full p-2 transition hover:bg-white/10 active:scale-95"
			aria-label="إعدادات الحلقة"
		>
			<Icon name="settings" class="text-2xl" />
		</a>
		<button
			onclick={() => (exportOpen = true)}
			class="rounded-full p-2 transition hover:bg-white/10 active:scale-95"
			aria-label="تصدير تقرير"
		>
			<Icon name="print" class="text-2xl" />
		</button>
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

<ExportReportModal
	bind:open={exportOpen}
	{halaqahId}
	halaqahName={halaqah?.name ?? 'الحلقة'}
	teacherName={halaqah?.teacher_name ?? ''}
	{students}
/>

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
						'flex flex-1 items-center justify-center gap-1 rounded-full border py-2 text-[11px] font-bold transition active:scale-95',
						tab === t.key
							? 'border-primary bg-primary text-on-primary shadow-sm'
							: 'border-outline-variant/70 text-on-surface-variant/70'
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

				<!-- ===== تقرير مصغّر لفترة محددة ===== -->
				<section
					class="rounded-[2rem] border border-outline-variant/15 bg-surface-container-lowest p-4 shadow-card"
				>
					<button
						type="button"
						onclick={() => (reportOpen = !reportOpen)}
						class="flex w-full items-center gap-2 text-right"
					>
						<Icon name="fact_check" class="text-base text-primary" />
						<span class="flex-1 text-[13px] font-bold text-on-surface-variant"
							>تقرير لفترة محددة</span
						>
						<Icon
							name={reportOpen ? 'expand_less' : 'expand_more'}
							class="text-lg text-on-surface-variant/50"
						/>
					</button>

					{#if reportOpen}
						<div class="mt-3 space-y-3 border-t border-outline-variant/15 pt-3">
							<div class="grid grid-cols-2 gap-2">
								<label class="space-y-1">
									<span class="pr-1 text-[11px] font-bold text-on-surface-variant">من</span>
									<input
										type="date"
										bind:value={reportFrom}
										max={reportTo || today}
										class="w-full rounded-xl bg-surface-container-low px-3 py-2 text-sm text-on-surface focus:outline-none focus:ring-2 focus:ring-primary/20"
									/>
								</label>
								<label class="space-y-1">
									<span class="pr-1 text-[11px] font-bold text-on-surface-variant">إلى</span>
									<input
										type="date"
										bind:value={reportTo}
										min={reportFrom}
										max={today}
										class="w-full rounded-xl bg-surface-container-low px-3 py-2 text-sm text-on-surface focus:outline-none focus:ring-2 focus:ring-primary/20"
									/>
								</label>
							</div>
							<button
								onclick={generateReport}
								disabled={reportLoading || !reportFrom || !reportTo}
								class="flex w-full items-center justify-center gap-2 rounded-full bg-brand py-3 text-sm font-bold text-white active:scale-[0.98] disabled:opacity-60"
							>
								{#if reportLoading}
									<Loader class="text-lg" /> جارٍ الإعداد…
								{:else}
									<Icon name="fact_check" class="text-lg" /> إنشاء التقرير
								{/if}
							</button>

							{#if reportRows.length > 0}
								<div
									class="hide-scrollbar overflow-x-auto rounded-2xl border border-outline-variant/15"
								>
									<table class="w-full min-w-[600px] text-[11px]">
										<thead>
											<tr class="bg-surface-container-low text-on-surface-variant/70">
												<th
													class="sticky right-0 z-10 bg-surface-container-low px-2 py-2 text-right"
													>الطالب</th
												>
												<th class="px-2 py-2">النقاط</th>
												<th class="px-2 py-2">أول صفحة</th>
												<th class="px-2 py-2">آخر صفحة</th>
												<th class="px-2 py-2">حضور</th>
												<th class="px-2 py-2">غياب</th>
												<th class="px-2 py-2">إذن</th>
												<th class="px-2 py-2">نسبة السلوك</th>
											</tr>
										</thead>
										<tbody>
											{#each reportRows as row (row.student.id)}
												<tr class="border-t border-outline-variant/10">
													<td
														class="sticky right-0 truncate bg-surface-container-lowest px-2 py-2 font-bold text-on-surface"
														>{row.student.full_name}</td
													>
													<td class="px-2 py-2 text-center font-bold text-primary"
														>{row.totalPoints}</td
													>
													<td class="px-2 py-2 text-center">{row.firstPage ?? '—'}</td>
													<td class="px-2 py-2 text-center">{row.lastPage ?? '—'}</td>
													<td class="px-2 py-2 text-center text-emerald-700">{row.presentCount}</td>
													<td class="px-2 py-2 text-center text-error">{row.absentCount}</td>
													<td class="px-2 py-2 text-center text-blue-700">{row.excusedCount}</td>
													<td class="px-2 py-2 text-center">{row.behaviorPct}%</td>
												</tr>
											{/each}
										</tbody>
									</table>
								</div>
							{:else if reportGenerated}
								<p class="text-center text-[11px] text-on-surface-variant/50">
									لا توجد سجلات في هذه الفترة.
								</p>
							{/if}
						</div>
					{/if}
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

				{#if dateRecords.size > 0}
					<button
						onclick={() => (deleteAllOpen = true)}
						disabled={deletingAll}
						class="flex w-full items-center justify-center gap-2 rounded-2xl border border-error/20 bg-error/5 px-4 py-3 text-center text-[13px] font-bold leading-tight text-error active:scale-[0.98] disabled:opacity-60"
					>
						{#if deletingAll}
							<Loader class="shrink-0 text-lg" /> جارٍ الحذف…
						{:else}
							<Icon name="delete" class="shrink-0 text-lg" /> حذف سجل اليوم لكل الطلاب
						{/if}
					</button>
				{/if}
			</div>
		{:else}
			<!-- ===== Recitation & revision: waiting / done / absent ===== -->
			<div class="space-y-6">
				{@render dateBar()}

				{#if recitation.waiting.length > 0}
					{@render recitationSection(
						'waiting',
						'pending_actions',
						'طلاب بانتظار التسميع',
						recitation.waiting,
						'bg-brand-tint text-brand-deep'
					)}
				{/if}

				{#if recitation.done.length > 0}
					{@render recitationSection(
						'done',
						'task_alt',
						'طلاب أتمّوا التسميع',
						recitation.done,
						'bg-emerald-500/15 text-emerald-700'
					)}
				{/if}

				{#if recitation.absent.length > 0}
					{@render recitationSection(
						'absent',
						'event_busy',
						'الطلاب الغائبون',
						recitation.absent,
						'bg-error/10 text-error'
					)}
				{/if}

				<!-- ===== ملاحظة عامة لكل الطلاب ===== -->
				<button
					type="button"
					onclick={() => (generalNoteOpen = true)}
					class="flex w-full items-center justify-center gap-2 rounded-2xl border border-outline-variant/20 bg-surface-container-low px-4 py-3 text-[13px] font-bold text-on-surface-variant active:scale-[0.98]"
				>
					<Icon name="edit_note" class="text-lg text-primary" /> ملاحظة عامة لكل الطلاب
				</button>
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

<ConfirmDialog
	bind:open={deleteAllOpen}
	title="حذف سجل اليوم لكل الطلاب؟"
	message="سيتم حذف كل سجلات الحضور والتسميع المحفوظة لهذا اليوم ({formatDateArabic(
		date
	)}) لجميع طلاب الحلقة نهائياً. لا يمكن التراجع عن هذا الإجراء."
	confirmLabel="حذف نهائي"
	tone="danger"
	icon="delete"
	onConfirm={deleteAllToday}
/>

{#if generalNoteOpen}
	<button
		type="button"
		onclick={() => (generalNoteOpen = false)}
		class="fixed inset-0 z-[70] bg-black/40"
		aria-label="إلغاء"
	></button>
	<div
		class="fixed inset-x-0 bottom-0 z-[71] space-y-4 rounded-t-[2rem] bg-surface-container-lowest p-5 pb-10 shadow-2xl"
		dir="rtl"
		role="dialog"
		aria-modal="true"
	>
		<div class="flex items-center gap-2">
			<Icon name="edit_note" class="text-2xl text-primary" />
			<div class="min-w-0 flex-1">
				<p class="text-[16px] font-bold text-on-surface">ملاحظة عامة لكل الطلاب</p>
				<p class="truncate text-[12px] text-on-surface-variant/70">{formatDateArabic(date)}</p>
			</div>
			<button
				type="button"
				onclick={() => (generalNoteOpen = false)}
				class="rounded-full p-2 text-on-surface-variant active:scale-90"
				aria-label="إغلاق"
			>
				<Icon name="close" />
			</button>
		</div>

		<div class="space-y-1.5">
			<span class="pr-1 text-[13px] font-bold text-on-surface-variant">نص الملاحظة</span>
			<textarea
				bind:value={generalNoteText}
				rows="3"
				placeholder="مثال: غداً اختبار عام في الحلقة"
				class="w-full resize-none rounded-2xl bg-surface-container-low p-3.5 text-sm text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none focus:ring-2 focus:ring-primary/20"
			></textarea>
			{#if generalNoteError}
				<p class="pr-1 text-[12px] font-bold text-error">{generalNoteError}</p>
			{/if}
		</div>

		<p class="text-[11px] leading-relaxed text-on-surface-variant/60">
			تُضاف هذه الملاحظة إلى سجل كل طالب لديه سجل محفوظ في هذا اليوم ({formatDateArabic(date)}).
		</p>

		<button
			type="button"
			onclick={applyGeneralNote}
			disabled={savingGeneralNote}
			class="flex w-full items-center justify-center gap-2 rounded-full bg-brand py-3.5 text-sm font-bold text-white active:scale-[0.98] disabled:opacity-70"
		>
			{#if savingGeneralNote}
				<Loader class="text-lg" />
			{:else}
				<Icon name="edit_note" class="text-lg" />
			{/if}
			إضافة للجميع
		</button>
	</div>
{/if}

<BottomNav />
