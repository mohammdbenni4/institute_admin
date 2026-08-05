// Typed CRUD helpers, one object per backend resource the teacher app needs.

import { api, qs } from './client';
import type {
	BulkAttendanceRequest,
	BulkAttendanceResponse,
	BulkUpsertRequest,
	BulkUpsertResponse,
	LatestRecitationsResponse,
	NextExamItem,
	ParentSummon,
	ParentSummonCreate,
	ParentSummonList,
	UpcomingExam,
	UpcomingExamCreate,
	DailyRecord,
	DailyRecordCreate,
	DailyRecordUpdate,
	Halaqah,
	Paginated,
	PageParams,
	Problem,
	ScoringSettings,
	Student,
	Teacher,
	UUID
} from './types';

export const teachersApi = {
	/** The signed-in user's own teacher profile (404 if the user isn't a teacher). */
	me: () => api.get<Teacher>('/teachers/me')
};

export const halaqahsApi = {
	list: (params?: PageParams & { teacher_id?: UUID }) =>
		api.get<Paginated<Halaqah>>(`/halaqahs${qs(params)}`),
	get: (id: UUID) => api.get<Halaqah>(`/halaqahs/${id}`)
};

export const studentsApi = {
	list: (params?: PageParams & { halaqah_id?: UUID | null }) =>
		api.get<Paginated<Student>>(`/students${qs(params)}`),
	get: (id: UUID) => api.get<Student>(`/students/${id}`)
};

export const dailyRecordsApi = {
	list: (
		params?: PageParams & {
			student_id?: UUID;
			teacher_id?: UUID;
			halaqah_id?: UUID;
			record_date?: string;
			date_from?: string;
			date_to?: string;
		}
	) => api.get<Paginated<DailyRecord>>(`/daily-records${qs(params)}`),
	get: (id: UUID) => api.get<DailyRecord>(`/daily-records/${id}`),
	create: (body: DailyRecordCreate) => api.post<DailyRecord>('/daily-records', body),
	update: (id: UUID, body: DailyRecordUpdate) =>
		api.patch<DailyRecord>(`/daily-records/${id}`, body),
	remove: (id: UUID) => api.delete(`/daily-records/${id}`),
	bulkAttendance: (body: BulkAttendanceRequest) =>
		api.post<BulkAttendanceResponse>('/daily-records/bulk-attendance', body),
	/** Idempotent batch upload keyed by (student, date) — one request per outbox drain. */
	bulkUpsert: (body: BulkUpsertRequest) =>
		api.post<BulkUpsertResponse>('/daily-records/bulk-upsert', body),
	/** Per-student last recitation + last homework, with no date-window guessing. */
	latestRecitations: (studentIds: UUID[], before?: string) =>
		api.get<LatestRecitationsResponse>(
			`/daily-records/latest-recitations?${studentIds
				.map((id) => `student_ids=${encodeURIComponent(id)}`)
				.join('&')}${before ? `&before=${before}` : ''}`
		)
};

export const parentSummonsApi = {
	list: (params?: PageParams & { status?: string; student_id?: UUID }) =>
		api.get<ParentSummonList>(`/parent-summons${qs(params)}`),
	create: (body: ParentSummonCreate) => api.post<ParentSummon>('/parent-summons', body)
};

export const upcomingExamsApi = {
	list: (params?: PageParams & { student_id?: UUID; halaqah_id?: UUID; status?: string }) =>
		api.get<{ items: UpcomingExam[]; total: number }>(`/upcoming-exams${qs(params)}`),
	create: (body: UpcomingExamCreate) => api.post<UpcomingExam>('/upcoming-exams', body),
	update: (id: UUID, body: Partial<UpcomingExamCreate> & { status?: string; clear?: string[] }) =>
		api.patch<UpcomingExam>(`/upcoming-exams/${id}`, body),
	remove: (id: UUID) => api.delete(`/upcoming-exams/${id}`),
	/** The soonest pending exam per student — one request for a whole halaqah. */
	next: (studentIds: UUID[]) =>
		api.get<{ items: NextExamItem[] }>(
			`/upcoming-exams/next?${studentIds
				.map((id) => `student_ids=${encodeURIComponent(id)}`)
				.join('&')}`
		)
};

export const scoringApi = {
	get: () => api.get<ScoringSettings>('/scoring-settings')
};

export const problemsApi = {
	list: (params?: PageParams) => api.get<Paginated<Problem>>(`/problems${qs(params)}`)
};
