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
	exam_from: number | null;
	exam_to: number | null;
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
}
