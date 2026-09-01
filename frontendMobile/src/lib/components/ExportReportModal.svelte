<script lang="ts">
	// Two-tab export sheet: pick a date range + which students to include, then which
	// fields the printed report shows per day. Settings persist across sessions.
	// The actual "export" is the browser's print dialog (→ "Save as PDF") over a
	// dedicated #print-report container — see the `@media print` rules in app.css.
	import { repo } from '$lib/offline';
	import { attitudeLabel, ratingLabel, recordPages } from '$lib/labels';
	import { formatDateArabic, formatMonthArabic, todayIso } from '$lib/utils';
	import { cn } from '$lib/utils';
	import { isNativeApp, printReport, reportFileName, shareReportPdf } from '$lib/print';
	import type { DailyRecord, Student } from '$lib/api';
	import Icon from './Icon.svelte';
	import Loader from './Loader.svelte';
	import Switch from './Switch.svelte';

	let {
		open = $bindable(false),
		halaqahId,
		halaqahName,
		teacherName = '',
		students
	}: {
		open?: boolean;
		halaqahId: string;
		halaqahName: string;
		teacherName?: string;
		students: Student[];
	} = $props();

	const STORAGE_KEY = 'export-report-settings-v1';

	interface ShowFlags {
		attendance: boolean;
		recitation: boolean;
		homework: boolean;
		revision: boolean;
		rating: boolean;
		notes: boolean;
		points: boolean;
	}

	const DEFAULT_SHOW: ShowFlags = {
		attendance: true,
		recitation: true,
		homework: true,
		revision: true,
		rating: true,
		notes: true,
		points: true
	};

	const DISPLAY_TOGGLES: { key: keyof ShowFlags; label: string; icon: string }[] = [
		{ key: 'attendance', label: 'الحضور', icon: 'fact_check' },
		{ key: 'recitation', label: 'التسميع', icon: 'menu_book' },
		{ key: 'homework', label: 'الوظيفة', icon: 'assignment' },
		{ key: 'revision', label: 'المراجعة', icon: 'history_edu' },
		{ key: 'rating', label: 'التقييم والأدب', icon: 'grade' },
		{ key: 'points', label: 'النقاط', icon: 'star' },
		{ key: 'notes', label: 'الملاحظات', icon: 'edit_note' }
	];

	interface StudentStats {
		presentCount: number;
		lateCount: number;
		excusedCount: number;
		absentCount: number;
		examFrom: number | null;
		examTo: number | null;
		totalPages: number;
		totalPoints: number;
		lastNote: string | null;
	}

	/** Attendance/recitation/points rollup for one student's records in the picked range. */
	function computeStats(records: DailyRecord[]): StudentStats {
		const stats: StudentStats = {
			presentCount: 0,
			lateCount: 0,
			excusedCount: 0,
			absentCount: 0,
			examFrom: null,
			examTo: null,
			totalPages: 0,
			totalPoints: 0,
			lastNote: null
		};
		for (const r of records) {
			if (r.present) {
				stats.presentCount++;
				if (r.late) stats.lateCount++;
			} else if (r.excused) {
				stats.excusedCount++;
			} else {
				stats.absentCount++;
			}
			if (stats.examFrom == null && r.exam_from != null) stats.examFrom = r.exam_from;
			if (r.exam_to != null) stats.examTo = r.exam_to;
			stats.totalPages += recordPages(r);
			stats.totalPoints += r.total_points;
			if (r.notes) stats.lastNote = r.notes;
		}
		return stats;
	}

	let tab = $state<'range' | 'display'>('range');
	let from = $state(todayIso());
	let to = $state(todayIso());
	let excluded = $state<Set<string>>(new Set());
	let show = $state<ShowFlags>({ ...DEFAULT_SHOW });
	let exporting = $state(false);
	/** Shown in the sheet when the platform refuses to print or share. */
	let exportError = $state('');
	let printRows = $state<{ student: Student; records: DailyRecord[]; stats: StudentStats }[]>([]);

	function loadSettings(): void {
		if (typeof localStorage === 'undefined') return;
		try {
			const raw = localStorage.getItem(STORAGE_KEY);
			if (!raw) return;
			const parsed = JSON.parse(raw) as {
				from?: string;
				to?: string;
				excludedIds?: string[];
				show?: Partial<ShowFlags>;
			};
			if (parsed.from) from = parsed.from;
			if (parsed.to) to = parsed.to;
			if (Array.isArray(parsed.excludedIds)) excluded = new Set(parsed.excludedIds);
			if (parsed.show) show = { ...DEFAULT_SHOW, ...parsed.show };
		} catch {
			/* corrupted cache — start fresh */
		}
	}

	function saveSettings(): void {
		if (typeof localStorage === 'undefined') return;
		try {
			localStorage.setItem(
				STORAGE_KEY,
				JSON.stringify({ from, to, excludedIds: [...excluded], show })
			);
		} catch {
			/* storage unavailable — settings just won't persist this session */
		}
	}

	// Re-load the last-used settings every time the sheet opens.
	$effect(() => {
		if (open) {
			loadSettings();
			tab = 'range';
		}
	});

	function toggleStudent(id: string): void {
		const next = new Set(excluded);
		if (next.has(id)) next.delete(id);
		else next.add(id);
		excluded = next;
	}

	function attendanceText(r: DailyRecord): string {
		if (r.present) return r.late ? 'متأخر' : 'حاضر';
		return r.excused ? 'إذن' : 'غائب';
	}

	/** Print-only status color, matched to the same palette used on-screen. */
	function attendanceClass(r: DailyRecord): string {
		if (r.present) return r.late ? 'att-late' : 'att-present';
		return r.excused ? 'att-excused' : 'att-absent';
	}

	function examText(r: DailyRecord): string {
		if (r.exam_from != null && r.exam_to != null) return `من ${r.exam_from} إلى ${r.exam_to}`;
		if (r.exam_to != null) return `إلى ${r.exam_to}`;
		if (r.exam_from != null) return `من ${r.exam_from}`;
		if (r.exam_total != null) return `${r.exam_total} صفحة`;
		return '—';
	}

	/** "١ آب ٢٠٢٦" — day + month + year, no weekday (compact for the printed table). */
	function shortDate(iso: string): string {
		return `${Number(iso.slice(8, 10))} ${formatMonthArabic(iso)}`;
	}

	/** "من {from} إلى {to} · شهر آب 2026" when the range is a single calendar month,
	 *  otherwise the two full dates — matches how the institute names its monthly reports. */
	function periodLabel(fromIso: string, toIso: string): string {
		if (fromIso.slice(0, 7) === toIso.slice(0, 7)) return `خلال شهر ${formatMonthArabic(fromIso)}`;
		return `من ${formatDateArabic(fromIso)} إلى ${formatDateArabic(toIso)}`;
	}

	/** Build the printable DOM, then hand it to `deliver` (print dialog or share sheet).
	 *  Both routes need exactly the same preparation, so it is written once. */
	async function runExport(mode: 'print' | 'share' = 'print'): Promise<void> {
		if (exporting || !from || !to) return;
		const includedStudents = students.filter((s) => !excluded.has(s.id));
		if (includedStudents.length === 0) return;
		exporting = true;
		exportError = '';
		try {
			const records = await repo.listMonthRecords(halaqahId, from, to, { force: true });
			const byStudent = new Map<string, DailyRecord[]>();
			for (const r of records) {
				const arr = byStudent.get(r.student_id);
				if (arr) arr.push(r);
				else byStudent.set(r.student_id, [r]);
			}
			printRows = includedStudents.map((s) => {
				const records = (byStudent.get(s.id) ?? [])
					.slice()
					.sort((a, b) => a.record_date.localeCompare(b.record_date));
				return { student: s, records, stats: computeStats(records) };
			});
			saveSettings();
			open = false;
			const title = `تقرير ${halaqahName} — ${periodLabel(from, to)}`;
			if (mode === 'share') {
				await shareReportPdf(reportFileName(halaqahName, from, to), title);
			} else {
				await printReport(title);
			}
		} catch (e) {
			// Android surfaces real failures here (no print service, share sheet refused).
			// Before this the button simply did nothing and said nothing.
			exportError = e instanceof Error ? e.message : 'تعذّر إخراج التقرير';
			open = true;
		} finally {
			exporting = false;
		}
	}
</script>

{#if open}
	<button
		type="button"
		class="fixed inset-0 z-[70] bg-black/40"
		aria-label="إغلاق"
		onclick={() => (open = false)}
	></button>
	<div
		class="fixed inset-x-0 bottom-0 z-[71] flex max-h-[85dvh] flex-col rounded-t-[2rem] bg-surface-container-lowest shadow-2xl"
		dir="rtl"
		role="dialog"
		aria-modal="true"
	>
		<div class="flex items-center gap-2 border-b border-outline-variant/15 p-4">
			<Icon name="print" class="text-xl text-primary" />
			<p class="flex-1 text-[15px] font-bold text-on-surface">تصدير تقرير</p>
			<button
				type="button"
				onclick={() => (open = false)}
				class="rounded-full p-1.5 text-on-surface-variant active:scale-90"
				aria-label="إغلاق"
			>
				<Icon name="close" />
			</button>
		</div>

		<div class="flex border-b border-outline-variant/15">
			<button
				type="button"
				onclick={() => (tab = 'range')}
				class={cn(
					'flex-1 border-b-2 py-2.5 text-[12px] font-bold transition',
					tab === 'range'
						? 'border-primary text-primary'
						: 'border-transparent text-on-surface-variant/60'
				)}
			>
				التاريخ والطلاب
			</button>
			<button
				type="button"
				onclick={() => (tab = 'display')}
				class={cn(
					'flex-1 border-b-2 py-2.5 text-[12px] font-bold transition',
					tab === 'display'
						? 'border-primary text-primary'
						: 'border-transparent text-on-surface-variant/60'
				)}
			>
				خيارات العرض
			</button>
		</div>

		<div class="flex-1 overflow-y-auto p-4">
			{#if tab === 'range'}
				<div class="space-y-4">
					<div class="grid grid-cols-2 gap-2">
						<label class="space-y-1">
							<span class="pr-1 text-[11px] font-bold text-on-surface-variant">من</span>
							<input
								type="date"
								bind:value={from}
								max={to || todayIso()}
								class="w-full rounded-xl bg-surface-container-low px-3 py-2 text-sm text-on-surface focus:outline-none focus:ring-2 focus:ring-primary/20"
							/>
						</label>
						<label class="space-y-1">
							<span class="pr-1 text-[11px] font-bold text-on-surface-variant">إلى</span>
							<input
								type="date"
								bind:value={to}
								min={from}
								max={todayIso()}
								class="w-full rounded-xl bg-surface-container-low px-3 py-2 text-sm text-on-surface focus:outline-none focus:ring-2 focus:ring-primary/20"
							/>
						</label>
					</div>

					<div>
						<p class="mb-2 pr-1 text-[11px] font-bold text-on-surface-variant">
							الطلاب ({students.length - excluded.size}/{students.length})
						</p>
						<div
							class="divide-y divide-outline-variant/10 rounded-2xl border border-outline-variant/15"
						>
							{#each students as s (s.id)}
								<div class="flex items-center justify-between gap-2 px-3 py-2.5">
									<span class="min-w-0 flex-1 truncate text-[13px] text-on-surface"
										>{s.full_name}</span
									>
									<Switch
										checked={!excluded.has(s.id)}
										onchange={() => toggleStudent(s.id)}
										label={s.full_name}
									/>
								</div>
							{/each}
						</div>
					</div>
				</div>
			{:else}
				<div
					class="divide-y divide-outline-variant/10 rounded-2xl border border-outline-variant/15"
				>
					{#each DISPLAY_TOGGLES as t (t.key)}
						<div class="flex items-center justify-between gap-2 px-3 py-3">
							<div class="flex items-center gap-2">
								<Icon name={t.icon} class="text-base text-primary" />
								<span class="text-[13px] text-on-surface">{t.label}</span>
							</div>
							<Switch bind:checked={show[t.key]} label={t.label} />
						</div>
					{/each}
				</div>
			{/if}
		</div>

		<div class="border-t border-outline-variant/15 p-4">
			{#if exportError}
				<p class="mb-2 flex items-center gap-1.5 text-[12px] font-bold text-error">
					<Icon name="error" class="text-[15px]" />
					{exportError}
				</p>
			{/if}
			<button
				type="button"
				onclick={() => runExport('print')}
				disabled={exporting || !from || !to || students.length === excluded.size}
				class="flex w-full items-center justify-center gap-2 rounded-full bg-brand py-3.5 text-sm font-bold text-white active:scale-[0.98] disabled:opacity-60"
			>
				{#if exporting}
					<Loader class="text-lg" /> جارٍ التحضير…
				{:else}
					<Icon name="print" class="text-lg" /> طباعة / حفظ PDF
				{/if}
			</button>
			{#if isNativeApp()}
				<!-- Native only: a browser has no share sheet to hand a file to. -->
				<button
					type="button"
					onclick={() => runExport('share')}
					disabled={exporting || !from || !to || students.length === excluded.size}
					class="mt-2 flex w-full items-center justify-center gap-2 rounded-full border border-brand/30 py-3 text-sm font-bold text-brand active:scale-[0.98] disabled:opacity-60"
				>
					<Icon name="share" class="text-lg" /> مشاركة PDF
				</button>
			{/if}
		</div>
	</div>
{/if}

<!-- Hidden except during print (see #print-report rules in app.css). One full page per
     student (see .student-page's page-break rule) — each page is meant to be handed out
     or filed on its own, so the header repeats on every page rather than once at the top. -->
<div id="print-report" dir="rtl">
	{#each printRows as row (row.student.id)}
		<section class="student-page">
			<header class="report-header">
				<h1>صرح القرآن</h1>
				<p class="report-sub">تقرير أداء الطالب · {periodLabel(from, to)}</p>
			</header>

			<div class="info-row">
				<div>
					<p class="info-line"><span>الطالب:</span> <strong>{row.student.full_name}</strong></p>
					<p class="info-line"><span>الحلقة:</span> {halaqahName}</p>
				</div>
				<div>
					<p class="info-line"><span>الأستاذ:</span> {teacherName || '—'}</p>
					<p class="info-line"><span>عدد الأيام المسجَّلة:</span> {row.records.length}</p>
				</div>
			</div>

			<div class="stats-row">
				<div class="stat-card">
					<p class="stat-title">الدوام</p>
					<p class="stat-body">
						حاضر {row.stats.presentCount} · متأخر {row.stats.lateCount} · إذن {row.stats
							.excusedCount} · غائب {row.stats.absentCount}
					</p>
				</div>
				{#if show.recitation}
					<div class="stat-card">
						<p class="stat-title">التسميع</p>
						<p class="stat-body">
							من {row.stats.examFrom ?? '—'} إلى {row.stats.examTo ?? '—'}
							{#if row.stats.totalPages}· المجموع {row.stats.totalPages} صفحة{/if}
						</p>
					</div>
				{/if}
				{#if show.points}
					<div class="stat-card">
						<p class="stat-title">النقاط</p>
						<p class="stat-body stat-points">{row.stats.totalPoints}</p>
					</div>
				{/if}
			</div>

			{#if show.notes}
				<div class="note-line"><span>ملاحظات الأستاذ:</span> {row.stats.lastNote ?? ''}</div>
				<div class="note-line"><span>ملاحظات الإدارة:</span></div>
			{/if}
			<!-- تُعبَّأ يدوياً بعد الطباعة — لا بيانات مرتبطة بها في التطبيق حالياً. -->
			<div class="note-line"><span>الاختبارات المنجزة:</span></div>

			{#if row.records.length === 0}
				<p class="empty-note">لا توجد سجلات في هذه الفترة.</p>
			{:else}
				<table>
					<thead>
						<tr>
							<th>التاريخ</th>
							{#if show.attendance}<th>الحضور</th>{/if}
							{#if show.recitation}<th>التسميع</th>{/if}
							{#if show.homework}<th>الوظيفة</th>{/if}
							{#if show.revision}<th>المراجعة</th>{/if}
							{#if show.rating}<th>التقدير</th>{/if}
							{#if show.rating}<th>الأدب</th>{/if}
							{#if show.points}<th>النقاط</th>{/if}
							{#if show.notes}<th>ملاحظات</th>{/if}
						</tr>
					</thead>
					<tbody>
						{#each row.records as r, i (r.id)}
							<tr class={i % 2 === 1 ? 'row-alt' : ''}>
								<td class="cell-date">{shortDate(r.record_date)}</td>
								{#if show.attendance}
									<td class={attendanceClass(r)}>{attendanceText(r)}</td>
								{/if}
								{#if show.recitation}<td>{examText(r)}</td>{/if}
								{#if show.homework}<td class="cell-notes">{r.homework ?? '—'}</td>{/if}
								{#if show.revision}<td>{r.revision_lesson ?? '—'}</td>{/if}
								{#if show.rating}<td>{r.rating != null ? ratingLabel(r.rating) : '—'}</td>{/if}
								{#if show.rating}
									<td>{r.attitude != null ? attitudeLabel(r.attitude) : '—'}</td>
								{/if}
								{#if show.points}<td class="cell-points">{r.total_points}</td>{/if}
								{#if show.notes}<td class="cell-notes">{r.notes ?? '—'}</td>{/if}
							</tr>
						{/each}
					</tbody>
				</table>
			{/if}

			<p class="report-footer">أُنشئ هذا التقرير في {formatDateArabic(todayIso())}</p>
		</section>
	{/each}
</div>

<style>
	#print-report {
		font-family: 'IBM Plex Sans Arabic', sans-serif;
		color: #1c2b24;
		background: #fff;
		font-size: 12.5px;
		/* Belt-and-braces: forces every descendant's background/border colors to survive
		   print/PDF export even when the browser's own "background graphics" print option
		   is left unchecked — repeated with !important since a plain declaration was still
		   getting dropped by some print engines in testing. */
		-webkit-print-color-adjust: exact !important;
		print-color-adjust: exact !important;
	}
	#print-report * {
		-webkit-print-color-adjust: exact !important;
		print-color-adjust: exact !important;
	}

	/* One full page per student: everything after the first starts on a fresh sheet. */
	.student-page {
		padding: 22px 26px;
		page-break-after: always;
	}
	.student-page:last-child {
		page-break-after: auto;
	}

	.report-header {
		margin-bottom: 10px;
		padding-bottom: 8px;
		border-bottom: 3px solid #1f7a52;
		text-align: center;
	}
	.report-header h1 {
		margin: 0 0 2px;
		font-size: 21px;
		font-weight: 700;
		color: #134d36;
	}
	.report-sub {
		margin: 0;
		font-size: 12px;
		color: #4b5f57;
	}

	.info-row {
		display: flex;
		justify-content: space-between;
		gap: 12px;
		margin-top: 10px;
		padding-bottom: 8px;
		border-bottom: 1px solid #e3e3e3;
	}
	.info-line {
		margin: 0 0 3px;
		font-size: 13px;
	}
	.info-line span {
		color: #4b5f57;
		font-weight: 400;
	}

	.stats-row {
		display: flex;
		gap: 8px;
		margin-top: 10px;
	}
	.stat-card {
		flex: 1;
		min-width: 0;
		border: 1px solid #bfe0cf;
		border-radius: 10px;
		background: #e7f3ec !important;
		padding: 6px 10px;
	}
	.stat-title {
		margin: 0 0 2px;
		font-size: 10.5px;
		font-weight: 700;
		color: #1f7a52;
	}
	.stat-body {
		margin: 0;
		font-size: 12px;
		color: #1c2b24;
	}
	.stat-points {
		font-size: 17px;
		font-weight: 700;
		color: #134d36;
	}

	.note-line {
		margin-top: 8px;
		padding: 5px 10px;
		border: 1px solid #e3e3e3;
		border-radius: 8px;
		font-size: 12px;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.note-line span {
		font-weight: 700;
		color: #134d36;
	}

	.empty-note {
		margin: 12px 0 0;
		padding: 10px 12px;
		border: 1px solid #e3e3e3;
		border-radius: 10px;
		font-size: 12px;
		color: #777;
	}

	table {
		width: 100%;
		/* `collapse` is the actual cause of the missing cell colors: Chrome's print/PDF
		   path silently drops table-cell background paint under `border-collapse:
		   collapse` (a long-documented Chromium quirk) even with print-color-adjust and
		   !important — `separate` + zero spacing paints identically on screen but keeps
		   the colors in print. */
		border-collapse: separate;
		border-spacing: 0;
		font-size: 11.5px;
		margin-top: 10px;
	}
	/* Background painted on the cells themselves (not the row, not an :nth-child
	   selector) — a table split across printed pages (a long month of records won't
	   always fit one page) was silently dropping row/`:nth-child`-level backgrounds on
	   its continuation pages in testing; per-cell `!important` backgrounds survived. */
	th {
		border: 1px solid #bfe0cf;
		padding: 5px 4px;
		text-align: center;
		font-weight: 700;
		color: #134d36;
		background: #e7f3ec !important;
	}
	td {
		border: 1px solid #e3e3e3;
		padding: 4px;
		text-align: center;
		color: #1c2b24;
		background: #fff !important;
	}
	tr.row-alt td {
		background: #f2f7f4 !important;
	}
	.cell-date {
		white-space: nowrap;
		color: #4b5f57;
	}
	.cell-points {
		font-weight: 700;
		color: #134d36;
	}
	.cell-notes {
		text-align: right;
		max-width: 140px;
	}
	.att-present {
		color: #1a7a4c;
		font-weight: 700;
	}
	.att-late {
		color: #a4720a;
		font-weight: 700;
	}
	.att-excused {
		color: #1a5ba8;
		font-weight: 700;
	}
	.att-absent {
		color: #b3261e;
		font-weight: 700;
	}

	.report-footer {
		margin-top: 14px;
		font-size: 9.5px;
		color: #9aa8a2;
		text-align: center;
	}
</style>
