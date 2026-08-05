// TypeScript mirrors of the backend (FastAPI) request/response schemas used by
// the teacher app. Keep in sync with
// `backend/src/institute_administration/modules/*/schemas.py`.

export type UUID = string;
/** ISO date (`YYYY-MM-DD`). */
export type IsoDate = string;
/** ISO datetime. */
export type IsoDateTime = string;

export type UserRole = 'super_admin' | 'teacher';

/** Generic paginated envelope returned by every list endpoint. */
export interface Paginated<T> {
	items: T[];
	total: number;
	limit: number;
	offset: number;
}

export interface PageParams {
	limit?: number;
	offset?: number;
}

// --- Auth ------------------------------------------------------------------
export interface TokenResponse {
	access_token: string;
	refresh_token: string;
	token_type: string;
}

export interface User {
	id: UUID;
	full_name: string;
	email: string;
	role: UserRole;
	date_of_birth: IsoDate | null;
	is_active: boolean;
	created_at: IsoDateTime;
	updated_at: IsoDateTime;
}

// --- Teachers --------------------------------------------------------------
export interface Teacher {
	id: UUID;
	user_id: UUID;
	full_name: string;
	email: string;
	date_of_birth: IsoDate | null;
	is_active: boolean;
	academic_study: string;
	islamic_study: string;
	is_assistant: boolean;
	created_at: IsoDateTime;
	updated_at: IsoDateTime;
}

// --- Halaqahs --------------------------------------------------------------
export interface Halaqah {
	id: UUID;
	name: string;
	level: string | null;
	age: string | null;
	teacher_id: UUID;
	teacher_name: string;
	halaqah_type_id: UUID;
	halaqah_type_name: string;
	time_id: UUID | null;
	time_name: string | null;
	/** Weekday -> session window, only for days the halaqah actually meets. */
	schedule: Record<string, { from: string; to: string }>;
	number_of_students: number;
	created_at: IsoDateTime;
	updated_at: IsoDateTime;
}

// --- Students --------------------------------------------------------------
export interface Student {
	id: UUID;
	full_name: string;
	father_name: string;
	father_number: string;
	date_of_birth: IsoDate | null;
	mother_number: string | null;
	orphan_of: 'father' | 'mother' | 'both' | null;
	residential_area: string | null;
	accepted_at: IsoDate | null;
	notes: string | null;
	halaqah_id: UUID | null;
	created_at: IsoDateTime;
	updated_at: IsoDateTime;
}

// --- Problems (الصعوبات) ---------------------------------------------------
export interface ProblemBrief {
	id: UUID;
	name: string;
	level_id: UUID;
	level_name: string;
}

export interface Problem {
	id: UUID;
	name: string;
	level_id: UUID;
	level_name: string;
	created_at: IsoDateTime;
	updated_at: IsoDateTime;
}

// --- Daily records ---------------------------------------------------------
/** 1..4 examination rating (4 = best). */
export type Rating = 1 | 2 | 3 | 4;
/** 1..3 behaviour rating (3 = best). */
export type Attitude = 1 | 2 | 3;

export interface DailyRecord {
	id: UUID;
	student_id: UUID;
	teacher_id: UUID;
	halaqah_id: UUID;
	record_date: IsoDate;
	present: boolean;
	excused: boolean;
	/** «متأخر» — a qualifier on attendance; a late student is still present. */
	late: boolean;
	/** Why an absence was excused (أذن). */
	excuse_reason: string | null;
	exam_from: number | null;
	exam_to: number | null;
	/** A page *count*, so it may be fractional («نصف صفحة» = 0.5). */
	exam_total: number | null;
	homework: string | null;
	problems: string | null;
	rating: Rating | null;
	revision_lesson: string | null;
	revision_rating: Rating | null;
	attitude: Attitude | null;
	added_points: number;
	notes: string | null;
	tagged_problems: ProblemBrief[];
	// Server-computed reward-card scores (read-only).
	card_present: number;
	card_exam: number;
	card_revision: number;
	card_attitude: number;
	total_points: number;
	created_at: IsoDateTime;
	updated_at: IsoDateTime;
}

export interface DailyRecordCreate {
	student_id: UUID;
	teacher_id: UUID;
	halaqah_id: UUID;
	present: boolean;
	excused?: boolean;
	record_date?: IsoDate | null;
	exam_from?: number | null;
	exam_to?: number | null;
	exam_total?: number | null;
	homework?: string | null;
	problems?: string | null;
	rating?: Rating | null;
	revision_lesson?: string | null;
	revision_rating?: Rating | null;
	attitude?: Attitude | null;
	added_points?: number;
	notes?: string | null;
	problem_ids?: UUID[];
}

/** PATCH body: every field optional; `student_id` is immutable server-side. */
export type DailyRecordUpdate = Partial<Omit<DailyRecordCreate, 'student_id'>>;

// --- Bulk attendance -------------------------------------------------------
export interface BulkAttendanceEntry {
	student_id: UUID;
	present: boolean;
	excused?: boolean;
}

export interface BulkAttendanceRequest {
	halaqah_id: UUID;
	teacher_id: UUID;
	record_date?: IsoDate | null;
	entries: BulkAttendanceEntry[];
}

export interface BulkAttendanceResponse {
	record_date: IsoDate;
	created: number;
	updated: number;
}

// --- Scoring settings ------------------------------------------------------
export interface ScoringSettings {
	present_points: number;
	rating_4_points: number;
	rating_3_points: number;
	rating_2_points: number;
	rating_1_points: number;
	revision_4_points: number;
	revision_3_points: number;
	revision_2_points: number;
	revision_1_points: number;
	attitude_3_points: number;
	attitude_2_points: number;
	attitude_1_points: number;
	absent_points: number;
	excused_points: number;
	/** Points for «متأخر»; defaults to the present weight. */
	late_points: number;
}

/** One record in a bulk upload, keyed by its natural (student, date) pair. */
export interface BulkUpsertItem {
	student_id: UUID;
	record_date: IsoDate;
	present: boolean;
	excused: boolean;
	late: boolean;
	excuse_reason: string | null;
	exam_from: number | null;
	exam_to: number | null;
	/** A page *count*, so it may be fractional («نصف صفحة» = 0.5). */
	exam_total: number | null;
	homework: string | null;
	problems: string | null;
	rating: Rating | null;
	revision_lesson: string | null;
	revision_rating: Rating | null;
	attitude: Attitude | null;
	added_points: number;
	notes: string | null;
	problem_ids: UUID[];
}

export interface BulkUpsertRequest {
	halaqah_id: UUID;
	teacher_id: UUID;
	records: BulkUpsertItem[];
}

export interface BulkUpsertResponse {
	items: DailyRecord[];
	created: number;
	updated: number;
}

/** A student's last recitation and the homework they were last assigned. */
export interface LatestRecitationItem {
	student_id: UUID;
	last_recitation: DailyRecord | null;
	homework: string | null;
}

export interface LatestRecitationsResponse {
	items: LatestRecitationItem[];
}

// --- استدعاء ولي الأمر ------------------------------------------------------
export type SummonStatus = 'new' | 'reviewing' | 'completed';

export interface ParentSummon {
	id: UUID;
	student_id: UUID;
	student_name: string;
	father_name: string | null;
	father_number: string | null;
	teacher_id: UUID;
	teacher_name: string;
	halaqah_id: UUID;
	halaqah_name: string;
	reason: string;
	status: SummonStatus;
	/** Server-rendered Arabic label — one source of truth for the wording. */
	status_label: string;
	/** The administration's reply back to the teacher. */
	admin_response: string | null;
	handled_at: IsoDateTime | null;
	created_at: IsoDateTime;
	updated_at: IsoDateTime;
}

export interface ParentSummonList {
	items: ParentSummon[];
	total: number;
	limit: number;
	offset: number;
	counts: Record<SummonStatus, number>;
}

export interface ParentSummonCreate {
	student_id: UUID;
	halaqah_id: UUID;
	reason: string;
}

// --- الاختبار القادم --------------------------------------------------------
export type UpcomingExamStatus = 'pending' | 'done' | 'cancelled';

export interface UpcomingExam {
	id: UUID;
	student_id: UUID;
	student_name: string;
	teacher_id: UUID;
	teacher_name: string;
	halaqah_id: UUID;
	halaqah_name: string;
	scheduled_date: IsoDate;
	part: number | null;
	exam_from: number | null;
	exam_to: number | null;
	notes: string | null;
	status: UpcomingExamStatus;
	status_label: string;
	/** Ready-made Arabic coverage description, e.g. «الجزء 5 · من 3 إلى 8». */
	summary: string;
}

export interface UpcomingExamCreate {
	student_id: UUID;
	halaqah_id: UUID;
	scheduled_date: IsoDate;
	part?: number | null;
	exam_from?: number | null;
	exam_to?: number | null;
	notes?: string | null;
}

export interface NextExamItem {
	student_id: UUID;
	exam: UpcomingExam | null;
}
