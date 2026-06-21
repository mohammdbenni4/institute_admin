// Typed CRUD helpers, one object per backend resource the teacher app needs.

import { api, qs } from './client';
import type {
	BulkAttendanceRequest,
	BulkAttendanceResponse,
	DailyRecord,
	DailyRecordCreate,
	DailyRecordUpdate,
	Halaqah,
	Paginated,
	PageParams,
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
		}
	) => api.get<Paginated<DailyRecord>>(`/daily-records${qs(params)}`),
	get: (id: UUID) => api.get<DailyRecord>(`/daily-records/${id}`),
	create: (body: DailyRecordCreate) => api.post<DailyRecord>('/daily-records', body),
	update: (id: UUID, body: DailyRecordUpdate) =>
		api.patch<DailyRecord>(`/daily-records/${id}`, body),
	remove: (id: UUID) => api.delete(`/daily-records/${id}`),
	bulkAttendance: (body: BulkAttendanceRequest) =>
		api.post<BulkAttendanceResponse>('/daily-records/bulk-attendance', body)
};

export const scoringApi = {
	get: () => api.get<ScoringSettings>('/scoring-settings')
};
