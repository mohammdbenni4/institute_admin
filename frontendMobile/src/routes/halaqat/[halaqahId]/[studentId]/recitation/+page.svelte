<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import {
		errorMessage,
		auth,
		type Attitude,
		type DailyRecord,
		type Halaqah,
		type Problem,
		type Rating,
		type ScoringSettings,
		type Student
	} from '$lib/api';
	import { net, repo } from '$lib/offline';
	import {
		ADDED_POINTS_OPTIONS,
		ATTITUDE_OPTIONS,
		HALF_OPTIONS,
		QURAN_PARTS,
		RATING_OPTIONS,
		computeScores,
		parseRashidiRevisions,
		parseRevisions,
		ratingLabel,
		serializeRashidiRevisions,
		serializeRevisions,
		type RashidiRevisionRow,
		type RevisionRow
	} from '$lib/labels';
	import {
		cn,
		formatDateArabic,
		formatDateShort,
		nextSessionDate,
		todayIso,
		toLatinDigits
	} from '$lib/utils';
	import TopBar from '$lib/components/TopBar.svelte';
	import Spinner from '$lib/components/Spinner.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import Field from '$lib/components/Field.svelte';
	import PillGroup from '$lib/components/PillGroup.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import Loader from '$lib/components/Loader.svelte';
	import SummonSheet from '$lib/components/SummonSheet.svelte';
	import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';
	import Dropdown from '$lib/components/Dropdown.svelte';
	import { upcomingExamsApi, type UpcomingExam } from '$lib/api';
	import {
		ayahsInJuz,
		juzsForSurah,
		pageForAyah,
		pagesForJuz,
		pagesForSurah,
		pageRef,
		pageFullLabel,
		SURAHS,
		surahsForJuz
	} from '$lib/quran';
	import {
		RASHIDI_FIRST_PAGE,
		RASHIDI_LAST_PAGE,
		RASHIDI_LINES_PER_PAGE,
		RASHIDI_STAGES,
		rashidiFullLabel,
		rashidiPagesForStage,
		rashidiStageForPage
	} from '$lib/rashidi';

	/** Every mushaf page / juz / surah, for the dropdowns. */
	const PAGES = Array.from({ length: 604 }, (_, i) => i + 1);
	const JUZ_NUMBERS = Array.from({ length: 30 }, (_, i) => i + 1);
	const SURAH_OPTIONS = SURAHS.map((s) => ({ value: s.number, label: s.name }));
	const QURAN_PART_OPTIONS = QURAN_PARTS.map((p) => ({ value: p, label: `الجزء ${p}` }));
	const toOptions = (values: number[]) => values.map((v) => ({ value: v, label: String(v) }));
	/** `form.exam_from`/`exam_to` are strings, so their dropdown options must be too —
	 *  otherwise picking one would assign a number into a field the rest of the form
	 *  (`.trim()`, `wholeOrNull`) treats as a string. */
	const toPageOptions = (values: number[]) =>
		values.map((v) => ({ value: String(v), label: String(v) }));

	const halaqahId = $derived($page.params.halaqahId ?? '');
	const studentId = $derived($page.params.studentId ?? '');
	const date = $derived($page.url.searchParams.get('date') || todayIso());

	let status = $state<'loading' | 'ready' | 'error'>('loading');
	let error = $state('');
	let student = $state<Student | null>(null);
	let halaqah = $state<Halaqah | null>(null);
	let settings = $state<ScoringSettings | null>(null);
	let record = $state<DailyRecord | null>(null);
	let allProblems = $state<Problem[]>([]);
	/** رشيدي: صفحة/مرحلة/سطر بدل جزء/سورة/آية/صفحة (انظر بطاقة التسميع أدناه). */
	const isRashidi = $derived(student?.student_type === 'rashidi');
	// The student's most recent exam and the homework they were told to prepare.
	let prevRecitation = $state<DailyRecord | null>(null);
	let requiredHomework = $state<string | null>(null);

	// Notes / difficulties start collapsed: most sessions never touch them, and
	// keeping them open made this screen far longer than a phone can show.
	let extrasOpen = $state(false);

	// «استدعاء ولي الأمر»
	let summonOpen = $state(false);

	// حذف سجل اليوم (الحضور والتسميع معاً)
	let deleteOpen = $state(false);
	let deleting = $state(false);

	// «الاختبار القادم» — the exam this student is working towards. Folded below the
	// difficulties section unless one is already scheduled.
	let nextExam = $state<UpcomingExam | null>(null);
	let examSectionOpen = $state(false);
	let examOpen = $state(false);
	let examSaving = $state(false);
	let examForm = $state({ scheduled_date: '', part: '', exam_from: '', exam_to: '', notes: '' });

	/** The halaqah's next scheduled session after the day being recorded. */
	const nextSession = $derived(nextSessionDate(halaqah?.schedule, date));

	let form = $state({
		exam_from: '',
		exam_to: '',
		exam_total: '',
		rating: null as number | null,
		revision_rating: null as number | null,
		homework: '',
		// Default a new record to «متوسط» rather than leaving الأدب unset.
		attitude: 2 as number | null,
		added_points: 0 as number | null,
		notes: '',
		problems: '',
		problem_ids: [] as string[]
	});
	let revisions = $state<RevisionRow[]>([]);
	/** رشيدي: مراحل (١-٦) بدل أجزاء، بلا نصف — انظر بطاقة المراجعة أدناه. */
	let rashidiRevisions = $state<RashidiRevisionRow[]>([]);

	// ===== Smart التسميع pickers: سورة/جزء/آية/صفحة kept in sync both ways =====
	type Side = 'from' | 'to' | 'hw';
	let fromSurah = $state<number | ''>('');
	let fromJuz = $state<number | ''>('');
	let fromAyah = $state<number | ''>('');
	let toSurah = $state<number | ''>('');
	let toJuz = $state<number | ''>('');
	let toAyah = $state<number | ''>('');
	// «وظيفة» — the next assignment, picked the same way as من/إلى (not free text).
	let hwSurah = $state<number | ''>('');
	let hwJuz = $state<number | ''>('');
	let hwAyah = $state<number | ''>('');
	let hwPage = $state('');

	// ===== رشيدي pickers: صفحة/مرحلة/سطر بدل جزء/سورة/آية/صفحة =====
	const RASHIDI_STAGE_OPTIONS = RASHIDI_STAGES.map((s) => ({ value: s.number, label: s.name }));
	const RASHIDI_LINE_OPTIONS = toOptions(
		Array.from({ length: RASHIDI_LINES_PER_PAGE }, (_, i) => i + 1)
	);
	/** Page choices for a رشيدي side: the whole primer (5..48), or just the picked stage's pages. */
	function rashidiPageOptions(stage: number | ''): number[] {
		if (stage === '') {
			return Array.from(
				{ length: RASHIDI_LAST_PAGE - RASHIDI_FIRST_PAGE + 1 },
				(_, i) => RASHIDI_FIRST_PAGE + i
			);
		}
		const s = RASHIDI_STAGES.find((x) => x.number === stage);
		return s ? rashidiPagesForStage(s) : [];
	}
	let fromStage = $state<number | ''>('');
	let fromLine = $state<number | ''>('');
	let toStage = $state<number | ''>('');
	let toLine = $state<number | ''>('');
	let hwStage = $state<number | ''>('');
	let hwLine = $state<number | ''>('');

	/** Surah choices for a side: 1..114, or just the surahs the picked juz touches. */
	function surahOptions(juz: number | ''): { value: number; label: string }[] {
		if (juz === '') return SURAH_OPTIONS;
		return surahsForJuz(juz).map((s) => ({ value: s.number, label: s.name }));
	}

	/** Ayah choices for a side: 1..ayahCount for the picked surah, narrowed further to
	 *  just the picked juz's slice of it when one is also set. */
	function ayahOptions(surahNumber: number | '', juz: number | ''): number[] {
		if (surahNumber === '') return [];
		const s = SURAHS[surahNumber - 1];
		if (!s) return [];
		if (juz === '') return Array.from({ length: s.ayahCount }, (_, i) => i + 1);
		const inJuz = ayahsInJuz(s, juz);
		return inJuz.length ? inJuz : Array.from({ length: s.ayahCount }, (_, i) => i + 1);
	}

	/** Page choices for a side: narrowed by whichever of surah/juz is already picked
	 *  (intersected if both are), or the whole mushaf if neither is. */
	function pageOptions(surahNumber: number | '', juz: number | ''): number[] {
		let opts = PAGES;
		if (surahNumber !== '') {
			const s = SURAHS[surahNumber - 1];
			if (s) opts = pagesForSurah(s);
		}
		if (juz !== '') {
			const juzPages = new Set(pagesForJuz(juz));
			const narrowed = opts.filter((p) => juzPages.has(p));
			if (narrowed.length) opts = narrowed;
		}
		return opts;
	}

	/** Juz choices for a side: 1..30, or just the juz range the picked surah spans. */
	function juzOptions(surahNumber: number | ''): number[] {
		if (surahNumber === '') return JUZ_NUMBERS;
		const s = SURAHS[surahNumber - 1];
		return s ? juzsForSurah(s) : JUZ_NUMBERS;
	}

	/** A new surah defaults to its first ayah (page/juz follow), so picking a surah alone
	 *  is already a complete, usable selection — not just a filter waiting on an ayah. */
	function onSurahPicked(side: Side): void {
		const value = side === 'from' ? fromSurah : side === 'to' ? toSurah : hwSurah;
		if (side === 'from') fromAyah = value === '' ? '' : 1;
		else if (side === 'to') toAyah = value === '' ? '' : 1;
		else hwAyah = value === '' ? '' : 1;
		if (value === '') {
			if (side === 'from') {
				fromJuz = '';
				form.exam_from = '';
			} else if (side === 'to') {
				toJuz = '';
				form.exam_to = '';
			} else {
				hwJuz = '';
				hwPage = '';
				form.homework = '';
			}
		} else {
			syncPageFromAyah(side);
		}
	}

	/** True once the teacher edits المجموع by hand, which freezes the auto-computation.
	 *  Recitation is often half or a quarter of a page, so the inclusive page count
	 *  derived from «من»/«إلى» is a starting point, not the answer. */
	let totalTouched = $state(false);

	/** المجموع as implied by the range: an inclusive page count, or '' when incomplete. */
	function autoTotal(): string {
		const from = Number(form.exam_from);
		const to = Number(form.exam_to);
		if (
			form.exam_from &&
			form.exam_to &&
			Number.isFinite(from) &&
			Number.isFinite(to) &&
			to >= from
		) {
			return String(to - from + 1);
		}
		return '';
	}

	/** Refresh المجموع from the range — unless the teacher has overridden it. */
	function recomputeTotal(): void {
		if (totalTouched) return;
		form.exam_total = autoTotal();
	}

	/** Nudge المجموع by half a page, clamped at zero. Starts from the auto value so the
	 *  first tap on «−» after picking a single page lands on «0.5» — نصف صفحة. */
	function stepTotal(delta: number): void {
		const base = Number(form.exam_total || autoTotal() || 0);
		const next = Math.max(0, Math.round((base + delta) * 100) / 100);
		form.exam_total = next === 0 ? '' : String(next);
		totalTouched = true;
	}

	/** Hand المجموع back to the automatic count. */
	function resetTotalToAuto(): void {
		totalTouched = false;
		form.exam_total = autoTotal();
	}

	/** جزء/صفحة/آية (أو مرحلة/صفحة/سطر لطلاب رشيدي) لصفحة معيّنة، أو «—» إن لم توجد. */
	function examPageLabel(page: number | null | undefined, line?: number | null): string {
		if (page == null) return '—';
		if (isRashidi) return rashidiFullLabel(page, line ?? null) ?? `صفحة ${page}`;
		return pageFullLabel(page) ?? `صفحة ${page}`;
	}

	/** «إلى» defaults to the same page as «من» — a single page is the default recitation
	 *  length; the teacher stretches the range manually when it's more than that. */
	function autoFillTo(fromPage: number): void {
		const ref = pageRef(fromPage);
		if (!ref) return;
		form.exam_to = String(ref.page);
		toSurah = ref.surah.number;
		toAyah = ref.ayah;
		toJuz = ref.juz;
		recomputeTotal();
		autoFillHomework(ref.page);
	}

	/** «وظيفة» defaults to one page past «إلى» — the natural next assignment — until the
	 *  teacher picks a different one directly from its own جزء/سورة/آية/صفحة row. */
	function autoFillHomework(toPage: number): void {
		const ref = pageRef(toPage + 1);
		if (!ref) {
			hwSurah = '';
			hwJuz = '';
			hwAyah = '';
			hwPage = '';
			form.homework = '';
			return;
		}
		hwPage = String(ref.page);
		hwSurah = ref.surah.number;
		hwAyah = ref.ayah;
		hwJuz = ref.juz;
		form.homework = pageFullLabel(ref.page) ?? `صفحة ${ref.page}`;
	}

	/** Resolve the page + juz from a picked surah/ayah pair (من/إلى/وظيفة). */
	function syncPageFromAyah(side: Side): void {
		const surah = side === 'from' ? fromSurah : side === 'to' ? toSurah : hwSurah;
		const ayah = side === 'from' ? fromAyah : side === 'to' ? toAyah : hwAyah;
		if (surah === '' || ayah === '') return;
		const res = pageForAyah(surah, ayah);
		if (!res) return;
		if (side === 'from') {
			form.exam_from = String(res.page);
			fromJuz = res.juz;
			autoFillTo(res.page);
		} else if (side === 'to') {
			form.exam_to = String(res.page);
			toJuz = res.juz;
			recomputeTotal();
			autoFillHomework(res.page);
		} else {
			hwPage = String(res.page);
			hwJuz = res.juz;
			form.homework = pageFullLabel(res.page) ?? `صفحة ${res.page}`;
		}
	}

	/** Resolve surah/ayah/juz from a directly-picked page (من/إلى/وظيفة). */
	function syncAyahFromPage(side: Side): void {
		const raw = side === 'from' ? form.exam_from : side === 'to' ? form.exam_to : hwPage;
		const ref = raw.trim() ? pageRef(Number(raw)) : null;
		if (side === 'from') {
			fromSurah = ref?.surah.number ?? '';
			fromAyah = ref?.ayah ?? '';
			fromJuz = ref?.juz ?? '';
			if (ref) autoFillTo(ref.page);
		} else if (side === 'to') {
			toSurah = ref?.surah.number ?? '';
			toAyah = ref?.ayah ?? '';
			toJuz = ref?.juz ?? '';
			recomputeTotal();
			if (ref) autoFillHomework(ref.page);
		} else {
			hwSurah = ref?.surah.number ?? '';
			hwAyah = ref?.ayah ?? '';
			hwJuz = ref?.juz ?? '';
			form.homework = ref ? (pageFullLabel(ref.page) ?? `صفحة ${ref.page}`) : '';
		}
	}

	/** Picking a juz alone (no surah yet) is still a complete-enough selection to fill the
	 *  rest of the row: keep the current surah if it still fits the new juz, otherwise fall
	 *  back to the juz's first surah, then default to that surah's first ayah within the
	 *  juz (via `syncPageFromAyah`, which also fills the page and cascades إلى/الوظيفة). */
	function syncFromJuz(side: Side): void {
		const juz = side === 'from' ? fromJuz : side === 'to' ? toJuz : hwJuz;
		if (juz === '') return;
		const surahNumber = side === 'from' ? fromSurah : side === 'to' ? toSurah : hwSurah;
		const currentSurah = surahNumber === '' ? null : SURAHS[surahNumber - 1];
		const surahStillValid = !!currentSurah && juzsForSurah(currentSurah).includes(juz);
		const surah = surahStillValid ? currentSurah : (surahsForJuz(juz)[0] ?? null);
		const ayah = surah ? (ayahsInJuz(surah, juz)[0] ?? 1) : '';
		if (side === 'from') {
			fromSurah = surah ? surah.number : '';
			fromAyah = ayah;
		} else if (side === 'to') {
			toSurah = surah ? surah.number : '';
			toAyah = ayah;
		} else {
			hwSurah = surah ? surah.number : '';
			hwAyah = ayah;
		}
		if (surah) {
			syncPageFromAyah(side);
		} else if (side === 'from') {
			form.exam_from = '';
			recomputeTotal();
		} else if (side === 'to') {
			form.exam_to = '';
			recomputeTotal();
		} else {
			hwPage = '';
			form.homework = '';
		}
	}

	/** «إلى» defaults to the same صفحة (ونفس السطر) as «من» — same «صفحة واحدة» default
	 *  philosophy as the قرآن model, just with رشيدي's مرحلة/صفحة/سطر shape. */
	function autoFillToRashidi(fromPage: number): void {
		const stage = rashidiStageForPage(fromPage);
		if (!stage) return;
		form.exam_to = String(fromPage);
		toStage = stage.number;
		toLine = fromLine === '' ? 1 : fromLine;
		recomputeTotal();
		autoFillHomeworkRashidi(fromPage);
	}

	/** «وظيفة» defaults to one صفحة past «إلى»، سطر 1. */
	function autoFillHomeworkRashidi(toPage: number): void {
		const stage = rashidiStageForPage(toPage + 1);
		if (!stage) {
			hwStage = '';
			hwPage = '';
			hwLine = '';
			form.homework = '';
			return;
		}
		hwPage = String(toPage + 1);
		hwStage = stage.number;
		hwLine = 1;
		form.homework = rashidiFullLabel(toPage + 1, 1) ?? `صفحة ${toPage + 1}`;
	}

	/** Resolve the مرحلة from a directly-picked صفحة (من/إلى/وظيفة). */
	function syncStageFromPageRashidi(side: Side): void {
		const raw = side === 'from' ? form.exam_from : side === 'to' ? form.exam_to : hwPage;
		const page = raw.trim() ? Number(raw) : null;
		const stage = page != null ? rashidiStageForPage(page) : null;
		if (side === 'from') {
			fromStage = stage?.number ?? '';
			if (page != null && stage) autoFillToRashidi(page);
		} else if (side === 'to') {
			toStage = stage?.number ?? '';
			recomputeTotal();
			if (page != null && stage) autoFillHomeworkRashidi(page);
		} else {
			hwStage = stage?.number ?? '';
			form.homework = page != null && stage ? (rashidiFullLabel(page, hwLine || null) ?? '') : '';
		}
	}

	/** A مرحلة is a broad filter, not a specific point — narrows الصفحة's options and,
	 *  once picked alone, defaults to that stage's first صفحة (mirrors الجزء's behaviour). */
	function syncPageFromStageRashidi(side: Side): void {
		const stageNumber = side === 'from' ? fromStage : side === 'to' ? toStage : hwStage;
		if (stageNumber === '') return;
		const stage = RASHIDI_STAGES.find((s) => s.number === stageNumber);
		if (!stage) return;
		const page = stage.firstPage;
		if (side === 'from') {
			form.exam_from = String(page);
			fromLine = 1;
			autoFillToRashidi(page);
		} else if (side === 'to') {
			form.exam_to = String(page);
			toLine = 1;
			recomputeTotal();
			autoFillHomeworkRashidi(page);
		} else {
			hwPage = String(page);
			hwLine = 1;
			form.homework = rashidiFullLabel(page, 1) ?? '';
		}
	}

	/** Restore fromStage/toStage from an already-saved صفحة when opening an existing
	 *  record — unlike `syncStageFromPageRashidi`, never cascades to autoFill «إلى»/
	 *  «وظيفة», since both sides already hold their own true saved values at load time. */
	function deriveRashidiStage(side: 'from' | 'to', page: string): void {
		const stage = page.trim() ? rashidiStageForPage(Number(page)) : null;
		if (side === 'from') fromStage = stage?.number ?? '';
		else toStage = stage?.number ?? '';
	}

	/** Clear the whole التسميع card — من/إلى/وظيفة pickers, المجموع, and التقدير. */
	function resetTasmee(): void {
		fromSurah = '';
		fromJuz = '';
		fromAyah = '';
		hwSurah = '';
		hwJuz = '';
		hwAyah = '';
		hwPage = '';
		form.homework = '';
		toSurah = '';
		toJuz = '';
		toAyah = '';
		fromStage = '';
		fromLine = '';
		toStage = '';
		toLine = '';
		hwStage = '';
		hwLine = '';
		form.exam_from = '';
		form.exam_to = '';
		form.exam_total = '';
		totalTouched = false;
		form.rating = null;
	}

	/** «من» = the last page the student reached last time (their previous recitation's
	 *  «إلى», or «من» if that's all that was recorded) — «إلى» follows automatically. */
	function fillLastPosition(): void {
		const page = prevRecitation?.exam_to ?? prevRecitation?.exam_from;
		if (page == null) return;
		form.exam_from = String(page);
		if (isRashidi) syncStageFromPageRashidi('from');
		else syncAyahFromPage('from');
	}

	let saving = $state(false);
	let feedback = $state<{ type: 'ok' | 'err'; text: string } | null>(null);
	let feedbackTimer: ReturnType<typeof setTimeout> | undefined;

	const problemsByLevel = $derived.by(() => {
		const map = new Map<string, { levelName: string; items: Problem[] }>();
		for (const p of allProblems) {
			const ex = map.get(p.level_id);
			if (ex) ex.items.push(p);
			else map.set(p.level_id, { levelName: p.level_name, items: [p] });
		}
		return [...map.values()];
	});

	const scores = $derived(
		computeScores(
			{
				present: record?.present ?? true,
				excused: record?.excused ?? false,
				late: record?.late ?? false,
				rating: form.rating,
				revision_rating: form.revision_rating,
				attitude: form.attitude,
				added_points: form.added_points ?? 0
			},
			settings
		)
	);

	/** How many difficulty tags are picked (shown on the collapsible's toggle). */
	const extrasCount = $derived(form.problem_ids.length);

	onMount(load);

	async function load() {
		if (!auth.teacher) return;
		status = 'loading';
		try {
			const [s, h, rec, scoring, presets, probs, latest] = await Promise.all([
				repo.getStudent(studentId),
				repo.getHalaqah(halaqahId),
				repo.getDayRecord(studentId, date),
				repo.getScoring(),
				repo.listScoringPresets(),
				repo.listProblems(),
				// No date window: a student's last recitation must show even after a
				// long absence (the old three-month lookback hid it).
				repo.latestRecitations([studentId], date)
			]);
			student = s;
			halaqah = h;
			// This student's assigned pricing preset (see halaqah settings), or the
			// halaqah's single default — matches how the mock server prices the same record.
			settings =
				(s.scoring_preset_id && presets.find((p) => p.id === s.scoring_preset_id)) || scoring;
			allProblems = probs;
			record = rec;

			const previous = latest.get(studentId);
			prevRecitation = previous?.record ?? null;
			requiredHomework = previous?.homework ?? null;
			void loadNextExam();

			if (record) {
				form = {
					exam_from: record.exam_from?.toString() ?? '',
					exam_to: record.exam_to?.toString() ?? '',
					exam_total: record.exam_total?.toString() ?? '',
					rating: record.rating,
					revision_rating: record.revision_rating,
					homework: record.homework ?? '',
					attitude: record.attitude,
					added_points: record.added_points,
					notes: record.notes ?? '',
					problems: record.problems ?? '',
					problem_ids: record.tagged_problems.map((p) => p.id)
				};
				if (s.student_type === 'rashidi') {
					rashidiRevisions = parseRashidiRevisions(record.revision_lesson);
				} else {
					revisions = parseRevisions(record.revision_lesson);
				}
				extrasOpen = record.tagged_problems.length > 0;
				fromLine = record.exam_from_line ?? '';
				toLine = record.exam_to_line ?? '';
				// A saved total that doesn't match the range was typed by hand (a half page,
				// most often) — keep it frozen so re-opening the record doesn't round it up.
				totalTouched = form.exam_total !== '' && form.exam_total !== autoTotal();
				if (s.student_type === 'rashidi') {
					deriveRashidiStage('from', form.exam_from);
					deriveRashidiStage('to', form.exam_to);
				} else {
					syncAyahFromPage('from');
					syncAyahFromPage('to');
				}
			}
			status = 'ready';
		} catch (e) {
			error = errorMessage(e, 'تعذّر تحميل البيانات');
			status = 'error';
		}
	}

	/** Best-effort: a planned exam is a nicety, never a reason to fail the screen. */
	async function loadNextExam() {
		if (!net.online) return;
		try {
			const res = await upcomingExamsApi.next([studentId]);
			nextExam = res.items[0]?.exam ?? null;
			if (nextExam) examSectionOpen = true;
		} catch {
			/* offline or unavailable — the section simply stays hidden */
		}
	}

	function openExamForm() {
		examForm = {
			scheduled_date: nextExam?.scheduled_date ?? '',
			part: nextExam?.part?.toString() ?? '',
			exam_from: nextExam?.exam_from?.toString() ?? '',
			exam_to: nextExam?.exam_to?.toString() ?? '',
			notes: nextExam?.notes ?? ''
		};
		examSectionOpen = true;
		examOpen = true;
	}

	async function saveExam() {
		if (examSaving) return;
		if (!examForm.scheduled_date) {
			flash('err', 'حدّد تاريخ الاختبار');
			return;
		}
		examSaving = true;
		try {
			const body = {
				student_id: studentId,
				halaqah_id: halaqahId,
				scheduled_date: examForm.scheduled_date,
				part: wholeOrNull(examForm.part) ?? null,
				exam_from: wholeOrNull(examForm.exam_from) ?? null,
				exam_to: wholeOrNull(examForm.exam_to) ?? null,
				notes: orNull(examForm.notes)
			};
			// Editing the existing plan rather than stacking a second one for the same day.
			nextExam = nextExam
				? await upcomingExamsApi.update(nextExam.id, body)
				: await upcomingExamsApi.create(body);
			examOpen = false;
			flash('ok', 'تم حفظ الاختبار القادم');
		} catch (e) {
			flash('err', errorMessage(e, 'تعذّر حفظ الاختبار — تحقق من الاتصال'));
		} finally {
			examSaving = false;
		}
	}

	async function cancelExam() {
		if (!nextExam) return;
		try {
			await upcomingExamsApi.remove(nextExam.id);
			nextExam = null;
			examOpen = false;
			flash('ok', 'تم حذف الاختبار القادم');
		} catch {
			flash('err', 'تعذّر الحذف — تحقق من الاتصال');
		}
	}

	function orNull(s: string): string | null {
		const t = s.trim();
		return t === '' ? null : t;
	}

	/**
	 * Parse a page *number* field (من / إلى / الجزء): whole numbers only.
	 * Returns `undefined` for input the server would reject, so the caller can say
	 * why *before* uploading rather than letting it become a stuck record.
	 */
	function wholeOrNull(s: string): number | null | undefined {
		const t = s.trim();
		if (t === '') return null;
		if (!/^\d+$/.test(t)) return undefined;
		const n = Number(t);
		return Number.isSafeInteger(n) ? n : undefined;
	}

	/**
	 * Parse a page *count* (العدد الكلي), which may be fractional — teachers count
	 * in halves and quarters, so «0.5» for نصف صفحة is a legitimate entry.
	 */
	function amountOrNull(s: string): number | null | undefined {
		const t = s.trim().replace('٫', '.').replace(',', '.');
		if (t === '') return null;
		if (!/^\d+(\.\d{1,2})?$/.test(t)) return undefined;
		const n = Number(t);
		return Number.isFinite(n) && n <= 999.99 ? n : undefined;
	}

	/** Arabic complaint about the exam fields, or null when they are fine. */
	function validateExam(): string | null {
		for (const [raw, label] of [
			[form.exam_from, 'التسميع «من»'],
			[form.exam_to, 'التسميع «إلى»']
		] as [string, string][]) {
			if (wholeOrNull(raw) === undefined) {
				return `${label}: يجب أن يكون رقماً صحيحاً بدون فاصلة عشرية`;
			}
		}
		if (amountOrNull(form.exam_total) === undefined) {
			return 'العدد الكلي: رقم غير صالح (يمكن استخدام الكسور مثل 0.5)';
		}
		const from = wholeOrNull(form.exam_from);
		const to = wholeOrNull(form.exam_to);
		if (from != null && to != null && to < from) {
			return 'التسميع «إلى» يجب ألا يكون أصغر من «من»';
		}
		return null;
	}

	/** Page *numbers* are whole: some Android keyboards offer «.» even with
	 *  `inputmode="numeric"`, and a decimal point there can only ever be rejected. */
	function digitsOnly(event: Event) {
		const el = event.currentTarget as HTMLInputElement;
		const cleaned = el.value.replace(/[^\d]/g, '');
		if (cleaned !== el.value) el.value = cleaned;
	}

	function addRevision() {
		// Default the review to the whole juzʼ (كله).
		revisions = [...revisions, { part: 1, half: 0, success: true }];
	}
	function removeRevision(i: number) {
		revisions = revisions.filter((_, idx) => idx !== i);
	}

	function addRashidiRevision() {
		rashidiRevisions = [...rashidiRevisions, { stage: 1, success: true }];
	}
	function removeRashidiRevision(i: number) {
		rashidiRevisions = rashidiRevisions.filter((_, idx) => idx !== i);
	}

	function toggleProblem(id: string) {
		form.problem_ids = form.problem_ids.includes(id)
			? form.problem_ids.filter((x) => x !== id)
			: [...form.problem_ids, id];
	}

	function flash(type: 'ok' | 'err', text: string) {
		feedback = { type, text };
		clearTimeout(feedbackTimer);
		feedbackTimer = setTimeout(() => (feedback = null), 2400);
	}

	async function save() {
		if (saving || !auth.teacher) return;
		// Catch what the server would reject, while the teacher is still looking at
		// the field — never let it become a stuck record in the outbox.
		const invalid = validateExam();
		if (invalid) {
			flash('err', invalid);
			return;
		}
		saving = true;
		feedback = null;
		// Everything except attendance (present/excused) — that is set on the الحضور tab.
		const fields = {
			exam_from: wholeOrNull(form.exam_from) ?? null,
			exam_to: wholeOrNull(form.exam_to) ?? null,
			exam_from_line: fromLine === '' ? null : fromLine,
			exam_to_line: toLine === '' ? null : toLine,
			exam_total: amountOrNull(form.exam_total) ?? null,
			rating: (form.rating as Rating | null) ?? null,
			revision_lesson: isRashidi
				? serializeRashidiRevisions(rashidiRevisions)
				: serializeRevisions(revisions),
			revision_rating: (form.revision_rating as Rating | null) ?? null,
			homework: orNull(form.homework),
			attitude: (form.attitude as Attitude | null) ?? null,
			added_points: form.added_points ?? 0,
			notes: orNull(form.notes),
			problems: orNull(form.problems),
			problem_ids: form.problem_ids
		};
		try {
			await repo.upsertDailyRecord({
				student_id: studentId,
				teacher_id: auth.teacher.id,
				halaqah_id: halaqahId,
				record_date: date,
				...fields
			});
			flash('ok', net.online ? 'تم حفظ السجل' : 'حُفظ محلياً — سيُرفع عند الاتصال');
			setTimeout(() => goto(`/halaqat/${halaqahId}?tab=recitation&date=${date}`), 600);
		} catch (e) {
			console.error('save daily record failed', e);
			flash('err', errorMessage(e, 'تعذّر حفظ السجل'));
			saving = false;
		}
	}

	async function deleteTodayRecord() {
		if (deleting || !record) return;
		deleting = true;
		try {
			await repo.deleteRecord(record.id);
			flash('ok', net.online ? 'تم حذف السجل' : 'حُذف محلياً — سيُحذف من الخادم عند الاتصال');
			setTimeout(() => goto(`/halaqat/${halaqahId}?tab=recitation&date=${date}`), 600);
		} catch (e) {
			console.error('delete daily record failed', e);
			flash('err', errorMessage(e, 'تعذّر حذف السجل'));
			deleting = false;
		}
	}
</script>

<TopBar
	title={student?.full_name ?? 'الطالب'}
	subtitle="اليوم {formatDateArabic(date)}{nextSession
		? ` · القادم ${formatDateArabic(nextSession)}`
		: ''}"
	backHref={`/halaqat/${halaqahId}`}
/>

<main class="mx-auto max-w-2xl space-y-3 px-3 pb-28 pt-[4.5rem]" dir="rtl">
	{#if status === 'loading'}
		<Spinner label="جارٍ التحميل…" />
	{:else if status === 'error'}
		<EmptyState icon="error" title="حدث خطأ" hint={error} />
	{:else}
		<!-- ===== Brief last-session summary: light, concise — recitation / revision / homework ===== -->
		<section class="rounded-3xl bg-surface-container-low/70 px-3.5 py-3">
			<div class="flex items-center gap-1.5 text-on-surface-variant/60">
				<Icon name="history" class="text-sm" />
				<span class="text-[11px] font-bold">آخر جلسة</span>
				{#if prevRecitation}
					<span class="text-[10px] text-on-surface-variant/45">
						{formatDateShort(prevRecitation.record_date)}{prevRecitation.rating != null
							? ` · ${ratingLabel(prevRecitation.rating)}`
							: ''}
					</span>
				{/if}
			</div>
			<div class="mt-2 grid grid-cols-2 gap-2 text-[11px]">
				<div class="min-w-0">
					<p class="text-on-surface-variant/45">التسميع</p>
					{#if prevRecitation?.exam_from != null || prevRecitation?.exam_to != null || requiredHomework}
						<p class="truncate font-bold text-on-surface-variant/80">
							من {toLatinDigits(
								examPageLabel(prevRecitation?.exam_from, prevRecitation?.exam_from_line)
							)}
						</p>
						<p class="truncate font-bold text-on-surface-variant/80">
							إلى {toLatinDigits(
								examPageLabel(prevRecitation?.exam_to, prevRecitation?.exam_to_line)
							)}
						</p>
						<p class="truncate font-bold text-on-surface-variant/80">
							وظيفة {toLatinDigits(requiredHomework) || '—'}
						</p>
					{:else}
						<p class="truncate font-bold text-on-surface-variant/80">لا يوجد</p>
					{/if}
				</div>
				<div class="min-w-0">
					<p class="text-on-surface-variant/45">المراجعة</p>
					<p class="truncate font-bold text-on-surface-variant/80">
						{toLatinDigits(prevRecitation?.revision_lesson) || 'لا يوجد'}
					</p>
				</div>
			</div>
		</section>

		<!-- ===== Detailed points strip: each source of points, total fixed at the line's end ===== -->
		<div
			class="flex flex-wrap items-center justify-between gap-x-1.5 gap-y-1 px-1 text-[10px] leading-none text-on-surface-variant/60"
		>
			<div class="flex flex-wrap items-center gap-x-1 gap-y-1">
				<span>حضور {scores.present}</span>
				<span class="text-on-surface-variant/25">·</span>
				<span>تسميع {scores.exam}</span>
				<span class="text-on-surface-variant/25">·</span>
				<span>مراجعة {scores.revision}</span>
				<span class="text-on-surface-variant/25">·</span>
				<span>أدب {scores.attitude}</span>
				{#if (form.added_points ?? 0) !== 0}
					<span class="text-on-surface-variant/25">·</span>
					<span class={(form.added_points ?? 0) > 0 ? 'text-emerald-700' : 'text-error'}>
						إضافي {(form.added_points ?? 0) > 0 ? '+' : ''}{form.added_points}
					</span>
				{/if}
			</div>
			<span class="shrink-0 font-bold text-primary">{scores.total} نقطة</span>
		</div>

		<!-- ===== التسميع ===== -->
		<section
			class="space-y-3 rounded-3xl border border-outline-variant/15 bg-surface-container-lowest p-3.5 shadow-card"
		>
			<Field
				label="التسميع"
				icon="menu_book"
				hint={isRashidi
					? '(المرحلة تُضيّق الصفحة، والصفحة تحدّد المرحلة)'
					: '(الجزء/السورة/الآية تملأ الصفحة، أو العكس)'}
			>
				{#snippet actions()}
					<div class="flex items-center gap-1.5">
						<button
							type="button"
							onclick={fillLastPosition}
							disabled={prevRecitation?.exam_to == null && prevRecitation?.exam_from == null}
							aria-label="تعبئة آخر موضع وصل إليه الطالب"
							class="flex h-7 w-7 items-center justify-center rounded-full bg-primary/10 text-primary active:scale-90 disabled:opacity-40"
						>
							<Icon name="trending_up" class="text-base" />
						</button>
						<button
							type="button"
							onclick={resetTasmee}
							aria-label="تصفير بطاقة التسميع"
							class="flex h-7 w-7 items-center justify-center rounded-full bg-surface-container-high text-on-surface-variant active:scale-90"
						>
							<Icon name="cancel" class="text-base" />
						</button>
					</div>
				{/snippet}
				<div class="space-y-1 rounded-2xl bg-surface-container-low/60 px-2.5 pb-2 pt-1">
					{#if isRashidi}
						<!-- رشيدي: صفحة/مرحلة/سطر بدل جزء/سورة/آية/صفحة -->
						<span class="pr-1 text-[10px] font-bold text-on-surface-variant/60">من</span>
						<div class="grid grid-cols-3 gap-1">
							<div class="min-w-0 space-y-0.5">
								<span class="block text-center text-[9px] text-on-surface-variant/45">ص</span>
								<Dropdown
									bind:value={form.exam_from}
									options={toPageOptions(rashidiPageOptions(fromStage))}
									onchange={() => syncStageFromPageRashidi('from')}
									class="px-1.5 py-3 text-[11px]"
								/>
							</div>
							<div class="min-w-0 space-y-0.5">
								<span class="block text-center text-[9px] text-on-surface-variant/45">مرحلة</span>
								<Dropdown
									bind:value={fromStage}
									options={RASHIDI_STAGE_OPTIONS}
									onchange={() => syncPageFromStageRashidi('from')}
									class="px-1.5 py-3 text-[11px]"
								/>
							</div>
							<div class="min-w-0 space-y-0.5">
								<span class="block text-center text-[9px] text-on-surface-variant/45">سطر</span>
								<Dropdown
									bind:value={fromLine}
									options={RASHIDI_LINE_OPTIONS}
									class="px-1.5 py-3 text-[11px]"
								/>
							</div>
						</div>

						<span class="block pr-1 pt-0.5 text-[10px] font-bold text-on-surface-variant/60"
							>إلى</span
						>
						<div class="grid grid-cols-3 gap-1">
							<Dropdown
								bind:value={form.exam_to}
								options={toPageOptions(rashidiPageOptions(toStage))}
								onchange={() => syncStageFromPageRashidi('to')}
								class="px-1.5 py-3 text-[11px]"
							/>
							<Dropdown
								bind:value={toStage}
								options={RASHIDI_STAGE_OPTIONS}
								onchange={() => syncPageFromStageRashidi('to')}
								class="px-1.5 py-3 text-[11px]"
							/>
							<Dropdown
								bind:value={toLine}
								options={RASHIDI_LINE_OPTIONS}
								class="px-1.5 py-3 text-[11px]"
							/>
						</div>

						<span class="block pr-1 pt-0.5 text-[10px] font-bold text-on-surface-variant/60"
							>وظيفة</span
						>
						<div class="grid grid-cols-3 gap-1">
							<Dropdown
								bind:value={hwPage}
								options={toPageOptions(rashidiPageOptions(hwStage))}
								onchange={() => syncStageFromPageRashidi('hw')}
								class="px-1.5 py-3 text-[11px]"
							/>
							<Dropdown
								bind:value={hwStage}
								options={RASHIDI_STAGE_OPTIONS}
								onchange={() => syncPageFromStageRashidi('hw')}
								class="px-1.5 py-3 text-[11px]"
							/>
							<Dropdown
								bind:value={hwLine}
								options={RASHIDI_LINE_OPTIONS}
								class="px-1.5 py-3 text-[11px]"
							/>
						</div>
					{:else}
						<!-- من: مع عناوين الأعمدة (الترتيب: صفحة، جزء، سورة، آية) -->
						<span class="pr-1 text-[10px] font-bold text-on-surface-variant/60">من</span>
						<div class="grid grid-cols-4 gap-1">
							<div class="min-w-0 space-y-0.5">
								<span class="block text-center text-[9px] text-on-surface-variant/45">ص</span>
								<Dropdown
									bind:value={form.exam_from}
									options={toPageOptions(pageOptions(fromSurah, fromJuz))}
									onchange={() => syncAyahFromPage('from')}
									class="px-1.5 py-3 text-[11px]"
								/>
							</div>
							<div class="min-w-0 space-y-0.5">
								<span class="block text-center text-[9px] text-on-surface-variant/45">ج</span>
								<Dropdown
									bind:value={fromJuz}
									options={toOptions(juzOptions(fromSurah))}
									onchange={() => syncFromJuz('from')}
									class="px-1.5 py-3 text-[11px]"
								/>
							</div>
							<div class="min-w-0 space-y-0.5">
								<span class="block text-center text-[9px] text-on-surface-variant/45">س</span>
								<Dropdown
									bind:value={fromSurah}
									options={surahOptions(fromJuz)}
									onchange={() => onSurahPicked('from')}
									class="px-1.5 py-3 text-[11px]"
								/>
							</div>
							<div class="min-w-0 space-y-0.5">
								<span class="block text-center text-[9px] text-on-surface-variant/45">آ</span>
								<Dropdown
									bind:value={fromAyah}
									options={toOptions(ayahOptions(fromSurah, fromJuz))}
									disabled={fromSurah === ''}
									onchange={() => syncPageFromAyah('from')}
									class="px-1.5 py-3 text-[11px]"
								/>
							</div>
						</div>

						<!-- إلى: بدون تكرار عناوين الأعمدة -->
						<span class="block pr-1 pt-0.5 text-[10px] font-bold text-on-surface-variant/60"
							>إلى</span
						>
						<div class="grid grid-cols-4 gap-1">
							<Dropdown
								bind:value={form.exam_to}
								options={toPageOptions(pageOptions(toSurah, toJuz))}
								onchange={() => syncAyahFromPage('to')}
								class="px-1.5 py-3 text-[11px]"
							/>
							<Dropdown
								bind:value={toJuz}
								options={toOptions(juzOptions(toSurah))}
								onchange={() => syncFromJuz('to')}
								class="px-1.5 py-3 text-[11px]"
							/>
							<Dropdown
								bind:value={toSurah}
								options={surahOptions(toJuz)}
								onchange={() => onSurahPicked('to')}
								class="px-1.5 py-3 text-[11px]"
							/>
							<Dropdown
								bind:value={toAyah}
								options={toOptions(ayahOptions(toSurah, toJuz))}
								disabled={toSurah === ''}
								onchange={() => syncPageFromAyah('to')}
								class="px-1.5 py-3 text-[11px]"
							/>
						</div>

						<!-- وظيفة: نفس تنسيق سطري من/إلى -->
						<span class="block pr-1 pt-0.5 text-[10px] font-bold text-on-surface-variant/60"
							>وظيفة</span
						>
						<div class="grid grid-cols-4 gap-1">
							<Dropdown
								bind:value={hwPage}
								options={toPageOptions(pageOptions(hwSurah, hwJuz))}
								onchange={() => syncAyahFromPage('hw')}
								class="px-1.5 py-3 text-[11px]"
							/>
							<Dropdown
								bind:value={hwJuz}
								options={toOptions(juzOptions(hwSurah))}
								onchange={() => syncFromJuz('hw')}
								class="px-1.5 py-3 text-[11px]"
							/>
							<Dropdown
								bind:value={hwSurah}
								options={surahOptions(hwJuz)}
								onchange={() => onSurahPicked('hw')}
								class="px-1.5 py-3 text-[11px]"
							/>
							<Dropdown
								bind:value={hwAyah}
								options={toOptions(ayahOptions(hwSurah, hwJuz))}
								disabled={hwSurah === ''}
								onchange={() => syncPageFromAyah('hw')}
								class="px-1.5 py-3 text-[11px]"
							/>
						</div>
					{/if}

					<!-- المجموع: يُحسب تلقائياً من «من»/«إلى» ويبقى قابلاً للتعديل، لأن التسميع
					     كثيراً ما يكون نصف صفحة أو ربعها ولا يطابق عدد الصفحات الكامل. -->
					<div class="flex items-center gap-1.5 pr-1 pt-1">
						<span class="shrink-0 text-[10px] font-bold text-on-surface-variant/60">المجموع</span>
						<button
							type="button"
							onclick={() => stepTotal(-0.5)}
							aria-label="إنقاص نصف صفحة"
							class="grid size-7 shrink-0 place-items-center rounded-full border border-outline-variant/25 pb-0.5 font-jakarta text-[16px] font-bold leading-none text-on-surface-variant active:scale-95"
							>−</button
						>
						<input
							bind:value={form.exam_total}
							oninput={() => (totalTouched = true)}
							inputmode="decimal"
							placeholder="—"
							class="w-14 rounded-xl border border-outline-variant/25 bg-surface-container-lowest py-1.5 text-center font-jakarta text-[13px] font-bold text-on-surface"
						/>
						<button
							type="button"
							onclick={() => stepTotal(0.5)}
							aria-label="زيادة نصف صفحة"
							class="grid size-7 shrink-0 place-items-center rounded-full border border-outline-variant/25 pb-0.5 font-jakarta text-[16px] font-bold leading-none text-on-surface-variant active:scale-95"
							>+</button
						>
						<span class="shrink-0 text-[10px] text-on-surface-variant/50">صفحة</span>
						{#if totalTouched}
							<button
								type="button"
								onclick={resetTotalToAuto}
								class="mr-auto shrink-0 text-[10px] font-bold text-primary underline underline-offset-2"
							>
								تلقائي
							</button>
						{/if}
					</div>
				</div>
			</Field>

			<div class="flex items-center gap-2">
				<div class="flex shrink-0 items-center gap-1">
					<Icon name="grade" class="text-base text-primary" />
					<span class="text-[13px] font-bold text-on-surface-variant">التقدير</span>
				</div>
				<PillGroup bind:value={form.rating} options={RATING_OPTIONS} compact class="flex-1" />
			</div>
		</section>

		<!-- ===== المراجعة ===== -->
		<section
			class="space-y-3 rounded-3xl border border-outline-variant/15 bg-surface-container-lowest p-3.5 shadow-card"
		>
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-1.5">
					<Icon name="history_edu" class="text-base text-primary" />
					<span class="text-[13px] font-bold text-on-surface-variant">المراجعة</span>
					{#if (isRashidi ? rashidiRevisions : revisions).length > 0}
						<span class="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-bold text-primary"
							>{(isRashidi ? rashidiRevisions : revisions).length}</span
						>
					{/if}
				</div>
				<button
					onclick={isRashidi ? addRashidiRevision : addRevision}
					class="flex items-center gap-1 rounded-full bg-primary/10 px-2.5 py-1 text-[11px] font-bold text-primary active:scale-95"
				>
					<Icon name="add" class="text-sm" /> إضافة
				</button>
			</div>

			{#if isRashidi}
				{#if rashidiRevisions.length > 0}
					<div class="space-y-1.5">
						{#each rashidiRevisions as rev, i (i)}
							<!-- grid (not flex): المرحلة takes the remaining space, أخفق/نجح and the trash
								     icon take only what their content needs — no النصف column لرشيدي. -->
							<div class="grid items-center gap-1" style="grid-template-columns: 1fr auto auto;">
								<Dropdown
									bind:value={rev.stage}
									options={RASHIDI_STAGE_OPTIONS}
									class="min-w-0 px-1.5 py-3 text-[11px]"
								/>
								<div class="flex overflow-hidden rounded-full border border-outline-variant/30">
									<button
										type="button"
										onclick={() => (rev.success = false)}
										class={cn(
											'px-2 py-3 text-[11px] font-bold transition active:scale-95',
											!rev.success
												? 'bg-error text-on-error'
												: 'bg-surface-container-low text-on-surface-variant'
										)}
									>
										أخفق
									</button>
									<button
										type="button"
										onclick={() => (rev.success = true)}
										class={cn(
											'px-2 py-3 text-[11px] font-bold transition active:scale-95',
											rev.success
												? 'bg-emerald-500 text-white'
												: 'bg-surface-container-low text-on-surface-variant'
										)}
									>
										نجح
									</button>
								</div>
								<button
									onclick={() => removeRashidiRevision(i)}
									class="rounded-full p-1 text-error active:scale-90"
									aria-label="حذف المراجعة"
								>
									<Icon name="delete" class="text-[15px]" />
								</button>
							</div>
						{/each}
					</div>
				{/if}
			{:else if revisions.length > 0}
				<div class="space-y-1.5">
					{#each revisions as rev, i (i)}
						<!-- grid (not flex) so the four columns always sum to exactly the card's width,
							     regardless of content length — الجزء and النصف share the fr space, أخفق/نجح
							     and the trash icon take only what their content needs. -->
						<div
							class="grid items-center gap-1"
							style="grid-template-columns: 1fr 1.15fr auto auto;"
						>
							<Dropdown
								bind:value={rev.part}
								options={QURAN_PART_OPTIONS}
								class="min-w-0 px-1.5 py-3 text-[11px]"
							/>
							<Dropdown
								bind:value={rev.half}
								options={HALF_OPTIONS}
								class="min-w-0 px-1.5 py-3 text-[11px]"
							/>
							<!-- أخفق / نجح side by side instead of one toggle, so both choices are visible at once -->
							<div class="flex overflow-hidden rounded-full border border-outline-variant/30">
								<button
									type="button"
									onclick={() => (rev.success = false)}
									class={cn(
										'px-2 py-3 text-[11px] font-bold transition active:scale-95',
										!rev.success
											? 'bg-error text-on-error'
											: 'bg-surface-container-low text-on-surface-variant'
									)}
								>
									أخفق
								</button>
								<button
									type="button"
									onclick={() => (rev.success = true)}
									class={cn(
										'px-2 py-3 text-[11px] font-bold transition active:scale-95',
										rev.success
											? 'bg-emerald-500 text-white'
											: 'bg-surface-container-low text-on-surface-variant'
									)}
								>
									نجح
								</button>
							</div>
							<button
								onclick={() => removeRevision(i)}
								class="rounded-full p-1 text-error active:scale-90"
								aria-label="حذف المراجعة"
							>
								<Icon name="delete" class="text-[15px]" />
							</button>
						</div>
					{/each}
				</div>
			{/if}

			<div class="flex items-center gap-2">
				<div class="flex shrink-0 items-center gap-1">
					<Icon name="grade" class="text-base text-primary" />
					<span class="text-[13px] font-bold text-on-surface-variant">تقييم المراجعة</span>
				</div>
				<PillGroup
					bind:value={form.revision_rating}
					options={RATING_OPTIONS}
					compact
					class="flex-1"
				/>
			</div>
		</section>

		<!-- ===== الأدب · نقاط إضافية / حسم ===== -->
		<section
			class="space-y-3 rounded-3xl border border-outline-variant/15 bg-surface-container-lowest p-3.5 shadow-card"
		>
			<div class="flex items-center gap-2">
				<div class="flex shrink-0 items-center gap-1">
					<Icon name="volunteer_activism" class="text-base text-primary" />
					<span class="text-[13px] font-bold text-on-surface-variant">الأدب</span>
				</div>
				<PillGroup bind:value={form.attitude} options={ATTITUDE_OPTIONS} compact class="flex-1" />
			</div>

			<!-- Free entry, positive or negative: the institute asked for points to be
			     added *and* deducted rather than picked from a fixed list. The chips are
			     shortcuts, not the only way in. -->
			<Field label="نقاط إضافية / حسم" icon="star" hint="(بالسالب للحسم)">
				{#snippet actions()}
					<button
						type="button"
						onclick={() => (form.added_points = 0)}
						aria-label="تصفير النقاط الإضافية"
						class="flex h-7 w-7 items-center justify-center rounded-full bg-surface-container-high text-on-surface-variant active:scale-90"
					>
						<Icon name="cancel" class="text-base" />
					</button>
				{/snippet}
				<div class="space-y-2">
					<div class="flex items-center gap-2">
						<button
							type="button"
							onclick={() => (form.added_points = (form.added_points ?? 0) - 1)}
							class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-error/10 text-lg font-bold text-error active:scale-95"
							aria-label="إنقاص نقطة"
						>
							−
						</button>
						<input
							value={form.added_points ?? 0}
							oninput={(e) => {
								const raw = (e.currentTarget as HTMLInputElement).value.replace(/[^0-9-]/g, '');
								const n = Number(raw);
								form.added_points = raw === '' || raw === '-' ? 0 : Number.isFinite(n) ? n : 0;
							}}
							inputmode="numeric"
							class="min-w-0 flex-1 rounded-2xl bg-surface-container-low px-3 py-2.5 text-center font-jakarta text-lg font-bold text-on-surface focus:outline-none focus:ring-2 focus:ring-primary/20"
						/>
						<button
							type="button"
							onclick={() => (form.added_points = (form.added_points ?? 0) + 1)}
							class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary/10 text-lg font-bold text-primary active:scale-95"
							aria-label="زيادة نقطة"
						>
							+
						</button>
					</div>
					<div class="flex flex-wrap gap-1.5">
						{#each ADDED_POINTS_OPTIONS.filter((v) => v !== 0) as v (v)}
							<button
								type="button"
								onclick={() => (form.added_points = v)}
								class={'rounded-full border px-3 py-1 text-[11px] font-bold transition active:scale-95 ' +
									((form.added_points ?? 0) === v
										? 'border-primary bg-primary text-on-primary'
										: 'border-outline-variant/30 bg-surface-container-low text-on-surface-variant')}
							>
								{`+${v}`}
							</button>
						{/each}
					</div>
				</div>
			</Field>
		</section>

		<!-- ===== الملاحظات — بطاقة مستقلة ===== -->
		<section
			class="rounded-3xl border border-outline-variant/15 bg-surface-container-lowest p-3.5 shadow-card"
		>
			<Field label="الملاحظات" icon="edit_note">
				<textarea
					bind:value={form.notes}
					rows="2"
					placeholder="اكتب ملاحظاتك هنا…"
					class="w-full resize-none rounded-xl bg-surface-container-low p-3 text-sm text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none focus:ring-2 focus:ring-primary/20"
				></textarea>
			</Field>
		</section>

		<!-- ===== الصعوبات — collapsed unless used; اختيار من قائمة جاهزة فقط ===== -->
		<section
			class="rounded-3xl border border-outline-variant/15 bg-surface-container-lowest shadow-card"
		>
			<button
				type="button"
				onclick={() => (extrasOpen = !extrasOpen)}
				class="flex w-full items-center gap-2 px-3.5 py-3 text-right"
			>
				<Icon name="report" class="text-base text-primary" />
				<span class="flex-1 text-[13px] font-bold text-on-surface-variant">الصعوبات</span>
				{#if extrasCount > 0}
					<span class="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-bold text-primary"
						>{extrasCount}</span
					>
				{/if}
				<Icon
					name={extrasOpen ? 'expand_less' : 'expand_more'}
					class="text-lg text-on-surface-variant/50"
				/>
			</button>

			{#if extrasOpen}
				<div class="space-y-3 border-t border-outline-variant/15 p-3.5">
					{#if problemsByLevel.length > 0}
						<div class="space-y-2.5">
							{#each problemsByLevel as group (group.levelName)}
								<div>
									<p class="mb-1 text-[11px] font-semibold text-on-surface-variant/70">
										{group.levelName}
									</p>
									<div class="flex flex-wrap gap-1.5">
										{#each group.items as p (p.id)}
											{@const selected = form.problem_ids.includes(p.id)}
											<button
												type="button"
												onclick={() => toggleProblem(p.id)}
												class={'rounded-full border px-2.5 py-1 text-[11px] font-medium transition active:scale-95 ' +
													(selected
														? 'border-primary bg-primary text-on-primary shadow-sm'
														: 'border-outline-variant/30 bg-surface-container-low text-on-surface-variant')}
											>
												{p.name}
											</button>
										{/each}
									</div>
								</div>
							{/each}
						</div>
					{:else}
						<p class="text-center text-[11px] text-on-surface-variant/50">
							لا توجد صعوبات معرَّفة لاختيارها.
						</p>
					{/if}
				</div>
			{/if}
		</section>

		<!-- ===== الاختبار القادم — مطوية افتراضياً، أسفل الصعوبات ===== -->
		<section
			class="rounded-3xl border border-outline-variant/15 bg-surface-container-lowest shadow-card"
		>
			<button
				type="button"
				onclick={() => (examSectionOpen = !examSectionOpen)}
				class="flex w-full items-center gap-2 px-3.5 py-3 text-right"
			>
				<Icon name="event_upcoming" class="text-base text-primary" />
				<span class="flex-1 text-[13px] font-bold text-on-surface-variant">الاختبار القادم</span>
				{#if nextExam}
					<span class="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-bold text-primary">
						{formatDateArabic(nextExam.scheduled_date)}
					</span>
				{/if}
				<Icon
					name={examSectionOpen ? 'expand_less' : 'expand_more'}
					class="text-lg text-on-surface-variant/50"
				/>
			</button>

			{#if examSectionOpen}
				<div class="space-y-2.5 border-t border-outline-variant/15 p-3.5">
					<div class="flex items-center justify-between gap-2">
						<div class="min-w-0 flex-1">
							{#if nextExam}
								<p class="truncate text-[13px] font-bold text-on-surface">{nextExam.summary}</p>
								{#if nextExam.notes}
									<p class="mt-0.5 truncate text-[11px] text-on-surface-variant/60">
										{nextExam.notes}
									</p>
								{/if}
							{:else}
								<p class="text-[12px] text-on-surface-variant/50">لم يُحدَّد اختبار قادم.</p>
							{/if}
						</div>
						<button
							type="button"
							onclick={openExamForm}
							class="flex shrink-0 items-center gap-1 rounded-full bg-primary/10 px-2.5 py-1 text-[11px] font-bold text-primary active:scale-95"
						>
							<Icon name={nextExam ? 'edit_note' : 'add'} class="text-sm" />
							{nextExam ? 'تعديل' : 'تحديد'}
						</button>
					</div>

					{#if examOpen}
						<div class="space-y-2.5 border-t border-outline-variant/15 pt-3">
							<div class="space-y-1">
								<span class="pr-1 text-[11px] font-bold text-on-surface-variant"
									>تاريخ الاختبار</span
								>
								<input
									type="date"
									bind:value={examForm.scheduled_date}
									class="w-full rounded-xl bg-surface-container-low px-3 py-2 text-sm text-on-surface focus:outline-none focus:ring-2 focus:ring-primary/20"
								/>
							</div>
							<div class="grid grid-cols-3 gap-2">
								<input
									bind:value={examForm.part}
									inputmode="numeric"
									oninput={digitsOnly}
									placeholder="الجزء"
									class="rounded-xl bg-surface-container-low px-2 py-2 text-center text-sm text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none focus:ring-2 focus:ring-primary/20"
								/>
								<input
									bind:value={examForm.exam_from}
									inputmode="numeric"
									placeholder="من"
									class="rounded-xl bg-surface-container-low px-2 py-2 text-center text-sm text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none focus:ring-2 focus:ring-primary/20"
								/>
								<input
									bind:value={examForm.exam_to}
									inputmode="numeric"
									placeholder="إلى"
									class="rounded-xl bg-surface-container-low px-2 py-2 text-center text-sm text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none focus:ring-2 focus:ring-primary/20"
								/>
							</div>
							<input
								bind:value={examForm.notes}
								placeholder="ملاحظات (اختياري)"
								class="w-full rounded-xl bg-surface-container-low px-3 py-2 text-sm text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none focus:ring-2 focus:ring-primary/20"
							/>
							<div class="flex gap-2">
								<button
									type="button"
									onclick={() => (examOpen = false)}
									class="flex-1 rounded-full bg-surface-container-high py-2.5 text-[12px] font-bold text-on-surface-variant active:scale-95"
								>
									إلغاء
								</button>
								{#if nextExam}
									<button
										type="button"
										onclick={cancelExam}
										class="rounded-full bg-error/10 px-4 py-2.5 text-[12px] font-bold text-error active:scale-95"
									>
										حذف
									</button>
								{/if}
								<button
									type="button"
									onclick={saveExam}
									disabled={examSaving}
									class="flex flex-1 items-center justify-center gap-1.5 rounded-full bg-brand py-2.5 text-[12px] font-bold text-white active:scale-95 disabled:opacity-70"
								>
									{#if examSaving}<Loader class="text-sm" />{/if} حفظ
								</button>
							</div>
							<p class="text-[10px] text-on-surface-variant/50">
								يتطلب تحديد الاختبار اتصالاً بالإنترنت.
							</p>
						</div>
					{/if}
				</div>
			{/if}
		</section>

		<!-- ===== استدعاء ولي الأمر · حذف سجل اليوم ===== -->
		<div class="flex gap-2">
			<button
				type="button"
				onclick={() => (summonOpen = true)}
				class="flex flex-1 items-center justify-center gap-1.5 rounded-3xl border border-error/20 bg-error/5 py-3 text-[12px] font-bold text-error active:scale-[0.98]"
			>
				<Icon name="groups" class="text-base" /> استدعاء ولي الأمر
			</button>
			{#if record}
				<button
					type="button"
					onclick={() => (deleteOpen = true)}
					class="flex flex-1 items-center justify-center gap-1.5 rounded-3xl border border-error/20 bg-error/5 py-3 text-[12px] font-bold text-error active:scale-[0.98]"
				>
					<Icon name="delete" class="text-base" /> حذف سجل اليوم
				</button>
			{/if}
		</div>
	{/if}
</main>

{#if student}
	<SummonSheet
		bind:open={summonOpen}
		studentId={student.id}
		studentName={student.full_name}
		{halaqahId}
		onDone={(msg) => flash('ok', msg)}
	/>
{/if}

<ConfirmDialog
	bind:open={deleteOpen}
	title="حذف سجل اليوم؟"
	message="سيتم حذف كل بيانات هذا اليوم لهذا الطالب نهائياً — الحضور والتسميع والمراجعة والملاحظات. لا يمكن التراجع عن هذا الإجراء."
	confirmLabel="حذف نهائي"
	tone="danger"
	icon="delete"
	onConfirm={deleteTodayRecord}
/>

{#if feedback}
	<div
		class={'fixed inset-x-0 bottom-28 z-50 mx-auto flex w-fit items-center gap-2 rounded-full px-4 py-2.5 text-sm font-bold text-white shadow-lg ' +
			(feedback.type === 'ok' ? 'bg-primary' : 'bg-error')}
	>
		<Icon name={feedback.type === 'ok' ? 'check_circle' : 'error'} class="text-lg" />
		{feedback.text}
	</div>
{/if}

{#if status === 'ready'}
	<button
		onclick={save}
		disabled={saving}
		class="fixed bottom-8 left-6 z-50 flex h-16 w-16 items-center justify-center rounded-full bg-brand text-white shadow-fab transition active:scale-95 disabled:opacity-70"
		aria-label="حفظ"
	>
		{#if saving}
			<Loader class="text-3xl" />
		{:else}
			<Icon name="check" class="text-3xl" />
		{/if}
	</button>
{/if}
