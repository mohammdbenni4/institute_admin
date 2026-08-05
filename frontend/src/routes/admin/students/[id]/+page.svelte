<script lang="ts">
	import { tick } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import PageHeader from '$lib/components/shared/PageHeader.svelte';
	import KPICard from '$lib/components/shared/KPICard.svelte';
	import DataTable, { type Column } from '$lib/components/shared/DataTable.svelte';
	import StatusBadge from '$lib/components/shared/StatusBadge.svelte';
	import Sparkline from '$lib/components/shared/Sparkline.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import Input from '$lib/components/ui/Input.svelte';
	import Dialog from '$lib/components/ui/Dialog.svelte';
	import {
		ApiError,
		dailyRecordsApi,
		halaqahsApi,
		instituteApi,
		studentsApi,
		upcomingExamsApi,
		type DailyRecord,
		type UpcomingExam,
		type InstituteSettings,
		type Student
	} from '$lib/api';
	import MonthlyReport from '$lib/components/reports/MonthlyReport.svelte';
	import ReportOptionsDialog from '$lib/components/reports/ReportOptionsDialog.svelte';
	import { exportStudentReport } from '$lib/reports/export';
	import {
		DEFAULT_SECTIONS,
		periodBounds,
		type ReportPeriod,
		type ReportSections
	} from '$lib/reports/options';
	import {
		ORPHAN_LABELS,
		attitudeLabel,
		currentMonth,
		formatDate,
		formatMonth,
		monthBounds,
		ratingLabel
	} from '$lib/labels';
	import { cn, whatsappLink } from '$lib/utils';
	import {
		ArrowRight,
		CalendarCheck,
		CalendarClock,
		MessageCircle,
		Printer,
		Star,
		TrendingUp,
		UserRound
	} from '@lucide/svelte';
	import { buttonClass } from '$lib/components/ui/Button.svelte';

	let id = $derived($page.params.id ?? '');

	let student = $state<Student | null>(null);
	let halaqahName = $state('—');
	let month = $state(currentMonth());
	let records = $state<DailyRecord[]>([]);
	let loadingRecords = $state(true);
	let error = $state('');
	let selected = $state<DailyRecord | null>(null);

	async function loadStudent() {
		error = '';
		try {
			const s = await studentsApi.get(id);
			student = s;
			halaqahName = '—';
			if (s.halaqah_id) {
				try {
					halaqahName = (await halaqahsApi.get(s.halaqah_id)).name;
				} catch {
					/* halaqah may have been removed */
				}
			}
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'تعذّر تحميل بيانات الطالب.';
		}
	}

	async function loadRecords() {
		loadingRecords = true;
		const { from, to } = monthBounds(month);
		try {
			const res = await dailyRecordsApi.list({
				student_id: id,
				date_from: from,
				date_to: to,
				limit: 200
			});
			records = res.items;
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'تعذّر تحميل السجلات.';
		} finally {
			loadingRecords = false;
		}
	}

	$effect(() => {
		if (id) loadStudent();
	});
	$effect(() => {
		// re-run whenever the student or the selected month changes
		if (id) {
			void month;
			loadRecords();
		}
	});

	// Chronological for the table (newest first) and the sparkline (oldest first).
	let byDateDesc = $derived(
		[...records].sort((a, b) => b.record_date.localeCompare(a.record_date))
	);
	let sparkValues = $derived(
		[...records]
			.sort((a, b) => a.record_date.localeCompare(b.record_date))
			.map((r) => r.total_points)
	);

	let kpis = $derived.by(() => {
		const sessions = records.length;
		const present = records.filter((r) => r.present).length;
		const points = records.reduce((sum, r) => sum + r.total_points, 0);
		return {
			sessions,
			present,
			attendance: sessions ? Math.round((present / sessions) * 100) : 0,
			points,
			avg: sessions ? Math.round(points / sessions) : 0
		};
	});

	let waLink = $derived(
		whatsappLink(
			student?.father_number,
			`السلام عليكم ورحمة الله، بخصوص الطالب ${student?.full_name ?? ''} في حلقة القرآن.`
		)
	);

	const columns: Column[] = [
		{ key: 'record_date', label: 'التاريخ' },
		{ key: 'present', label: 'الحضور' },
		{ key: 'rating', label: 'التقدير' },
		{ key: 'exam', label: 'التسميع' },
		{ key: 'total_points', label: 'النقاط' }
	];

	function examRange(r: DailyRecord): string {
		if (r.exam_from == null && r.exam_to == null) return '—';
		return `${r.exam_from ?? '—'} – ${r.exam_to ?? '—'}`;
	}

	// ─── الاختبارات القادمة ───────────────────────────────────────────────────
	// Read-only here: teachers plan them in their app, the administration reviews.
	let upcomingExams = $state<UpcomingExam[]>([]);

	$effect(() => {
		if (!id) return;
		upcomingExamsApi
			.list({ student_id: id, status: 'pending', limit: 20 })
			.then((r) => (upcomingExams = r.items))
			.catch(() => (upcomingExams = []));
	});

	// ─── Printed / exported report ────────────────────────────────────────────
	// The report can span a different period than the page's month view, so it keeps
	// its own records array and only refetches when the dialog asks for it.
	let reportOpen = $state(false);
	let reportBusy = $state(false);
	let institute = $state<InstituteSettings | null>(null);
	let teacherName = $state('');
	let reportSections = $state<ReportSections>({ ...DEFAULT_SECTIONS });
	let reportPeriod = $state<ReportPeriod>({
		mode: 'month',
		month: currentMonth(),
		from: monthBounds(currentMonth()).from,
		to: monthBounds(currentMonth()).to
	});
	let reportRecords = $state<DailyRecord[]>([]);

	$effect(() => {
		// The institute header (name, logo, phone) is needed before the first print.
		if (!institute) {
			instituteApi
				.get()
				.then((v) => (institute = v))
				.catch(() => {});
		}
	});

	$effect(() => {
		// The report prints the teacher's name in the «الأستاذ» field.
		const hid = student?.halaqah_id;
		if (!hid) return;
		halaqahsApi
			.get(hid)
			.then((h) => (teacherName = h.teacher_name))
			.catch(() => {});
	});

	/** Fetch every record inside the report's period (the API caps `limit` at 200). */
	async function fetchReportRecords(): Promise<DailyRecord[]> {
		const { from, to } = periodBounds(reportPeriod);
		const out: DailyRecord[] = [];
		for (let offset = 0; ; offset += 200) {
			const res = await dailyRecordsApi.list({
				student_id: id,
				date_from: from,
				date_to: to,
				limit: 200,
				offset
			});
			out.push(...res.items);
			if (out.length >= res.total || res.items.length === 0) break;
		}
		return out;
	}

	function openReport() {
		reportPeriod.month = month;
		const b = monthBounds(month);
		reportPeriod.from = b.from;
		reportPeriod.to = b.to;
		reportOpen = true;
	}

	async function printReport() {
		reportBusy = true;
		try {
			reportRecords = await fetchReportRecords();
			reportOpen = false;
			// Let the report render with the fetched period before the print dialog opens.
			await tick();
			window.print();
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'تعذّر تحضير التقرير.';
		} finally {
			reportBusy = false;
		}
	}

	async function exportReport() {
		reportBusy = true;
		try {
			const rows = await fetchReportRecords();
			await exportStudentReport({
				student,
				halaqahName,
				period: reportPeriod,
				records: rows,
				sections: reportSections
			});
			reportOpen = false;
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'تعذّر تصدير التقرير.';
		} finally {
			reportBusy = false;
		}
	}
</script>

<div class="page-container">
	<PageHeader
		title={student?.full_name ?? 'ملف الطالب'}
		subtitle={`الحلقة: ${halaqahName}`}
		breadcrumbs={[
			{ label: 'لوحة التحكم' },
			{ label: 'الطلاب' },
			{ label: student?.full_name ?? '…' }
		]}
	>
		{#snippet actions()}
			<Button variant="outline" onclick={() => goto('/admin/students')}>
				<ArrowRight class="h-4 w-4" />رجوع
			</Button>
			{#if waLink}
				<a
					href={waLink}
					target="_blank"
					rel="noopener noreferrer"
					class={cn(buttonClass('outline'), 'text-emerald-600 hover:text-emerald-700')}
				>
					<MessageCircle class="h-4 w-4" />تواصل مع الأهل
				</a>
			{/if}
			<Button onclick={openReport}>
				<Printer class="h-4 w-4" />تقرير الطالب
			</Button>
		{/snippet}
	</PageHeader>

	{#if error}
		<p class="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>
	{/if}

	<!-- Student info -->
	<div class="glass-card p-5">
		<div class="flex flex-wrap items-start justify-between gap-4">
			<div class="flex items-center gap-3">
				<div class="rounded-2xl bg-primary/10 p-3 text-primary"><UserRound class="h-6 w-6" /></div>
				<div>
					<p class="text-lg font-bold text-foreground">{student?.full_name ?? '…'}</p>
					<p class="text-sm text-muted-foreground">
						{student?.father_name ? `الأب: ${student.father_name}` : ''}
					</p>
				</div>
			</div>
			<dl class="grid grid-cols-2 gap-x-8 gap-y-1 text-sm sm:grid-cols-3">
				<div>
					<dt class="text-muted-foreground">جوال الأب</dt>
					<dd dir="ltr" class="text-right font-medium">{student?.father_number ?? '—'}</dd>
				</div>
				<div>
					<dt class="text-muted-foreground">منطقة السكن</dt>
					<dd class="font-medium">{student?.residential_area ?? '—'}</dd>
				</div>
				<div>
					<dt class="text-muted-foreground">تاريخ القبول</dt>
					<dd class="font-medium">{formatDate(student?.accepted_at)}</dd>
				</div>
				<div>
					<dt class="text-muted-foreground">تاريخ الميلاد</dt>
					<dd class="font-medium">{formatDate(student?.date_of_birth)}</dd>
				</div>
				<div>
					<dt class="text-muted-foreground">الحالة</dt>
					<dd class="font-medium">
						{student?.orphan_of ? ORPHAN_LABELS[student.orphan_of] : 'غير يتيم'}
					</dd>
				</div>
			</dl>
		</div>
	</div>

	<!-- Month selector -->
	<div class="flex flex-wrap items-center gap-3">
		<label for="month" class="text-sm font-medium text-muted-foreground">الشهر</label>
		<Input id="month" type="month" bind:value={month} class="w-44" />
		<span class="text-sm text-muted-foreground">{formatMonth(month)}</span>
	</div>

	<!-- الاختبارات القادمة -->
	{#if upcomingExams.length > 0}
		<div class="glass-card space-y-3 p-5">
			<div class="flex items-center gap-2 text-sm font-bold text-foreground">
				<CalendarClock class="h-4 w-4 text-primary" />الاختبارات القادمة
			</div>
			<div class="space-y-2">
				{#each upcomingExams as ex (ex.id)}
					<div
						class="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-border bg-muted/30 px-4 py-2.5"
					>
						<div class="min-w-0">
							<p class="text-sm font-semibold text-foreground">{ex.summary}</p>
							{#if ex.notes}
								<p class="truncate text-xs text-muted-foreground">{ex.notes}</p>
							{/if}
						</div>
						<div class="flex items-center gap-3 text-xs">
							<span class="text-muted-foreground">المعلم: {ex.teacher_name}</span>
							<span class="rounded-full bg-primary/10 px-2.5 py-1 font-semibold text-primary">
								{formatDate(ex.scheduled_date)}
							</span>
						</div>
					</div>
				{/each}
			</div>
		</div>
	{/if}

	<!-- KPIs -->
	<div class="grid grid-cols-2 gap-4 lg:grid-cols-4">
		<KPICard title="عدد الحصص" value={kpis.sessions} icon={CalendarCheck} />
		<KPICard
			title="نسبة الحضور"
			value={`${kpis.attendance}%`}
			icon={CalendarCheck}
			subtitle={`حضر ${kpis.present} من ${kpis.sessions}`}
		/>
		<KPICard title="مجموع النقاط" value={kpis.points} icon={Star} />
		<KPICard title="متوسط النقاط" value={kpis.avg} icon={TrendingUp} subtitle="لكل حصة" />
	</div>

	<!-- Points trend -->
	<div class="glass-card p-5">
		<div class="mb-3 flex items-center gap-2">
			<TrendingUp class="h-4 w-4 text-primary" />
			<h2 class="section-title text-base">اتجاه النقاط خلال الشهر</h2>
		</div>
		<Sparkline values={sparkValues} class="h-16 w-full" />
	</div>

	<!-- Records table -->
	<DataTable
		{columns}
		rows={byDateDesc}
		onRowClick={(r) => (selected = r)}
		emptyMessage={loadingRecords ? 'جارٍ التحميل…' : 'لا توجد سجلات في هذا الشهر'}
	>
		{#snippet cell({ row, column, value })}
			{#if column.key === 'record_date'}
				<span class="font-medium">{formatDate(row.record_date)}</span>
			{:else if column.key === 'present'}
				<StatusBadge
					label={row.present ? 'حاضر' : 'غائب'}
					tone={row.present ? 'success' : 'danger'}
				/>
			{:else if column.key === 'rating'}
				{ratingLabel(row.rating)}
			{:else if column.key === 'exam'}
				{examRange(row)}
			{:else if column.key === 'total_points'}
				<span class="font-bold text-primary">{row.total_points}</span>
			{:else}
				{value ?? '—'}
			{/if}
		{/snippet}
	</DataTable>
</div>

<!-- Daily-record detail -->
<Dialog
	open={selected !== null}
	onOpenChange={(o) => !o && (selected = null)}
	title="تفاصيل السجل اليومي"
	class="max-w-xl"
>
	{#if selected}
		{@const r = selected}
		<div class="space-y-4">
			<div class="flex items-center justify-between rounded-xl bg-muted/40 px-4 py-3">
				<span class="font-medium">{formatDate(r.record_date)}</span>
				<StatusBadge label={r.present ? 'حاضر' : 'غائب'} tone={r.present ? 'success' : 'danger'} />
			</div>

			<dl class="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
				<div>
					<dt class="text-muted-foreground">التسميع (من – إلى)</dt>
					<dd class="font-medium">{examRange(r)}</dd>
				</div>
				<div>
					<dt class="text-muted-foreground">مجموع التسميع</dt>
					<dd class="font-medium">{r.exam_total ?? '—'}</dd>
				</div>
				<div>
					<dt class="text-muted-foreground">التقدير</dt>
					<dd class="font-medium">{ratingLabel(r.rating)}</dd>
				</div>
				<div>
					<dt class="text-muted-foreground">الأدب</dt>
					<dd class="font-medium">{attitudeLabel(r.attitude)}</dd>
				</div>
				<div>
					<dt class="text-muted-foreground">درس المراجعة</dt>
					<dd class="font-medium">{r.revision_lesson ?? '—'}</dd>
				</div>
				<div>
					<dt class="text-muted-foreground">تقدير المراجعة</dt>
					<dd class="font-medium">{ratingLabel(r.revision_rating)}</dd>
				</div>
				<div>
					<dt class="text-muted-foreground">الواجب القادم</dt>
					<dd class="font-medium">{r.homework ?? '—'}</dd>
				</div>
				<div>
					<dt class="text-muted-foreground">الصعوبات</dt>
					<dd class="font-medium">{r.problems ?? '—'}</dd>
				</div>
			</dl>

			<div class="rounded-xl border border-border p-4">
				<p class="mb-2 text-xs font-semibold text-muted-foreground">توزيع النقاط</p>
				<div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
					<span>حضور: <b>{r.card_present}</b></span>
					<span>تسميع: <b>{r.card_exam}</b></span>
					<span>أدب: <b>{r.card_attitude}</b></span>
					<span>إضافية: <b>{r.added_points}</b></span>
					<span class="ms-auto text-primary">الإجمالي: <b>{r.total_points}</b></span>
				</div>
			</div>

			{#if r.notes}
				<div>
					<p class="mb-1 text-xs font-semibold text-muted-foreground">ملاحظات</p>
					<p class="rounded-xl bg-muted/30 px-4 py-3 text-sm">{r.notes}</p>
				</div>
			{/if}
		</div>
	{/if}
</Dialog>

<ReportOptionsDialog
	bind:open={reportOpen}
	bind:sections={reportSections}
	bind:period={reportPeriod}
	busy={reportBusy}
	onPrint={printReport}
	onExport={exportReport}
/>

<!-- The institute's paper report, laid out for printing. Hidden on screen by the
     `@media print` rule in app.css, which shows only `#print-report`. -->
{#if institute}
	<MonthlyReport
		{institute}
		{student}
		{teacherName}
		{halaqahName}
		period={reportPeriod}
		records={reportRecords}
		sections={reportSections}
	/>
{/if}
