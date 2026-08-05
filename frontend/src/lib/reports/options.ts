// What a printed/exported student report contains, and over which period.
//
// The institute prints these sheets for parents, so every block is optional: a
// month with no administrative exam, or a report meant only as an attendance
// summary, should not carry empty scaffolding.

export interface ReportSections {
	/** الدوام الكلي — present / excused / unexcused counts. */
	attendance: boolean;
	/** التأخير — a 4th attendance row. Off matches the original paper form exactly. */
	late: boolean;
	/** التسميع — recited range and page total. */
	recitation: boolean;
	/** الاختبارات الإدارية — printed as an empty grid, filled in by hand. */
	adminExams: boolean;
	/** النقاط — the reward-card total. */
	points: boolean;
	/** ملاحظات المدرّس — the teacher's notes from the period. */
	teacherNotes: boolean;
	/** ملاحظات الإدارة — the institute's standing note. */
	adminNotes: boolean;
	/** Signature boxes for the institute and the parent. */
	signatures: boolean;
	/** A day-by-day table of the period's records. */
	dailyTable: boolean;
	/** الوظائف اليومية — the homework assigned on each day. */
	homework: boolean;
}

export const DEFAULT_SECTIONS: ReportSections = {
	attendance: true,
	late: true,
	recitation: true,
	adminExams: true,
	points: true,
	teacherNotes: true,
	adminNotes: true,
	signatures: true,
	dailyTable: false,
	homework: false
};

export const SECTION_LABELS: { key: keyof ReportSections; label: string; hint?: string }[] = [
	{ key: 'attendance', label: 'الدوام الكلي', hint: 'الحضور والغياب المبرر وغير المبرر' },
	{ key: 'late', label: 'التأخير', hint: 'صف إضافي لا يوجد في الورقة الأصلية' },
	{ key: 'recitation', label: 'التسميع', hint: 'من / إلى / العدد الكلي' },
	{ key: 'adminExams', label: 'الاختبارات الإدارية', hint: 'جدول فارغ يُملأ يدوياً' },
	{ key: 'points', label: 'النقاط', hint: 'مجموع نقاط الفترة' },
	{ key: 'teacherNotes', label: 'ملاحظات المدرّس' },
	{ key: 'adminNotes', label: 'ملاحظات الإدارة' },
	{ key: 'signatures', label: 'التواقيع', hint: 'إدارة المعهد وولي الأمر' },
	{ key: 'dailyTable', label: 'جدول السجلات اليومية', hint: 'صف لكل يوم مُسجَّل' },
	{ key: 'homework', label: 'الوظائف اليومية', hint: 'الواجب المُسنَد في كل يوم' }
];

/** A report covers either a calendar month or an explicit from→to window. */
export type PeriodMode = 'month' | 'range';

export interface ReportPeriod {
	mode: PeriodMode;
	/** `YYYY-MM`, used when mode is 'month'. */
	month: string;
	/** `YYYY-MM-DD`, used when mode is 'range'. */
	from: string;
	to: string;
}

/** Levantine Gregorian month names — the wording used on the institute's sheet. */
const LEVANT_MONTHS = [
	'كانون الثاني',
	'شباط',
	'آذار',
	'نيسان',
	'أيار',
	'حزيران',
	'تموز',
	'آب',
	'أيلول',
	'تشرين الأول',
	'تشرين الثاني',
	'كانون الأول'
];

export function levantMonthName(month: string): string {
	const m = Number(month.split('-')[1]);
	return LEVANT_MONTHS[m - 1] ?? '';
}

export function levantYear(month: string): string {
	return month.split('-')[0];
}

/** `24 حزيران 2026` — a full date in the same Levantine wording as the heading.
 *  `Intl('ar')` would say «يونيو» here and the sheet would name the month two
 *  different ways in one page. */
export function levantDate(iso: string): string {
	const [y, m, d] = iso.split('-');
	return `${Number(d)} ${LEVANT_MONTHS[Number(m) - 1] ?? ''} ${y}`;
}

/** Resolve a period to the inclusive ISO bounds the API expects. */
export function periodBounds(period: ReportPeriod): { from: string; to: string } {
	if (period.mode === 'range') return { from: period.from, to: period.to };
	const [y, m] = period.month.split('-').map(Number);
	const last = new Date(y, m, 0).getDate();
	const mm = String(m).padStart(2, '0');
	return { from: `${y}-${mm}-01`, to: `${y}-${mm}-${String(last).padStart(2, '0')}` };
}

/** The heading a report shows for its period. */
export function periodLabel(period: ReportPeriod): string {
	if (period.mode === 'month') {
		return `شهر ${levantMonthName(period.month)} ${levantYear(period.month)}`;
	}
	return `من ${period.from} إلى ${period.to}`;
}
