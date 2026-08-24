// In-browser demo dataset for the mock backend. Persisted to localStorage so
// records created/edited during a demo survive a page reload; `resetMockData()`
// wipes it back to the freshly-seeded state.

import { computeScores } from '$lib/labels';
import { pageFullLabel } from '$lib/quran';
import {
	RASHIDI_FIRST_PAGE,
	RASHIDI_LAST_PAGE,
	RASHIDI_LINES_PER_PAGE,
	RASHIDI_STAGES,
	rashidiFullLabel
} from '$lib/rashidi';
import type {
	Attitude,
	DailyRecord,
	Halaqah,
	ParentSummon,
	Problem,
	Rating,
	ScoringPreset,
	ScoringSettings,
	Student,
	StudentType,
	Teacher,
	UpcomingExam,
	User
} from '$lib/api/types';
import { DEMO_EMAIL } from './config';

export interface MockDb {
	version: number;
	user: User;
	teacher: Teacher;
	halaqahs: Halaqah[];
	students: Student[];
	problems: Problem[];
	records: DailyRecord[];
	summons: ParentSummon[];
	exams: UpcomingExam[];
	scoring: ScoringSettings;
	/** Named pricing systems a student can be assigned (see halaqah settings) — as if
	 *  synced read-only from the admin dashboard; this app never authors new ones. */
	scoringPresets: ScoringPreset[];
}

const STORAGE_KEY = 'mock.db.v1';
// Bumped for the student_type/scoring_preset_id/scoringPresets addition — older cached
// demo data lacks these fields, so a version bump forces a reseed instead of silently
// running with `undefined` where the new fields are expected.
const SEED_VERSION = 2;

let uidCounter = 0;
function uid(prefix: string): string {
	uidCounter += 1;
	return `${prefix}-${uidCounter}-${Math.random().toString(36).slice(2, 8)}`;
}

function daysAgo(n: number): string {
	const d = new Date();
	d.setDate(d.getDate() - n);
	return d.toISOString().slice(0, 10);
}

function pick<T>(arr: T[]): T {
	return arr[Math.floor(Math.random() * arr.length)];
}

function weighted<T>(options: { value: T; weight: number }[]): T {
	const total = options.reduce((s, o) => s + o.weight, 0);
	let r = Math.random() * total;
	for (const o of options) {
		if ((r -= o.weight) <= 0) return o.value;
	}
	return options[options.length - 1].value;
}

const DEFAULT_SCORING: ScoringSettings = {
	present_points: 5,
	rating_4_points: 7,
	rating_3_points: 5,
	rating_2_points: 3,
	rating_1_points: 0,
	revision_4_points: 7,
	revision_3_points: 5,
	revision_2_points: 3,
	revision_1_points: 0,
	attitude_3_points: 3,
	attitude_2_points: 2,
	attitude_1_points: 1,
	absent_points: 0,
	excused_points: 2,
	late_points: 3
};

/** Sample dashboard-managed pricing systems (see `MockDb.scoringPresets`). */
const SCORING_PRESETS: ScoringPreset[] = [
	{
		id: 'scoring-preset-rashidi',
		name: 'نظام رشيدي',
		...DEFAULT_SCORING,
		present_points: 4,
		rating_4_points: 6,
		rating_3_points: 4,
		rating_2_points: 2,
		revision_4_points: 6,
		revision_3_points: 4,
		revision_2_points: 2,
		excused_points: 1,
		late_points: 2
	},
	{
		id: 'scoring-preset-quran',
		name: 'نظام قرآن',
		...DEFAULT_SCORING,
		present_points: 6,
		rating_4_points: 10,
		rating_3_points: 7,
		rating_2_points: 4,
		revision_4_points: 10,
		revision_3_points: 7,
		revision_2_points: 4,
		excused_points: 3,
		late_points: 4
	}
];

const PROBLEMS: { id: string; name: string; level_id: string; level_name: string }[] = [
	{ id: 'problem-1', name: 'ضعف في مخارج الحروف', level_id: 'level-1', level_name: 'بسيطة' },
	{ id: 'problem-2', name: 'كثرة النسيان', level_id: 'level-2', level_name: 'متوسطة' },
	{ id: 'problem-3', name: 'ضعف التجويد', level_id: 'level-1', level_name: 'بسيطة' },
	{ id: 'problem-4', name: 'عدم الانتظام في الحضور', level_id: 'level-3', level_name: 'شديدة' },
	{ id: 'problem-5', name: 'بطء في الحفظ', level_id: 'level-2', level_name: 'متوسطة' }
];

const STUDENT_NAMES = [
	'أحمد خالد المطيري',
	'يوسف عبدالله الشمري',
	'إبراهيم سعود العتيبي',
	'عمر ناصر القحطاني',
	'زيد فيصل الدوسري',
	'سلمان تركي الحربي',
	'عبدالرحمن بندر الغامدي',
	'محمد وليد الزهراني',
	'خالد سعد العنزي',
	'فيصل عمار السبيعي',
	'ناصر حمد الرشيدي',
	'عبدالعزيز ماجد المالكي',
	'حمزة طلال الجهني'
];

const FATHER_NAMES = [
	'خالد المطيري',
	'عبدالله الشمري',
	'سعود العتيبي',
	'ناصر القحطاني',
	'فيصل الدوسري',
	'تركي الحربي',
	'بندر الغامدي',
	'وليد الزهراني',
	'سعد العنزي',
	'عمار السبيعي',
	'حمد الرشيدي',
	'ماجد المالكي',
	'طلال الجهني'
];

const AREAS = ['حي النسيم', 'حي الروضة', 'حي الملقا', 'حي العزيزية', 'حي السلام'];

const NOTE_SAMPLES = [
	'يحتاج إلى متابعة أكثر في المنزل',
	'تحسّن ملحوظ هذا الأسبوع',
	'تأخر في الحضور مرتين',
	'أداء ممتاز، يستحق تشجيعاً',
	null,
	null
];

/** Where a student's memorization has reached — advances a page or two on every
 *  present day, so their history reads as real progress through the mushaf (1..604)
 *  instead of unrelated random numbers each day. */
interface PageCursor {
	current: number;
}

function buildRecordFor(
	student: Student,
	teacherId: string,
	date: string,
	scoring: ScoringSettings,
	cursor: PageCursor
): DailyRecord | null {
	// ~18% of days have no record at all — attendance not yet taken that session.
	if (Math.random() < 0.18) return null;

	const present = weighted([
		{ value: true, weight: 82 },
		{ value: false, weight: 18 }
	]);
	const excused = !present && Math.random() < 0.5;
	const late = present && Math.random() < 0.12;

	const rating = present
		? weighted<Rating>([
				{ value: 4, weight: 35 },
				{ value: 3, weight: 35 },
				{ value: 2, weight: 20 },
				{ value: 1, weight: 10 }
			])
		: null;
	const hasRevision = present && Math.random() < 0.6;
	const revisionRating = hasRevision
		? weighted<Rating>([
				{ value: 4, weight: 40 },
				{ value: 3, weight: 30 },
				{ value: 2, weight: 20 },
				{ value: 1, weight: 10 }
			])
		: null;
	const revisionSuccess = (revisionRating ?? 0) >= 3;
	const revisionLesson = !hasRevision
		? null
		: student.student_type === 'rashidi'
			? `المرحلة ${1 + Math.floor(Math.random() * RASHIDI_STAGES.length)}: ${revisionSuccess ? 'نجح' : 'أخفق'}`
			: `الجزء ${1 + Math.floor(Math.random() * 30)} (كله): ${revisionSuccess ? 'نجح' : 'أخفق'}`;

	// A real page range: starts where the student last left off, and advances by
	// however much they recited today — so «آخر موضع» reflects genuine forward
	// progress rather than a fresh random spot every day. Rashidi students walk the
	// 48-page primer instead of the 604-page mushaf, plus a random line per page.
	const isRashidi = student.student_type === 'rashidi';
	const maxPage = isRashidi ? RASHIDI_LAST_PAGE : 604;
	const minPage = isRashidi ? RASHIDI_FIRST_PAGE : 1;
	let examFrom: number | null = null;
	let examTo: number | null = null;
	let examFromLine: number | null = null;
	let examToLine: number | null = null;
	let examTotal: number | null = null;
	if (present) {
		const pagesToday = weighted([
			{ value: 1, weight: 55 },
			{ value: 2, weight: 30 },
			{ value: 3, weight: 15 }
		]);
		examFrom = cursor.current;
		examTo = Math.min(maxPage, cursor.current + pagesToday - 1);
		examTotal = examTo - examFrom + 1;
		cursor.current = examTo >= maxPage ? minPage : examTo + 1; // wrap around at the end
		if (isRashidi) {
			examFromLine = 1 + Math.floor(Math.random() * RASHIDI_LINES_PER_PAGE);
			examToLine = 1 + Math.floor(Math.random() * RASHIDI_LINES_PER_PAGE);
		}
	}

	const attitude = present
		? weighted<Attitude>([
				{ value: 3, weight: 60 },
				{ value: 2, weight: 30 },
				{ value: 1, weight: 10 }
			])
		: null;

	const addedPoints = weighted([
		{ value: 0, weight: 80 },
		{ value: 5, weight: 10 },
		{ value: 10, weight: 5 },
		{ value: -5, weight: 5 }
	]);

	// Same «صفحة تالية لـ إلى» rule the real app uses (see autoFillHomework), so demo data
	// reads with the exact من/إلى/وظيفة format instead of unrelated free-text samples.
	const homework = !present
		? null
		: isRashidi
			? rashidiFullLabel(cursor.current, 1 + Math.floor(Math.random() * RASHIDI_LINES_PER_PAGE))
			: pageFullLabel(cursor.current);
	const notes = Math.random() < 0.2 ? pick(NOTE_SAMPLES) : null;
	const tagged =
		rating != null && rating <= 2 && Math.random() < 0.5
			? [pick(PROBLEMS)].map((p) => ({
					id: p.id,
					name: p.name,
					level_id: p.level_id,
					level_name: p.level_name
				}))
			: [];

	const scores = computeScores(
		{
			present,
			excused,
			late,
			rating,
			revision_rating: revisionRating,
			attitude,
			added_points: addedPoints
		},
		scoring
	);

	const now = new Date().toISOString();
	return {
		id: uid('record'),
		student_id: student.id,
		teacher_id: teacherId,
		halaqah_id: student.halaqah_id ?? '',
		record_date: date,
		present,
		excused,
		late,
		excuse_reason: excused ? 'إذن ولي الأمر' : null,
		exam_from: examFrom,
		exam_to: examTo,
		exam_from_line: examFromLine,
		exam_to_line: examToLine,
		exam_total: examTotal,
		homework,
		problems: tagged.length ? tagged[0].name : null,
		rating,
		revision_lesson: revisionLesson,
		revision_rating: revisionRating,
		attitude,
		added_points: addedPoints,
		notes,
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

export function seedDb(): MockDb {
	uidCounter = 0;
	const now = new Date().toISOString();

	const userId = 'user-teacher-1';
	const teacherId = 'teacher-1';

	const user: User = {
		id: userId,
		full_name: 'الشيخ عبدالرحمن السالم',
		email: DEMO_EMAIL,
		role: 'teacher',
		date_of_birth: '1988-04-12',
		is_active: true,
		created_at: now,
		updated_at: now
	};

	const teacher: Teacher = {
		id: teacherId,
		user_id: userId,
		full_name: user.full_name,
		email: user.email,
		date_of_birth: user.date_of_birth,
		is_active: true,
		academic_study: 'بكالوريوس شريعة إسلامية',
		islamic_study: 'إجازة في القراءات العشر',
		is_assistant: false,
		created_at: now,
		updated_at: now
	};

	const halaqahs: Halaqah[] = [
		{
			id: 'halaqah-1',
			name: 'حلقة الفرقان',
			level: 'متوسط',
			age: '9-12 سنة',
			teacher_id: teacherId,
			teacher_name: teacher.full_name,
			teachers: [{ id: teacherId, name: teacher.full_name }],
			halaqah_type_id: 'type-hifz',
			halaqah_type_name: 'حفظ',
			time_id: 'time-asr',
			time_name: 'بعد العصر',
			schedule: {
				saturday: { from: '16:00', to: '17:30' },
				monday: { from: '16:00', to: '17:30' },
				wednesday: { from: '16:00', to: '17:30' }
			},
			number_of_students: 0,
			created_at: now,
			updated_at: now
		},
		{
			id: 'halaqah-2',
			name: 'حلقة النور',
			level: 'مبتدئ',
			age: '7-9 سنوات',
			teacher_id: teacherId,
			teacher_name: teacher.full_name,
			teachers: [{ id: teacherId, name: teacher.full_name }],
			halaqah_type_id: 'type-tahfeez',
			halaqah_type_name: 'تحفيظ',
			time_id: 'time-maghrib',
			time_name: 'بعد المغرب',
			schedule: {
				sunday: { from: '18:30', to: '19:30' },
				tuesday: { from: '18:30', to: '19:30' },
				thursday: { from: '18:30', to: '19:30' }
			},
			number_of_students: 0,
			created_at: now,
			updated_at: now
		}
	];

	const students: Student[] = STUDENT_NAMES.map((name, i) => {
		const halaqah = halaqahs[i % 2];
		const birthYear = 2013 + (i % 6);
		const birthMonth = String(1 + (i % 12)).padStart(2, '0');
		const birthDay = String(10 + (i % 15)).padStart(2, '0');
		return {
			id: `student-${i + 1}`,
			full_name: name,
			father_name: FATHER_NAMES[i],
			father_number: `05${String(10000000 + i * 137).padStart(8, '0')}`,
			date_of_birth: `${birthYear}-${birthMonth}-${birthDay}`,
			mother_number: i % 3 === 0 ? `05${String(20000000 + i * 91).padStart(8, '0')}` : null,
			orphan_of: i === 4 ? 'father' : null,
			residential_area: pick(AREAS),
			accepted_at: daysAgo(120 + i * 5),
			notes: null,
			halaqah_id: halaqah.id,
			student_type: (i % 2 === 0 ? 'quran' : 'rashidi') as StudentType,
			scoring_preset_id:
				i % 3 === 0 ? (i % 2 === 0 ? 'scoring-preset-quran' : 'scoring-preset-rashidi') : null,
			created_at: now,
			updated_at: now
		};
	});

	for (const h of halaqahs) {
		h.number_of_students = students.filter((s) => s.halaqah_id === h.id).length;
	}

	const problems: Problem[] = PROBLEMS.map((p) => ({ ...p, created_at: now, updated_at: now }));

	function halaqahName(id: string | null): string {
		return halaqahs.find((h) => h.id === id)?.name ?? '';
	}

	const records: DailyRecord[] = [];
	for (let i = 0; i < students.length; i++) {
		const student = students[i];
		// Each student is somewhere different in their curriculum (mushaf or, for
		// رشيدي, the 48-page primer); walk the 14 days oldest→newest so the cursor
		// advances forward like real progress instead of jumping around.
		const cursor: PageCursor = {
			current:
				student.student_type === 'rashidi'
					? RASHIDI_FIRST_PAGE + (i % (RASHIDI_LAST_PAGE - RASHIDI_FIRST_PAGE + 1))
					: 1 + ((i * 41) % 560)
		};
		for (let d = 14; d >= 1; d--) {
			const rec = buildRecordFor(student, teacherId, daysAgo(d), DEFAULT_SCORING, cursor);
			if (rec) records.push(rec);
		}
	}

	const summons: ParentSummon[] = [
		{
			id: uid('summon'),
			student_id: students[2].id,
			student_name: students[2].full_name,
			father_name: students[2].father_name,
			father_number: students[2].father_number,
			teacher_id: teacherId,
			teacher_name: teacher.full_name,
			halaqah_id: students[2].halaqah_id ?? '',
			halaqah_name: halaqahName(students[2].halaqah_id),
			reason: 'تكرار الغياب دون عذر خلال الأسبوعين الماضيين',
			status: 'new',
			status_label: 'جديد',
			admin_response: null,
			handled_at: null,
			created_at: daysAgo(1),
			updated_at: daysAgo(1)
		},
		{
			id: uid('summon'),
			student_id: students[5].id,
			student_name: students[5].full_name,
			father_name: students[5].father_name,
			father_number: students[5].father_number,
			teacher_id: teacherId,
			teacher_name: teacher.full_name,
			halaqah_id: students[5].halaqah_id ?? '',
			halaqah_name: halaqahName(students[5].halaqah_id),
			reason: 'ضعف واضح في الحفظ يحتاج متابعة الأسرة',
			status: 'reviewing',
			status_label: 'قيد المراجعة',
			admin_response: null,
			handled_at: null,
			created_at: daysAgo(3),
			updated_at: daysAgo(2)
		},
		{
			id: uid('summon'),
			student_id: students[8].id,
			student_name: students[8].full_name,
			father_name: students[8].father_name,
			father_number: students[8].father_number,
			teacher_id: teacherId,
			teacher_name: teacher.full_name,
			halaqah_id: students[8].halaqah_id ?? '',
			halaqah_name: halaqahName(students[8].halaqah_id),
			reason: 'سلوك غير منضبط داخل الحلقة',
			status: 'completed',
			status_label: 'مكتمل',
			admin_response: 'تم التواصل مع ولي الأمر وتعهد بالمتابعة',
			handled_at: daysAgo(1),
			created_at: daysAgo(6),
			updated_at: daysAgo(1)
		}
	];

	const exams: UpcomingExam[] = [
		{
			id: uid('exam'),
			student_id: students[0].id,
			student_name: students[0].full_name,
			teacher_id: teacherId,
			teacher_name: teacher.full_name,
			halaqah_id: students[0].halaqah_id ?? '',
			halaqah_name: halaqahName(students[0].halaqah_id),
			scheduled_date: daysAgo(-3),
			part: 5,
			exam_from: 1,
			exam_to: 10,
			notes: 'اختبار ربع الجزء',
			status: 'pending',
			status_label: 'قيد الانتظار',
			summary: 'الجزء 5 · من 1 إلى 10'
		},
		{
			id: uid('exam'),
			student_id: students[3].id,
			student_name: students[3].full_name,
			teacher_id: teacherId,
			teacher_name: teacher.full_name,
			halaqah_id: students[3].halaqah_id ?? '',
			halaqah_name: halaqahName(students[3].halaqah_id),
			scheduled_date: daysAgo(-1),
			part: 12,
			exam_from: 1,
			exam_to: 20,
			notes: null,
			status: 'pending',
			status_label: 'قيد الانتظار',
			summary: 'الجزء 12 · من 1 إلى 20'
		},
		{
			id: uid('exam'),
			student_id: students[7].id,
			student_name: students[7].full_name,
			teacher_id: teacherId,
			teacher_name: teacher.full_name,
			halaqah_id: students[7].halaqah_id ?? '',
			halaqah_name: halaqahName(students[7].halaqah_id),
			scheduled_date: daysAgo(2),
			part: 3,
			exam_from: 1,
			exam_to: 15,
			notes: null,
			status: 'done',
			status_label: 'تم',
			summary: 'الجزء 3 · من 1 إلى 15'
		}
	];

	return {
		version: SEED_VERSION,
		user,
		teacher,
		halaqahs,
		students,
		problems,
		records,
		summons,
		exams,
		scoring: DEFAULT_SCORING,
		scoringPresets: SCORING_PRESETS
	};
}

let cached: MockDb | null = null;

export function loadDb(): MockDb {
	if (cached) return cached;
	if (typeof localStorage !== 'undefined') {
		try {
			const raw = localStorage.getItem(STORAGE_KEY);
			if (raw) {
				const parsed = JSON.parse(raw) as MockDb;
				if (parsed.version === SEED_VERSION) {
					cached = parsed;
					return cached;
				}
			}
		} catch {
			/* corrupted cache — fall through to reseed */
		}
	}
	cached = seedDb();
	persist();
	return cached;
}

export function saveDb(db: MockDb): void {
	cached = db;
	persist();
}

export function resetMockData(): void {
	cached = seedDb();
	persist();
}

function persist(): void {
	if (typeof localStorage === 'undefined' || !cached) return;
	try {
		localStorage.setItem(STORAGE_KEY, JSON.stringify(cached));
	} catch {
		/* storage unavailable — demo data just stays in-memory for this session */
	}
}
