<script lang="ts">
	// The institute's monthly student sheet, reproduced for printing.
	//
	// The layout follows the paper original: a centred masthead, one table whose
	// right-hand column lists the attendance rows and whose remaining column groups
	// are التسميع / الاختبارات الإدارية / النقاط, then free-text boxes for the
	// teacher's and the administration's notes, and finally the signature row.
	//
	// «الاختبارات الإدارية» is deliberately printed empty: the institute has no
	// administrative-exam records in the system, and the sheet is filled in by hand
	// and returned («تعاد الورقة إلى المعهد»).
	//
	// Inline styles are used throughout on purpose — the print stylesheet in app.css
	// isolates `#print-report`, and inline rules survive without depending on the
	// app's own cascade.
	import type { DailyRecord, InstituteSettings, Student } from '$lib/api';
	import {
		levantDate,
		periodLabel,
		type ReportPeriod,
		type ReportSections
	} from '$lib/reports/options';

	/** Move the sheet to be a direct child of <body>.
	 *
	 *  The print stylesheet then removes the app shell with
	 *  `body > *:not(#print-report)`. Hiding the shell with `visibility` instead left
	 *  it taking up layout and every print spilled a blank second sheet. */
	function portal(node: HTMLElement) {
		document.body.appendChild(node);
		return {
			destroy() {
				node.remove();
			}
		};
	}

	let {
		institute,
		student,
		teacherName,
		halaqahName,
		period,
		records,
		sections
	}: {
		institute: InstituteSettings;
		student: Student | null;
		teacherName: string;
		halaqahName: string;
		period: ReportPeriod;
		records: DailyRecord[];
		sections: ReportSections;
	} = $props();

	const byDate = $derived([...records].sort((a, b) => a.record_date.localeCompare(b.record_date)));

	const stats = $derived.by(() => {
		const present = records.filter((r) => r.present).length;
		const late = records.filter((r) => r.late).length; // subset of present
		const excused = records.filter((r) => !r.present && r.excused).length;
		const absent = records.filter((r) => !r.present && !r.excused).length;
		const froms = records.map((r) => r.exam_from).filter((v): v is number => v != null);
		const tos = records.map((r) => r.exam_to).filter((v): v is number => v != null);
		return {
			present,
			late,
			excused,
			absent,
			examFrom: froms.length ? Math.min(...froms) : null,
			examTo: tos.length ? Math.max(...tos) : null,
			// Page counts are fractional now, so round the sum: adding floats can leave
			// artefacts like 2.5000000000000004 on a printed report.
			examTotal: Math.round(records.reduce((s, r) => s + (r.exam_total ?? 0), 0) * 100) / 100,
			points: records.reduce((s, r) => s + r.total_points, 0)
		};
	});

	const teacherNotes = $derived(
		byDate
			.filter((r) => r.notes && r.notes.trim() !== '')
			.map((r) => `${levantDate(r.record_date)}: ${r.notes}`)
	);

	const homeworkRows = $derived(byDate.filter((r) => r.homework && r.homework.trim() !== ''));

	const BORDER = '1px solid #9cc3de';
	const HEAD_BG = '#dbeaf5';
	const CELL_BG = '#eef6fb';
	const INK = '#1b4b73';

	/** Blank lines to keep a hand-filled box the same height as on the paper form. */
	function blanks(used: number, wanted: number): number[] {
		return Array.from({ length: Math.max(0, wanted - used) }, (_, i) => i);
	}
</script>

<div
	id="print-report"
	use:portal
	dir="rtl"
	style="font-family: 'IBM Plex Sans Arabic', system-ui, sans-serif; color: {INK}; background: #fff; padding: 8mm;"
>
	<!-- ── Masthead ── -->
	<div style="text-align:center; margin-bottom:6mm;">
		{#if institute.logo_url}
			<img
				src={institute.logo_url}
				alt=""
				style="height:22mm; object-fit:contain; margin:0 auto 2mm;"
			/>
		{/if}
		<div style="font-size:26px; font-weight:700; line-height:1.2;">{institute.name}</div>
		{#if institute.subtitle}
			<div style="font-size:13px; letter-spacing:2px; margin-top:1mm;">{institute.subtitle}</div>
		{/if}
	</div>

	<!-- ── Student / teacher / period ── -->
	<div style="display:flex; justify-content:space-between; font-size:14px; font-weight:700;">
		<span>الطالب : {student?.full_name ?? '..........................................'}</span>
		<span>الأستاذ : {teacherName || halaqahName}</span>
	</div>
	<div
		style="display:flex; justify-content:space-between; font-size:14px; font-weight:700; margin-top:2mm; margin-bottom:4mm;"
	>
		<span>عمل الطالب خلال {periodLabel(period)}.</span>
		<span>الحلقة : {halaqahName}</span>
	</div>

	<!-- ── Main grid: attendance | recitation | admin exams | points ── -->
	{#if sections.attendance || sections.recitation || sections.adminExams || sections.points}
		{@const cols =
			(sections.recitation ? 3 : 0) + (sections.adminExams ? 2 : 0) + (sections.points ? 1 : 0)}
		<table style="width:100%; border-collapse:collapse; font-size:12px; text-align:center;">
			<thead>
				<tr>
					{#if sections.attendance}
						<th style="border:{BORDER}; background:{HEAD_BG}; padding:2mm; font-weight:700;"
							>الدوام الكلي</th
						>
						<th style="border:{BORDER}; background:{HEAD_BG}; padding:2mm; width:16mm;"></th>
					{/if}
					{#if sections.recitation}
						<th
							colspan="3"
							style="border:{BORDER}; background:{HEAD_BG}; padding:2mm; font-weight:700;"
							>التسميع</th
						>
					{/if}
					{#if sections.adminExams}
						<th
							colspan="2"
							style="border:{BORDER}; background:{HEAD_BG}; padding:2mm; font-weight:700;"
							>الاختبارات الإدارية</th
						>
					{/if}
					{#if sections.points}
						<th style="border:{BORDER}; background:{HEAD_BG}; padding:2mm; font-weight:700;"
							>النقاط</th
						>
					{/if}
				</tr>
				<tr>
					{#if sections.attendance}
						<th style="border:{BORDER}; background:{HEAD_BG}; padding:2mm; font-weight:700;"
							>الحضور</th
						>
						<td style="border:{BORDER}; background:{CELL_BG}; padding:2mm; font-weight:700;"
							>{stats.present}</td
						>
					{/if}
					{#if sections.recitation}
						<th style="border:{BORDER}; background:{HEAD_BG}; padding:2mm;">من</th>
						<th style="border:{BORDER}; background:{HEAD_BG}; padding:2mm;">الى</th>
						<th style="border:{BORDER}; background:{HEAD_BG}; padding:2mm;">العدد الكلي</th>
					{/if}
					{#if sections.adminExams}
						<th style="border:{BORDER}; background:{HEAD_BG}; padding:2mm;">الجزء</th>
						<th style="border:{BORDER}; background:{HEAD_BG}; padding:2mm;">العلامة</th>
					{/if}
					{#if sections.points}
						<th style="border:{BORDER}; background:{HEAD_BG}; padding:2mm;">عدد النقاط</th>
					{/if}
				</tr>
			</thead>
			<tbody>
				<!-- Row 1 carries the period's figures; the two rows below it hold the
				     remaining attendance counters, matching the paper form. -->
				<tr>
					{#if sections.attendance}
						<th style="border:{BORDER}; background:{HEAD_BG}; padding:2mm; font-weight:700;"
							>الغياب المبرر</th
						>
						<td style="border:{BORDER}; background:{CELL_BG}; padding:2mm; font-weight:700;"
							>{stats.excused}</td
						>
					{/if}
					{#if sections.recitation}
						<td style="border:{BORDER}; background:{CELL_BG}; padding:2mm;"
							>{stats.examFrom ?? ''}</td
						>
						<td style="border:{BORDER}; background:{CELL_BG}; padding:2mm;">{stats.examTo ?? ''}</td
						>
						<td style="border:{BORDER}; background:{CELL_BG}; padding:2mm;"
							>{stats.examTotal || ''}</td
						>
					{/if}
					{#if sections.adminExams}
						<td style="border:{BORDER}; background:{CELL_BG}; padding:2mm; height:8mm;"></td>
						<td style="border:{BORDER}; background:{CELL_BG}; padding:2mm;"></td>
					{/if}
					{#if sections.points}
						<td style="border:{BORDER}; background:{CELL_BG}; padding:2mm; font-weight:700;"
							>{stats.points}</td
						>
					{/if}
				</tr>
				<tr>
					{#if sections.attendance}
						<th style="border:{BORDER}; background:{HEAD_BG}; padding:2mm; font-weight:700;"
							>الغياب غير المبرر</th
						>
						<td style="border:{BORDER}; background:{CELL_BG}; padding:2mm; font-weight:700;"
							>{stats.absent}</td
						>
					{/if}
					{#each blanks(0, cols) as i (i)}
						<td style="border:{BORDER}; background:{CELL_BG}; padding:2mm; height:8mm;"></td>
					{/each}
				</tr>
				{#if sections.attendance && sections.late}
					<!-- Not on the original paper form; switch «التأخير» off to match it exactly. -->
					<tr>
						<th style="border:{BORDER}; background:{HEAD_BG}; padding:2mm; font-weight:700;"
							>التأخير</th
						>
						<td style="border:{BORDER}; background:{CELL_BG}; padding:2mm; font-weight:700;"
							>{stats.late}</td
						>
						{#each blanks(0, cols) as i (i)}
							<td style="border:{BORDER}; background:{CELL_BG}; padding:2mm; height:8mm;"></td>
						{/each}
					</tr>
				{/if}
			</tbody>
		</table>
	{/if}

	<!-- ── Teacher notes ── -->
	{#if sections.teacherNotes}
		<table
			style="width:100%; border-collapse:collapse; font-size:12px; margin-top:5mm; text-align:center;"
		>
			<thead>
				<tr
					><th style="border:{BORDER}; background:{HEAD_BG}; padding:2.5mm; font-size:15px;"
						>ملاحظات المدرّس</th
					></tr
				>
			</thead>
			<tbody>
				{#each teacherNotes as note, i (i)}
					<tr
						><td
							style="border:{BORDER}; background:{CELL_BG}; padding:2mm; height:7mm; text-align:right;"
							>{note}</td
						></tr
					>
				{/each}
				{#each blanks(teacherNotes.length, 3) as i (i)}
					<tr><td style="border:{BORDER}; background:{CELL_BG}; height:7mm;"></td></tr>
				{/each}
			</tbody>
		</table>
	{/if}

	<!-- ── Administration notes ── -->
	{#if sections.adminNotes}
		<table
			style="width:100%; border-collapse:collapse; font-size:12px; margin-top:5mm; text-align:center;"
		>
			<thead>
				<tr
					><th style="border:{BORDER}; background:{HEAD_BG}; padding:2.5mm; font-size:15px;"
						>ملاحظات الإدارة</th
					></tr
				>
			</thead>
			<tbody>
				{#if institute.report_note}
					<tr
						><td
							style="border:{BORDER}; background:{CELL_BG}; padding:2mm; height:7mm; letter-spacing:1px;"
							>{institute.report_note}</td
						></tr
					>
				{/if}
				{#each blanks(institute.report_note ? 1 : 0, 3) as i (i)}
					<tr><td style="border:{BORDER}; background:{CELL_BG}; height:7mm;"></td></tr>
				{/each}
			</tbody>
		</table>
	{/if}

	<!-- ── Daily records ── -->
	{#if sections.dailyTable}
		<table
			style="width:100%; border-collapse:collapse; font-size:11px; margin-top:5mm; text-align:center;"
		>
			<thead>
				<tr>
					{#each ['التاريخ', 'الحضور', 'التسميع', 'التقدير', 'النقاط'] as h (h)}
						<th style="border:{BORDER}; background:{HEAD_BG}; padding:1.5mm;">{h}</th>
					{/each}
				</tr>
			</thead>
			<tbody>
				{#each byDate as r (r.id)}
					<tr>
						<td style="border:{BORDER}; padding:1.5mm;">{levantDate(r.record_date)}</td>
						<td style="border:{BORDER}; padding:1.5mm;">
							{r.present ? (r.late ? 'متأخر' : 'حاضر') : r.excused ? 'مأذون' : 'غائب'}
							{#if r.excuse_reason}<span style="font-size:9px;"> ({r.excuse_reason})</span>{/if}
						</td>
						<td style="border:{BORDER}; padding:1.5mm;">
							{r.exam_from ?? '—'} – {r.exam_to ?? '—'}
						</td>
						<td style="border:{BORDER}; padding:1.5mm;">{r.rating ?? '—'}</td>
						<td style="border:{BORDER}; padding:1.5mm; font-weight:700;">{r.total_points}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	{/if}

	<!-- ── Daily homework ── -->
	{#if sections.homework}
		<table
			style="width:100%; border-collapse:collapse; font-size:11px; margin-top:5mm; text-align:center;"
		>
			<thead>
				<tr>
					<th style="border:{BORDER}; background:{HEAD_BG}; padding:1.5mm; width:30mm;">التاريخ</th>
					<th style="border:{BORDER}; background:{HEAD_BG}; padding:1.5mm;">الوظيفة اليومية</th>
				</tr>
			</thead>
			<tbody>
				{#each homeworkRows as r (r.id)}
					<tr>
						<td style="border:{BORDER}; padding:1.5mm;">{levantDate(r.record_date)}</td>
						<td style="border:{BORDER}; padding:1.5mm; text-align:right;">{r.homework}</td>
					</tr>
				{/each}
				{#if homeworkRows.length === 0}
					<tr><td colspan="2" style="border:{BORDER}; padding:2mm;">لا توجد وظائف مسجّلة</td></tr>
				{/if}
			</tbody>
		</table>
	{/if}

	<!-- ── Signatures ── -->
	{#if sections.signatures}
		<table
			style="width:100%; border-collapse:collapse; font-size:12px; margin-top:5mm; text-align:center;"
		>
			<thead>
				<tr>
					<th
						style="border:{BORDER}; background:{HEAD_BG}; padding:2.5mm; font-size:14px; width:50%;"
						>إدارة المعهد</th
					>
					<th style="border:{BORDER}; background:{HEAD_BG}; padding:2.5mm; font-size:14px;"
						>توقيع وملاحظات ولي أمر الطالب</th
					>
				</tr>
			</thead>
			<tbody>
				<tr>
					<td style="border:{BORDER}; background:{CELL_BG}; height:20mm;"></td>
					<td style="border:{BORDER}; background:{CELL_BG}; height:20mm;"></td>
				</tr>
			</tbody>
		</table>
	{/if}

	<!-- ── Footer ── -->
	<div
		style="display:flex; justify-content:space-between; align-items:center; font-size:12px; font-weight:700; margin-top:4mm;"
	>
		<span>رقم المعهد : {institute.phone}</span>
		{#if institute.report_footer}
			<span style="color:#c0392b;">{institute.report_footer}</span>
		{/if}
	</div>
</div>
