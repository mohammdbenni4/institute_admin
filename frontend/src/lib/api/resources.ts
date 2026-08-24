// Typed CRUD helpers, one object per backend resource.

import { api, qs } from './client';
import type {
	AnalyticsOverview,
	AtRiskResponse,
	AttendanceMatrix,
	AttendanceMatrixParams,
	DailyRecord,
	Halaqah,
	HalaqahCreate,
	InstituteSettings,
	LeaderboardResponse,
	Problem,
	ProblemCreate,
	ProblemLevel,
	ProblemLevelCreate,
	ProblemLevelUpdate,
	ProblemUpdate,
	ScoringPreset,
	ScoringPresetWrite,
	ScoringSettings,
	HalaqahType,
	HalaqahTypeCreate,
	HalaqahTypeUpdate,
	HalaqahUpdate,
	DailyRecordCreate,
	DailyRecordUpdate,
	Paginated,
	PageParams,
	ParentSummon,
	ParentSummonList,
	ParentSummonUpdate,
	UpcomingExam,
	Student,
	StudentCreate,
	StudentImportResponse,
	StudentUpdate,
	Teacher,
	TeacherCreate,
	TeacherUpdate,
	Time,
	TimeCreate,
	TimeUpdate,
	User,
	UserCreate,
	UserUpdate,
	UUID
} from './types';

export const usersApi = {
	list: (params?: PageParams) => api.get<Paginated<User>>(`/users${qs(params)}`),
	get: (id: UUID) => api.get<User>(`/users/${id}`),
	create: (body: UserCreate) => api.post<User>('/users', body),
	update: (id: UUID, body: UserUpdate) => api.patch<User>(`/users/${id}`, body),
	remove: (id: UUID) => api.delete(`/users/${id}`)
};

export const teachersApi = {
	list: (params?: PageParams) => api.get<Paginated<Teacher>>(`/teachers${qs(params)}`),
	get: (id: UUID) => api.get<Teacher>(`/teachers/${id}`),
	create: (body: TeacherCreate) => api.post<Teacher>('/teachers', body),
	update: (id: UUID, body: TeacherUpdate) => api.patch<Teacher>(`/teachers/${id}`, body),
	remove: (id: UUID) => api.delete(`/teachers/${id}`)
};

export const studentsApi = {
	list: (params?: PageParams & { halaqah_id?: UUID | null }) =>
		api.get<Paginated<Student>>(`/students${qs(params)}`),
	get: (id: UUID) => api.get<Student>(`/students/${id}`),
	create: (body: StudentCreate) => api.post<Student>('/students', body),
	importBulk: (items: StudentCreate[]) =>
		api.post<StudentImportResponse>('/students/import', { items }),
	update: (id: UUID, body: StudentUpdate) => api.patch<Student>(`/students/${id}`, body),
	remove: (id: UUID) => api.delete(`/students/${id}`)
};

export const halaqahsApi = {
	list: (params?: PageParams & { teacher_id?: UUID }) =>
		api.get<Paginated<Halaqah>>(`/halaqahs${qs(params)}`),
	get: (id: UUID) => api.get<Halaqah>(`/halaqahs/${id}`),
	create: (body: HalaqahCreate) => api.post<Halaqah>('/halaqahs', body),
	update: (id: UUID, body: HalaqahUpdate) => api.patch<Halaqah>(`/halaqahs/${id}`, body),
	remove: (id: UUID) => api.delete(`/halaqahs/${id}`)
};

export const halaqahTypesApi = {
	list: (params?: PageParams) => api.get<Paginated<HalaqahType>>(`/halaqah-types${qs(params)}`),
	get: (id: UUID) => api.get<HalaqahType>(`/halaqah-types/${id}`),
	create: (body: HalaqahTypeCreate) => api.post<HalaqahType>('/halaqah-types', body),
	update: (id: UUID, body: HalaqahTypeUpdate) =>
		api.patch<HalaqahType>(`/halaqah-types/${id}`, body),
	remove: (id: UUID) => api.delete(`/halaqah-types/${id}`)
};

export const timesApi = {
	list: (params?: PageParams) => api.get<Paginated<Time>>(`/times${qs(params)}`),
	get: (id: UUID) => api.get<Time>(`/times/${id}`),
	create: (body: TimeCreate) => api.post<Time>('/times', body),
	update: (id: UUID, body: TimeUpdate) => api.patch<Time>(`/times/${id}`, body),
	remove: (id: UUID) => api.delete(`/times/${id}`)
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
	/** Partial update — used by the admin attendance editor so recording an إذن
	 *  never overwrites the day's recitation, rating or points. */
	update: (id: UUID, body: DailyRecordUpdate) =>
		api.patch<DailyRecord>(`/daily-records/${id}`, body),
	create: (body: DailyRecordCreate) => api.post<DailyRecord>('/daily-records', body)
};

type AnalyticsParams = { date_from?: string; date_to?: string };

export const analyticsApi = {
	overview: (params?: AnalyticsParams) =>
		api.get<AnalyticsOverview>(`/analytics/overview${qs(params)}`),
	leaderboard: (params?: AnalyticsParams & { top?: number }) =>
		api.get<LeaderboardResponse>(`/analytics/halaqah-leaderboard${qs(params)}`),
	atRisk: (params?: AnalyticsParams) => api.get<AtRiskResponse>(`/analytics/at-risk${qs(params)}`),
	/** Server-aggregated attendance heat-map: one row per student, already filtered,
	 *  sorted and paginated (replaces paging every daily record of the month). */
	attendanceMatrix: (params?: AttendanceMatrixParams) =>
		api.get<AttendanceMatrix>(`/analytics/attendance-matrix${qs(params)}`)
};

export const instituteApi = {
	get: () => api.get<InstituteSettings>('/institute-settings'),
	update: (body: InstituteSettings) => api.put<InstituteSettings>('/institute-settings', body)
};

export const parentSummonsApi = {
	list: (params?: PageParams & { status?: string; student_id?: UUID; teacher_id?: UUID }) =>
		api.get<ParentSummonList>(`/parent-summons${qs(params)}`),
	update: (id: UUID, body: ParentSummonUpdate) =>
		api.patch<ParentSummon>(`/parent-summons/${id}`, body),
	remove: (id: UUID) => api.delete(`/parent-summons/${id}`)
};

export const upcomingExamsApi = {
	list: (params?: PageParams & { student_id?: UUID; halaqah_id?: UUID; status?: string }) =>
		api.get<{ items: UpcomingExam[]; total: number }>(`/upcoming-exams${qs(params)}`),
	remove: (id: UUID) => api.delete(`/upcoming-exams/${id}`)
};

export const scoringApi = {
	get: () => api.get<ScoringSettings>('/scoring-settings'),
	update: (body: ScoringSettings) => api.put<ScoringSettings>('/scoring-settings', body)
};

/** Named pricing systems assignable per student. Reading is open to any authenticated
 *  user (the teacher app lists them); writing is super-admin, i.e. this dashboard. */
export const scoringPresetsApi = {
	list: () => api.get<{ items: ScoringPreset[]; total: number }>('/scoring-presets'),
	create: (body: ScoringPresetWrite) => api.post<ScoringPreset>('/scoring-presets', body),
	update: (id: UUID, body: ScoringPresetWrite) =>
		api.put<ScoringPreset>(`/scoring-presets/${id}`, body),
	remove: (id: UUID) => api.delete(`/scoring-presets/${id}`)
};

export const problemLevelsApi = {
	list: (params?: PageParams) => api.get<Paginated<ProblemLevel>>(`/problem-levels${qs(params)}`),
	get: (id: UUID) => api.get<ProblemLevel>(`/problem-levels/${id}`),
	create: (body: ProblemLevelCreate) => api.post<ProblemLevel>('/problem-levels', body),
	update: (id: UUID, body: ProblemLevelUpdate) =>
		api.patch<ProblemLevel>(`/problem-levels/${id}`, body),
	remove: (id: UUID) => api.delete(`/problem-levels/${id}`)
};

export const problemsApi = {
	list: (params?: PageParams & { level_id?: UUID }) =>
		api.get<Paginated<Problem>>(`/problems${qs(params)}`),
	get: (id: UUID) => api.get<Problem>(`/problems/${id}`),
	create: (body: ProblemCreate) => api.post<Problem>('/problems', body),
	update: (id: UUID, body: ProblemUpdate) => api.patch<Problem>(`/problems/${id}`, body),
	remove: (id: UUID) => api.delete(`/problems/${id}`)
};
