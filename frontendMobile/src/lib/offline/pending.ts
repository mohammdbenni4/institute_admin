// Human-readable summary of the records still awaiting upload, for the sync sheet:
// a one-line summary per record plus a field-by-field old→new diff.

import { ratingLabel, attitudeLabel } from '$lib/labels';
import { toLatinDigits } from '$lib/utils';
import { db, type CachedRecord, type RecordBaseline } from './db';

export interface FieldChange {
	label: string;
	old: string;
	new: string;
}

export interface PendingChange {
	id: string;
	studentName: string;
	dateIso: string;
	detail: string;
	/** true = created locally (no server "before" state — everything is new). */
	localOnly: boolean;
	changes: FieldChange[];
	/** Arabic reason the server refused this record, if it did. */
	syncError: string | null;
	/** Where to send the teacher to correct it. */
	studentId: string;
	halaqahId: string;
}

/** Anything with a value that a record can carry, formatted for display. */
type FieldSource = Pick<
	CachedRecord,
	| 'present'
	| 'excused'
	| 'late'
	| 'excuse_reason'
	| 'exam_from'
	| 'exam_to'
	| 'exam_total'
	| 'homework'
	| 'problems'
	| 'rating'
	| 'revision_lesson'
	| 'revision_rating'
	| 'attitude'
	| 'added_points'
	| 'notes'
>;

const DASH = '—';

function fmtAttendance(present: boolean, excused: boolean, late = false): string {
	if (present) return late ? 'متأخر' : 'حاضر';
	return excused ? 'أذن' : 'غائب';
}

function fmtExam(from: number | null, to: number | null, total: number | null): string {
	if (from != null && to != null) return `من ${from} إلى ${to}`;
	if (to != null) return `إلى ${to}`;
	if (from != null) return `من ${from}`;
	if (total != null) return `${total} صفحة`;
	return DASH;
}

/** Free text as stored. `toLatinDigits` normalises records written by older app
 *  versions, which saved Arabic-Indic digits (e.g. "الجزء ٢٩"). */
function txt(v: string | null | undefined): string {
	return v && v.trim() !== '' ? toLatinDigits(v) : DASH;
}

/** Labelled, display-formatted view of the editable fields. */
const FIELDS: { label: string; get: (r: FieldSource) => string }[] = [
	{ label: 'الحضور', get: (r) => fmtAttendance(r.present, r.excused, r.late) },
	{ label: 'سبب الإذن', get: (r) => txt(r.excuse_reason) },
	{ label: 'التسميع', get: (r) => fmtExam(r.exam_from, r.exam_to, r.exam_total) },
	{ label: 'التقدير', get: (r) => (r.rating != null ? ratingLabel(r.rating) : DASH) },
	{ label: 'المراجعة', get: (r) => txt(r.revision_lesson) },
	{
		label: 'تقييم المراجعة',
		get: (r) => (r.revision_rating != null ? ratingLabel(r.revision_rating) : DASH)
	},
	{ label: 'الأدب', get: (r) => (r.attitude != null ? attitudeLabel(r.attitude) : DASH) },
	{ label: 'نقاط إضافية', get: (r) => String(r.added_points ?? 0) },
	{ label: 'الواجب', get: (r) => txt(r.homework) },
	{ label: 'ملاحظات', get: (r) => txt(r.notes) },
	{ label: 'الصعوبات', get: (r) => txt(r.problems) }
];

/** Diff the record's current values against its baseline (or a blank "before"). */
function diff(rec: CachedRecord): FieldChange[] {
	const before: FieldSource | null = rec.localOnly ? null : (rec.baseline as RecordBaseline | null);
	const out: FieldChange[] = [];
	for (const f of FIELDS) {
		const now = f.get(rec);
		const old = before ? f.get(before as FieldSource) : DASH;
		if (now !== old) out.push({ label: f.label, old, new: now });
	}
	return out;
}

/** A short Arabic one-liner of what a dirty record carries (collapsed view). */
function describe(r: CachedRecord): string {
	const bits: string[] = [];
	bits.push(fmtAttendance(r.present, r.excused, r.late));
	if (r.rating != null || r.exam_to != null || r.exam_from != null || r.exam_total != null) {
		bits.push('تسميع');
	}
	if (r.revision_lesson) bits.push('مراجعة');
	if (r.attitude != null) bits.push('أدب');
	if ((r.added_points ?? 0) !== 0) bits.push('نقاط إضافية');
	return bits.join(' · ');
}

/** List the local edits not yet pushed, newest first, with the student's name + diff. */
export async function listPendingChanges(): Promise<PendingChange[]> {
	const dirty = await db.records.where('dirty').equals(1).toArray();
	const out: PendingChange[] = [];
	for (const r of dirty) {
		const s = await db.students.get(r.student_id);
		out.push({
			id: r.id,
			studentName: s?.full_name ?? 'طالب',
			dateIso: r.record_date,
			detail: describe(r),
			localOnly: r.localOnly === 1,
			changes: diff(r),
			syncError: r.syncError ?? null,
			studentId: r.student_id,
			halaqahId: r.halaqah_id
		});
	}
	out.sort(
		(a, b) => b.dateIso.localeCompare(a.dateIso) || a.studentName.localeCompare(b.studentName)
	);
	return out;
}
