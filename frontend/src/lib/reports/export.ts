// Spreadsheet export of a student's report period.
//
// The printed sheet is the parent-facing artefact; this is the data-facing one —
// the same section switches decide which sheets are written, so an export never
// carries columns the admin explicitly excluded. SheetJS is loaded lazily (it is
// already a dependency for the student Excel import) so it stays out of the main
// bundle.

import type { DailyRecord, Student } from '$lib/api';
import { attitudeLabel, formatDate, ratingLabel } from '$lib/labels';
import { periodBounds, type ReportPeriod, type ReportSections } from './options';

function attendanceLabel(r: DailyRecord): string {
	if (r.present) return r.late ? 'متأخر' : 'حاضر';
	return r.excused ? 'مأذون' : 'غائب';
}

/** `الملخّص` — one row of period totals. */
function summarySheet(
	student: Student | null,
	halaqahName: string,
	period: ReportPeriod,
	records: DailyRecord[],
	sections: ReportSections
): Record<string, string | number>[] {
	const { from, to } = periodBounds(period);
	const row: Record<string, string | number> = {
		الطالب: student?.full_name ?? '',
		الحلقة: halaqahName,
		'من تاريخ': from,
		'إلى تاريخ': to
	};
	if (sections.attendance) {
		row['الحضور'] = records.filter((r) => r.present).length;
		row['الغياب المبرر'] = records.filter((r) => !r.present && r.excused).length;
		row['الغياب غير المبرر'] = records.filter((r) => !r.present && !r.excused).length;
	}
	if (sections.late) row['التأخير'] = records.filter((r) => r.late).length;
	if (sections.recitation) {
		const froms = records.map((r) => r.exam_from).filter((v): v is number => v != null);
		const tos = records.map((r) => r.exam_to).filter((v): v is number => v != null);
		row['التسميع من'] = froms.length ? Math.min(...froms) : '';
		row['التسميع إلى'] = tos.length ? Math.max(...tos) : '';
		row['العدد الكلي'] =
			Math.round(records.reduce((s, r) => s + (r.exam_total ?? 0), 0) * 100) / 100;
	}
	if (sections.points) {
		row['مجموع النقاط'] = records.reduce((s, r) => s + r.total_points, 0);
	}
	return [row];
}

/** `السجلات اليومية` — a row per recorded day, columns follow the switches. */
function dailySheet(
	records: DailyRecord[],
	sections: ReportSections
): Record<string, string | number>[] {
	return records.map((r) => {
		const row: Record<string, string | number> = { التاريخ: formatDate(r.record_date) };
		if (sections.attendance) {
			row['الحضور'] = attendanceLabel(r);
			row['سبب الإذن'] = r.excuse_reason ?? '';
		}
		if (sections.recitation) {
			row['من'] = r.exam_from ?? '';
			row['إلى'] = r.exam_to ?? '';
			row['العدد الكلي'] = r.exam_total ?? '';
			row['التقدير'] = ratingLabel(r.rating);
			row['المراجعة'] = r.revision_lesson ?? '';
		}
		if (sections.teacherNotes) {
			row['الأدب'] = attitudeLabel(r.attitude);
			row['ملاحظات'] = r.notes ?? '';
			row['الصعوبات'] = r.tagged_problems.map((p) => p.name).join('، ');
		}
		if (sections.points) row['النقاط'] = r.total_points;
		return row;
	});
}

/** `الوظائف اليومية` — date + the homework assigned that day. */
function homeworkSheet(records: DailyRecord[]): Record<string, string>[] {
	return records
		.filter((r) => r.homework && r.homework.trim() !== '')
		.map((r) => ({
			التاريخ: formatDate(r.record_date),
			'الوظيفة اليومية': r.homework ?? ''
		}));
}

/** Build and download an .xlsx for the selected sections and period. */
export async function exportStudentReport(opts: {
	student: Student | null;
	halaqahName: string;
	period: ReportPeriod;
	records: DailyRecord[];
	sections: ReportSections;
}): Promise<void> {
	const XLSX = await import('xlsx');
	const ordered = [...opts.records].sort((a, b) => a.record_date.localeCompare(b.record_date));
	const book = XLSX.utils.book_new();

	XLSX.utils.book_append_sheet(
		book,
		XLSX.utils.json_to_sheet(
			summarySheet(opts.student, opts.halaqahName, opts.period, ordered, opts.sections)
		),
		'الملخص'
	);

	if (opts.sections.dailyTable) {
		XLSX.utils.book_append_sheet(
			book,
			XLSX.utils.json_to_sheet(dailySheet(ordered, opts.sections)),
			'السجلات اليومية'
		);
	}
	if (opts.sections.homework) {
		XLSX.utils.book_append_sheet(
			book,
			XLSX.utils.json_to_sheet(homeworkSheet(ordered)),
			'الوظائف اليومية'
		);
	}

	const { from, to } = periodBounds(opts.period);
	const name = (opts.student?.full_name ?? 'تقرير').replace(/[\\/:*?"<>|]/g, '');
	XLSX.writeFile(book, `${name}_${from}_${to}.xlsx`);
}
