// TypeScript mirrors of the backend (FastAPI) request/response schemas.
// Keep these in sync with `backend/src/institute_administration/modules/*/schemas.py`.

export type UUID = string;
/** ISO date (`YYYY-MM-DD`). */
export type IsoDate = string;
/** ISO datetime. */
export type IsoDateTime = string;

export type UserRole = 'super_admin' | 'teacher';
export type OrphanStatus = 'father' | 'mother' | 'both';

export const WEEKDAYS = [
	'saturday',
	'sunday',
	'monday',
	'tuesday',
	'wednesday',
	'thursday',
	'friday'
] as const;
export type Weekday = (typeof WEEKDAYS)[number];

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

// --- Users -----------------------------------------------------------------
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

export interface UserCreate {
	full_name: string;
	email: string;
	password: string;
	role: UserRole;
	date_of_birth?: IsoDate | null;
	is_active?: boolean;
}

export interface UserUpdate {
	full_name?: string;
	email?: string;
	password?: string;
	role?: UserRole;
	date_of_birth?: IsoDate | null;
	is_active?: boolean;
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

export interface TeacherCreate {
	full_name: string;
	email: string;
	password: string;
	academic_study: string;
	islamic_study: string;
	is_assistant?: boolean;
	date_of_birth?: IsoDate | null;
}

export interface TeacherUpdate {
	full_name?: string;
	email?: string;
	password?: string;
	date_of_birth?: IsoDate | null;
	is_active?: boolean;
	academic_study?: string;
	islamic_study?: string;
	is_assistant?: boolean;
}

// --- Students --------------------------------------------------------------
export interface Student {
	id: UUID;
	full_name: string;
	father_name: string;
	father_number: string;
	date_of_birth: IsoDate | null;
	mother_number: string | null;
	orphan_of: OrphanStatus | null;
	residential_area: string | null;
	accepted_at: IsoDate | null;
	notes: string | null;
	halaqah_id: UUID | null;
	created_at: IsoDateTime;
	updated_at: IsoDateTime;
}

export interface StudentCreate {
	full_name: string;
	father_name: string;
	father_number: string;
	date_of_birth?: IsoDate | null;
	mother_number?: string | null;
	orphan_of?: OrphanStatus | null;
	residential_area?: string | null;
	accepted_at?: IsoDate | null;
	notes?: string | null;
	halaqah_id?: UUID | null;
}

export type StudentUpdate = Partial<StudentCreate>;

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

export interface HalaqahCreate {
	name: string;
	teacher_id: UUID;
	halaqah_type_id: UUID;
	level?: string | null;
	age?: string | null;
	time_id?: UUID | null;
}

export type HalaqahUpdate = Partial<HalaqahCreate>;

// --- Halaqah types ---------------------------------------------------------
export interface HalaqahType {
	id: UUID;
	name: string;
	created_at: IsoDateTime;
	updated_at: IsoDateTime;
}

export interface HalaqahTypeCreate {
	name: string;
}

export type HalaqahTypeUpdate = Partial<HalaqahTypeCreate>;

// --- Times -----------------------------------------------------------------
/** A single day's time window. Wire format uses `from`/`to` (HH:MM). */
export interface DayTime {
	from: string;
	to: string;
}

export type DaySchedule = Record<Weekday, DayTime | null>;

export interface Time extends DaySchedule {
	id: UUID;
	name: string;
	created_at: IsoDateTime;
	updated_at: IsoDateTime;
}

export interface TimeCreate extends Partial<DaySchedule> {
	name: string;
}

export interface TimeUpdate extends Partial<DaySchedule> {
	name?: string;
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
	card_present: number;
	card_exam: number;
	card_attitude: number;
	total_points: number;
	created_at: IsoDateTime;
	updated_at: IsoDateTime;
}

// --- Analytics -------------------------------------------------------------
export interface AnalyticsOverview {
	records: number;
	present: number;
	absent: number;
	attendance_rate: number;
	total_points: number;
	active_students: number;
	halaqahs: number;
}

export interface LeaderboardEntry {
	rank: number;
	student_id: UUID;
	student_name: string;
	total_points: number;
	sessions: number;
	present_count: number;
}

export interface HalaqahLeaderboard {
	halaqah_id: UUID;
	halaqah_name: string;
	students: LeaderboardEntry[];
}

export interface LeaderboardResponse {
	date_from: IsoDate;
	date_to: IsoDate;
	items: HalaqahLeaderboard[];
}

export interface AtRiskStudent {
	student_id: UUID;
	student_name: string;
	halaqah_id: UUID;
	halaqah_name: string;
	sessions: number;
	absences: number;
	total_points: number;
	reasons: string[];
}

export interface AtRiskResponse {
	date_from: IsoDate;
	date_to: IsoDate;
	items: AtRiskStudent[];
}

// --- Scoring settings ------------------------------------------------------
export interface ScoringSettings {
	present_points: number;
	rating_4_points: number;
	rating_3_points: number;
	rating_2_points: number;
	rating_1_points: number;
	attitude_3_points: number;
	attitude_2_points: number;
	attitude_1_points: number;
}
