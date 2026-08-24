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
	student_type: StudentType | null;
	/** Which `ScoringPreset` prices this student's card; null = the institute-wide weights. */
	scoring_preset_id: UUID | null;
	created_at: IsoDateTime;
	updated_at: IsoDateTime;
}

/** The memorisation track a student follows — «رشيدي» students are located by
 *  مرحلة/صفحة/سطر instead of جزء/سورة/آية. */
export type StudentType = 'rashidi' | 'quran';

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
	student_type?: StudentType | null;
	scoring_preset_id?: UUID | null;
}

export type StudentUpdate = Partial<StudentCreate>;

export interface StudentImportResponse {
	created: number;
}

// --- Halaqahs --------------------------------------------------------------
/** One member of a halaqah's teaching staff. */
export interface TeacherBrief {
	id: UUID;
	name: string;
}

export interface Halaqah {
	id: UUID;
	name: string;
	level: string | null;
	age: string | null;
	/** «المعلم المسؤول» — the one name printed on the student's paper report. */
	teacher_id: UUID;
	teacher_name: string;
	/** Everyone who may teach this halaqah, responsible teacher first. Access is
	 *  decided by this membership, not by `teacher_id`. */
	teachers: TeacherBrief[];
	halaqah_type_id: UUID;
	halaqah_type_name: string;
	time_id: UUID | null;
	number_of_students: number;
	created_at: IsoDateTime;
	updated_at: IsoDateTime;
}

export interface HalaqahCreate {
	name: string;
	/** The responsible teacher; always a member regardless of `teacher_ids`. */
	teacher_id: UUID;
	/** Additional teachers who may also teach this halaqah. */
	teacher_ids?: UUID[] | null;
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

// --- Problems (الصعوبات) ---------------------------------------------------
export interface ProblemLevel {
	id: UUID;
	name: string;
	created_at: IsoDateTime;
	updated_at: IsoDateTime;
}

export interface ProblemLevelCreate {
	name: string;
}

export type ProblemLevelUpdate = Partial<ProblemLevelCreate>;

export interface Problem {
	id: UUID;
	name: string;
	level_id: UUID;
	level_name: string;
	created_at: IsoDateTime;
	updated_at: IsoDateTime;
}

export interface ProblemCreate {
	name: string;
	level_id: UUID;
}

export interface ProblemUpdate {
	name?: string;
	level_id?: UUID;
}

export interface ProblemBrief {
	id: UUID;
	name: string;
	level_id: UUID;
	level_name: string;
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

export interface DailyRecordUpdate {
	present?: boolean;
	excused?: boolean;
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

// --- Analytics -------------------------------------------------------------
/** Filters accepted by the aggregated attendance-matrix endpoint. */
export interface AttendanceMatrixParams {
	date_from?: string;
	date_to?: string;
	halaqah_id?: UUID;
	teacher_id?: UUID;
	search?: string;
	status?: 'present' | 'late' | 'absent' | 'excused';
	on_day?: string;
	sort?: 'halaqah' | 'name' | 'rate-asc' | 'rate-desc';
	limit?: number;
	offset?: number;
}

export interface AttendanceMatrixStudent {
	student_id: UUID;
	student_name: string;
	father_number: string | null;
	halaqah_id: UUID | null;
	halaqah_name: string | null;
	teacher_id: UUID | null;
	/** The responsible teacher — the table links to them. */
	teacher_name: string | null;
	/** Every teacher of the halaqah, comma-separated. */
	teacher_names: string | null;
	/** Every attended day, late ones included. */
	present: number;
	/** Subset of `present`. */
	late: number;
	absent: number;
	excused: number;
	total: number;
	rate: number;
	/** One char per day of the window: P present, A absent, E excused, '.' no record. */
	days: string;
}

export interface AttendanceMatrix {
	date_from: string;
	date_to: string;
	days: number;
	items: AttendanceMatrixStudent[];
	total: number;
	limit: number;
	offset: number;
	students: number;
	total_present: number;
	total_late: number;
	total_absent: number;
	total_excused: number;
	average_rate: number;
}

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

/** A named set of weights a student can be pinned to instead of the institute-wide
 *  settings. Same fifteen fields plus an identity — a preset is a complete pricing
 *  system, not a patch over the defaults. */
export interface ScoringPreset extends ScoringSettings {
	id: UUID;
	name: string;
}

export interface ScoringPresetWrite extends ScoringSettings {
	name: string;
}

/** The institute's own identity, printed on the monthly student report. */
export interface InstituteSettings {
	name: string;
	subtitle: string;
	phone: string;
	/** Data URI or absolute URL. Kept inline so the printed report is self-contained. */
	logo_url: string | null;
	report_footer: string;
	report_note: string;
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

export interface ParentSummonUpdate {
	status?: SummonStatus;
	admin_response?: string | null;
}

// --- الاختبار القادم --------------------------------------------------------
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
	status: 'pending' | 'done' | 'cancelled';
	status_label: string;
	summary: string;
}
