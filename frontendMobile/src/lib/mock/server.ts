// Routes API calls to the in-memory/localStorage mock dataset instead of a real
// backend, so the app is fully usable (browse, edit, create) with no server.

import { computeScores } from '$lib/labels';
import type {
	BulkAttendanceRequest,
	BulkAttendanceResponse,
	BulkUpsertRequest,
	BulkUpsertResponse,
	DailyRecord,
	DailyRecordCreate,
	DailyRecordUpdate,
	LatestRecitationsResponse,
	NextExamItem,
	Paginated,
	ParentSummon,
	ParentSummonCreate,
	ParentSummonList,
	Problem,
	ScoringSettings,
	StudentUpdate,
	SummonStatus,
	TokenResponse,
	UpcomingExam,
	UpcomingExamCreate,
	UpcomingExamStatus
} from '$lib/api/types';
import { DEMO_EMAIL, DEMO_PASSWORD } from './config';
import { loadDb, saveDb, type MockDb } from './data';

const ACCESS_TOKEN = 'mock-access-token';
const REFRESH_TOKEN = 'mock-refresh-token';

let uidCounter = 0;
function uid(prefix: string): string {
	uidCounter += 1;
	return `${prefix}-${Date.now().toString(36)}-${uidCounter}`;
}

function today(): string {
	return new Date().toISOString().slice(0, 10);
}

function clone<T>(v: T): T {
	return JSON.parse(JSON.stringify(v));
}

/** The scoring config that actually prices a student's points: their assigned preset
 *  (if any and still known) falling back to the halaqah's single default settings. */
function scoringFor(db: MockDb, studentId: string): ScoringSettings {
	const student = db.students.find((s) => s.id === studentId);
	const preset = student?.scoring_preset_id
		? db.scoringPresets.find((p) => p.id === student.scoring_preset_id)
		: null;
	return preset ?? db.scoring;
}

function notFound(): { status: number; data: unknown } {
	return { status: 404, data: { detail: 'العنصر المطلوب غير موجود', code: 'not_found' } };
}

function paginate<T>(items: T[], q: URLSearchParams): Paginated<T> {
	const limit = q.get('limit') ? Number(q.get('limit')) : 50;
	const offset = q.get('offset') ? Number(q.get('offset')) : 0;
	return { items: items.slice(offset, offset + limit), total: items.length, limit, offset };
}

const EXAM_STATUS_LABEL: Record<UpcomingExamStatus, string> = {
	pending: 'قيد الانتظار',
	done: 'تم',
	cancelled: 'ملغى'
};

const SUMMON_STATUS_LABEL: Record<SummonStatus, string> = {
	new: 'جديد',
	reviewing: 'قيد المراجعة',
	completed: 'مكتمل'
};

function examSummary(input: {
	part?: number | null;
	exam_from?: number | null;
	exam_to?: number | null;
}): string {
	const bits: string[] = [];
	if (input.part != null) bits.push(`الجزء ${input.part}`);
	if (input.exam_from != null && input.exam_to != null)
		bits.push(`من ${input.exam_from} إلى ${input.exam_to}`);
	return bits.join(' · ') || 'بدون تفاصيل';
}

function buildRecord(db: MockDb, input: DailyRecordCreate, problemIds?: string[]): DailyRecord {
	const now = new Date().toISOString();
	const ids = problemIds ?? input.problem_ids ?? [];
	const tagged = ids
		.map((id) => db.problems.find((p) => p.id === id))
		.filter((p): p is Problem => !!p)
		.map((p) => ({ id: p.id, name: p.name, level_id: p.level_id, level_name: p.level_name }));
	const scores = computeScores(
		{
			present: input.present,
			excused: input.excused ?? false,
			rating: input.rating ?? null,
			revision_rating: input.revision_rating ?? null,
			attitude: input.attitude ?? null,
			added_points: input.added_points ?? 0
		},
		scoringFor(db, input.student_id)
	);
	return {
		id: uid('record'),
		student_id: input.student_id,
		teacher_id: input.teacher_id,
		halaqah_id: input.halaqah_id,
		record_date: input.record_date ?? today(),
		present: input.present,
		excused: input.excused ?? false,
		late: false,
		excuse_reason: null,
		exam_from: input.exam_from ?? null,
		exam_to: input.exam_to ?? null,
		exam_from_line: input.exam_from_line ?? null,
		exam_to_line: input.exam_to_line ?? null,
		exam_total: input.exam_total ?? null,
		homework: input.homework ?? null,
		problems: input.problems ?? null,
		rating: input.rating ?? null,
		revision_lesson: input.revision_lesson ?? null,
		revision_rating: input.revision_rating ?? null,
		attitude: input.attitude ?? null,
		added_points: input.added_points ?? 0,
		notes: input.notes ?? null,
		tagged_problems: tagged,
		card_present: scores.present,
		card_exam: scores.exam,
		card_revision: scores.revision,
		card_attitude: scores.attitude,
		total_points: scores.total,
		created_at: now,
		updated_at: now
	};
}

function applyUpdate(db: MockDb, rec: DailyRecord, patch: DailyRecordUpdate): DailyRecord {
	const merged: DailyRecord = {
		...rec,
		...patch,
		record_date: patch.record_date ?? rec.record_date,
		updated_at: new Date().toISOString()
	};
	if (patch.problem_ids) {
		merged.tagged_problems = patch.problem_ids
			.map((id) => db.problems.find((p) => p.id === id))
			.filter((p): p is Problem => !!p)
			.map((p) => ({ id: p.id, name: p.name, level_id: p.level_id, level_name: p.level_name }));
	}
	const scores = computeScores(
		{
			present: merged.present,
			excused: merged.excused,
			late: merged.late,
			rating: merged.rating,
			revision_rating: merged.revision_rating,
			attitude: merged.attitude,
			added_points: merged.added_points
		},
		scoringFor(db, merged.student_id)
	);
	merged.card_present = scores.present;
	merged.card_exam = scores.exam;
	merged.card_revision = scores.revision;
	merged.card_attitude = scores.attitude;
	merged.total_points = scores.total;
	return merged;
}

export async function mockDispatch(
	method: string,
	fullPath: string,
	body?: unknown
): Promise<{ status: number; data: unknown }> {
	const [pathname, queryString = ''] = fullPath.split('?');
	const q = new URLSearchParams(queryString);
	const db = loadDb();

	// ---- auth ---------------------------------------------------------------
	if (method === 'POST' && pathname === '/auth/login') {
		const { email, password } = (body ?? {}) as { email?: string; password?: string };
		if ((email ?? '').trim().toLowerCase() !== DEMO_EMAIL || password !== DEMO_PASSWORD) {
			return {
				status: 401,
				data: { detail: 'البريد الإلكتروني أو كلمة المرور غير صحيحة', code: 'bad_credentials' }
			};
		}
		const tr: TokenResponse = {
			access_token: ACCESS_TOKEN,
			refresh_token: REFRESH_TOKEN,
			token_type: 'bearer'
		};
		return { status: 200, data: tr };
	}
	if (method === 'POST' && pathname === '/auth/refresh') {
		const tr: TokenResponse = {
			access_token: ACCESS_TOKEN,
			refresh_token: REFRESH_TOKEN,
			token_type: 'bearer'
		};
		return { status: 200, data: tr };
	}
	if (method === 'GET' && pathname === '/auth/me') {
		return { status: 200, data: clone(db.user) };
	}
	if (method === 'GET' && pathname === '/teachers/me') {
		return { status: 200, data: clone(db.teacher) };
	}

	// ---- halaqahs -------------------------------------------------------------
	if (method === 'GET' && pathname === '/halaqahs') {
		let items = db.halaqahs;
		const teacherId = q.get('teacher_id');
		if (teacherId) items = items.filter((h) => h.teacher_id === teacherId);
		return { status: 200, data: paginate(items, q) };
	}
	let m = pathname.match(/^\/halaqahs\/([^/]+)$/);
	if (method === 'GET' && m) {
		const h = db.halaqahs.find((x) => x.id === m![1]);
		return h ? { status: 200, data: clone(h) } : notFound();
	}

	// ---- students ---------------------------------------------------------
	if (method === 'GET' && pathname === '/students') {
		let items = db.students;
		const halaqahId = q.get('halaqah_id');
		if (halaqahId) items = items.filter((s) => s.halaqah_id === halaqahId);
		return { status: 200, data: paginate(items, q) };
	}
	m = pathname.match(/^\/students\/([^/]+)$/);
	if (method === 'GET' && m) {
		const s = db.students.find((x) => x.id === m![1]);
		return s ? { status: 200, data: clone(s) } : notFound();
	}
	// Teaching preferences only. Mirrors the real API, where the full PATCH /students/{id}
	// is super-admin and a teacher may only touch these two fields via /track.
	m = pathname.match(/^\/students\/([^/]+)\/track$/);
	if (method === 'PATCH' && m) {
		const idx = db.students.findIndex((x) => x.id === m![1]);
		if (idx === -1) return notFound();
		const patch = body as StudentUpdate;
		db.students[idx] = {
			...db.students[idx],
			...patch,
			updated_at: new Date().toISOString()
		};
		saveDb(db);
		return { status: 200, data: clone(db.students[idx]) };
	}

	// ---- problems / scoring -------------------------------------------------
	if (method === 'GET' && pathname === '/problems') {
		return { status: 200, data: paginate(db.problems, q) };
	}
	if (method === 'GET' && pathname === '/scoring-settings') {
		return { status: 200, data: clone(db.scoring) };
	}
	if (method === 'GET' && pathname === '/scoring-presets') {
		return { status: 200, data: paginate(db.scoringPresets, q) };
	}

	// ---- daily records ------------------------------------------------------
	if (method === 'GET' && pathname === '/daily-records/latest-recitations') {
		const studentIds = q.getAll('student_ids');
		const before = q.get('before');
		const items = studentIds.map((sid) => {
			let recs = db.records.filter((r) => r.student_id === sid);
			if (before) recs = recs.filter((r) => r.record_date < before);
			recs = [...recs].sort((a, b) => (a.record_date < b.record_date ? 1 : -1));
			const last = recs.find(
				(r) =>
					r.rating != null ||
					r.exam_from != null ||
					r.exam_to != null ||
					r.exam_total != null ||
					!!r.revision_lesson
			);
			const withHomework = recs.find((r) => r.homework && r.homework.trim() !== '');
			return {
				student_id: sid,
				last_recitation: last ? clone(last) : null,
				homework: withHomework?.homework ?? null
			};
		});
		const res: LatestRecitationsResponse = { items };
		return { status: 200, data: res };
	}
	if (method === 'GET' && pathname === '/daily-records') {
		let items = db.records;
		const studentId = q.get('student_id');
		const teacherId = q.get('teacher_id');
		const halaqahId = q.get('halaqah_id');
		const recordDate = q.get('record_date');
		const dateFrom = q.get('date_from');
		const dateTo = q.get('date_to');
		if (studentId) items = items.filter((r) => r.student_id === studentId);
		if (teacherId) items = items.filter((r) => r.teacher_id === teacherId);
		if (halaqahId) items = items.filter((r) => r.halaqah_id === halaqahId);
		if (recordDate) items = items.filter((r) => r.record_date === recordDate);
		if (dateFrom) items = items.filter((r) => r.record_date >= dateFrom);
		if (dateTo) items = items.filter((r) => r.record_date <= dateTo);
		items = [...items].sort((a, b) => (a.record_date < b.record_date ? 1 : -1));
		return { status: 200, data: paginate(items, q) };
	}
	m = pathname.match(/^\/daily-records\/([^/]+)$/);
	if (method === 'GET' && m) {
		const r = db.records.find((x) => x.id === m![1]);
		return r ? { status: 200, data: clone(r) } : notFound();
	}
	if (method === 'POST' && pathname === '/daily-records') {
		const rec = buildRecord(db, body as DailyRecordCreate);
		db.records.push(rec);
		saveDb(db);
		return { status: 201, data: clone(rec) };
	}
	if (method === 'PATCH' && m) {
		const idx = db.records.findIndex((x) => x.id === m![1]);
		if (idx === -1) return notFound();
		const updated = applyUpdate(db, db.records[idx], body as DailyRecordUpdate);
		db.records[idx] = updated;
		saveDb(db);
		return { status: 200, data: clone(updated) };
	}
	if (method === 'DELETE' && m) {
		const idx = db.records.findIndex((x) => x.id === m![1]);
		if (idx === -1) return notFound();
		db.records.splice(idx, 1);
		saveDb(db);
		return { status: 204, data: null };
	}
	if (method === 'POST' && pathname === '/daily-records/bulk-attendance') {
		const req = body as BulkAttendanceRequest;
		const date = req.record_date ?? today();
		let created = 0;
		let updated = 0;
		for (const entry of req.entries) {
			const idx = db.records.findIndex(
				(r) => r.student_id === entry.student_id && r.record_date === date
			);
			if (idx === -1) {
				const rec = buildRecord(db, {
					student_id: entry.student_id,
					teacher_id: req.teacher_id,
					halaqah_id: req.halaqah_id,
					record_date: date,
					present: entry.present,
					excused: entry.excused ?? false
				});
				db.records.push(rec);
				created++;
			} else {
				db.records[idx] = applyUpdate(db, db.records[idx], {
					present: entry.present,
					excused: entry.excused ?? false
				});
				updated++;
			}
		}
		saveDb(db);
		const res: BulkAttendanceResponse = { record_date: date, created, updated };
		return { status: 200, data: res };
	}
	if (method === 'POST' && pathname === '/daily-records/bulk-upsert') {
		const req = body as BulkUpsertRequest;
		let created = 0;
		let updated = 0;
		const items: DailyRecord[] = [];
		for (const item of req.records) {
			const idx = db.records.findIndex(
				(r) => r.student_id === item.student_id && r.record_date === item.record_date
			);
			if (idx === -1) {
				const rec = buildRecord(
					db,
					{
						student_id: item.student_id,
						teacher_id: req.teacher_id,
						halaqah_id: req.halaqah_id,
						record_date: item.record_date,
						present: item.present,
						excused: item.excused,
						exam_from: item.exam_from,
						exam_to: item.exam_to,
						exam_total: item.exam_total,
						homework: item.homework,
						problems: item.problems,
						rating: item.rating,
						revision_lesson: item.revision_lesson,
						revision_rating: item.revision_rating,
						attitude: item.attitude,
						added_points: item.added_points,
						notes: item.notes,
						problem_ids: item.problem_ids
					},
					item.problem_ids
				);
				rec.late = item.late;
				rec.excuse_reason = item.excuse_reason;
				db.records.push(rec);
				items.push(rec);
				created++;
			} else {
				const merged = applyUpdate(db, db.records[idx], {
					present: item.present,
					excused: item.excused,
					exam_from: item.exam_from,
					exam_to: item.exam_to,
					exam_total: item.exam_total,
					homework: item.homework,
					problems: item.problems,
					rating: item.rating,
					revision_lesson: item.revision_lesson,
					revision_rating: item.revision_rating,
					attitude: item.attitude,
					added_points: item.added_points,
					notes: item.notes,
					problem_ids: item.problem_ids
				});
				merged.late = item.late;
				merged.excuse_reason = item.excuse_reason;
				db.records[idx] = merged;
				items.push(merged);
				updated++;
			}
		}
		saveDb(db);
		const res: BulkUpsertResponse = { items: clone(items), created, updated };
		return { status: 200, data: res };
	}

	// ---- parent summons -----------------------------------------------------
	if (method === 'GET' && pathname === '/parent-summons') {
		let items = db.summons;
		const status = q.get('status');
		const studentId = q.get('student_id');
		if (status) items = items.filter((s) => s.status === status);
		if (studentId) items = items.filter((s) => s.student_id === studentId);
		items = [...items].sort((a, b) => (a.created_at < b.created_at ? 1 : -1));
		const page = paginate(items, q);
		const counts: Record<SummonStatus, number> = { new: 0, reviewing: 0, completed: 0 };
		for (const s of db.summons) counts[s.status]++;
		const res: ParentSummonList = { ...page, counts };
		return { status: 200, data: res };
	}
	if (method === 'POST' && pathname === '/parent-summons') {
		const req = body as ParentSummonCreate;
		const student = db.students.find((s) => s.id === req.student_id);
		const now = new Date().toISOString();
		const summon: ParentSummon = {
			id: uid('summon'),
			student_id: req.student_id,
			student_name: student?.full_name ?? '',
			father_name: student?.father_name ?? null,
			father_number: student?.father_number ?? null,
			teacher_id: db.teacher.id,
			teacher_name: db.teacher.full_name,
			halaqah_id: req.halaqah_id,
			halaqah_name: db.halaqahs.find((h) => h.id === req.halaqah_id)?.name ?? '',
			reason: req.reason,
			status: 'new',
			status_label: SUMMON_STATUS_LABEL.new,
			admin_response: null,
			handled_at: null,
			created_at: now,
			updated_at: now
		};
		db.summons.unshift(summon);
		saveDb(db);
		return { status: 201, data: clone(summon) };
	}

	// ---- upcoming exams -------------------------------------------------------
	if (method === 'GET' && pathname === '/upcoming-exams/next') {
		const studentIds = q.getAll('student_ids');
		const items: NextExamItem[] = studentIds.map((sid) => {
			const pending = db.exams
				.filter((e) => e.student_id === sid && e.status === 'pending')
				.sort((a, b) => (a.scheduled_date > b.scheduled_date ? 1 : -1));
			return { student_id: sid, exam: pending[0] ? clone(pending[0]) : null };
		});
		return { status: 200, data: { items } };
	}
	if (method === 'GET' && pathname === '/upcoming-exams') {
		let items = db.exams;
		const studentId = q.get('student_id');
		const halaqahId = q.get('halaqah_id');
		const status = q.get('status');
		if (studentId) items = items.filter((e) => e.student_id === studentId);
		if (halaqahId) items = items.filter((e) => e.halaqah_id === halaqahId);
		if (status) items = items.filter((e) => e.status === status);
		items = [...items].sort((a, b) => (a.scheduled_date > b.scheduled_date ? 1 : -1));
		const limit = q.get('limit') ? Number(q.get('limit')) : 50;
		const offset = q.get('offset') ? Number(q.get('offset')) : 0;
		return {
			status: 200,
			data: { items: items.slice(offset, offset + limit).map(clone), total: items.length }
		};
	}
	if (method === 'POST' && pathname === '/upcoming-exams') {
		const req = body as UpcomingExamCreate;
		const student = db.students.find((s) => s.id === req.student_id);
		const exam: UpcomingExam = {
			id: uid('exam'),
			student_id: req.student_id,
			student_name: student?.full_name ?? '',
			teacher_id: db.teacher.id,
			teacher_name: db.teacher.full_name,
			halaqah_id: req.halaqah_id,
			halaqah_name: db.halaqahs.find((h) => h.id === req.halaqah_id)?.name ?? '',
			scheduled_date: req.scheduled_date,
			part: req.part ?? null,
			exam_from: req.exam_from ?? null,
			exam_to: req.exam_to ?? null,
			notes: req.notes ?? null,
			status: 'pending',
			status_label: EXAM_STATUS_LABEL.pending,
			summary: examSummary(req)
		};
		db.exams.push(exam);
		saveDb(db);
		return { status: 201, data: clone(exam) };
	}
	m = pathname.match(/^\/upcoming-exams\/([^/]+)$/);
	if (method === 'PATCH' && m) {
		const idx = db.exams.findIndex((x) => x.id === m![1]);
		if (idx === -1) return notFound();
		const patch = body as Partial<UpcomingExamCreate> & {
			status?: UpcomingExamStatus;
			clear?: string[];
		};
		const merged: UpcomingExam = { ...db.exams[idx], ...patch };
		for (const field of patch.clear ?? []) {
			(merged as unknown as Record<string, unknown>)[field] = null;
		}
		if (patch.status) merged.status_label = EXAM_STATUS_LABEL[patch.status];
		merged.summary = examSummary(merged);
		db.exams[idx] = merged;
		saveDb(db);
		return { status: 200, data: clone(merged) };
	}
	if (method === 'DELETE' && m) {
		const idx = db.exams.findIndex((x) => x.id === m![1]);
		if (idx === -1) return notFound();
		db.exams.splice(idx, 1);
		saveDb(db);
		return { status: 204, data: null };
	}

	return {
		status: 404,
		data: { detail: `مسار غير معروف في بيانات العرض التجريبي: ${method} ${pathname}` }
	};
}
