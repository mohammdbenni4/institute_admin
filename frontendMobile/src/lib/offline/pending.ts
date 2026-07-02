// Human-readable summary of the records still awaiting upload, for the sync sheet.

import { db, type CachedRecord } from './db';

export interface PendingChange {
	id: string;
	studentName: string;
	dateIso: string;
	detail: string;
}

/** A short Arabic description of what a dirty record carries. */
function describe(r: CachedRecord): string {
	const bits: string[] = [];
	bits.push(r.present ? 'حاضر' : r.excused ? 'أذن' : 'غائب');
	if (r.rating != null || r.exam_to != null || r.exam_from != null || r.exam_total != null) {
		bits.push('تسميع');
	}
	if (r.revision_lesson) bits.push('مراجعة');
	if (r.attitude != null) bits.push('أدب');
	if ((r.added_points ?? 0) !== 0) bits.push('نقاط إضافية');
	return bits.join(' · ');
}

/** List the local edits not yet pushed, newest first, with the student's name. */
export async function listPendingChanges(): Promise<PendingChange[]> {
	const dirty = await db.records.where('dirty').equals(1).toArray();
	const out: PendingChange[] = [];
	for (const r of dirty) {
		const s = await db.students.get(r.student_id);
		out.push({
			id: r.id,
			studentName: s?.full_name ?? 'طالب',
			dateIso: r.record_date,
			detail: describe(r)
		});
	}
	out.sort(
		(a, b) => b.dateIso.localeCompare(a.dateIso) || a.studentName.localeCompare(b.studentName)
	);
	return out;
}
