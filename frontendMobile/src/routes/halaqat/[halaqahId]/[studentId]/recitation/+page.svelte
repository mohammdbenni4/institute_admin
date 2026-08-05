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
		parseRevisions,
		ratingLabel,
		serializeRevisions,
		type RevisionRow
	} from '$lib/labels';
	import {
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
	import { upcomingExamsApi, type UpcomingExam } from '$lib/api';

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
	// The student's most recent exam and the homework they were told to prepare.
	let prevRecitation = $state<DailyRecord | null>(null);
	let requiredHomework = $state<string | null>(null);

	// Notes / difficulties start collapsed: most sessions never touch them, and
	// keeping them open made this screen far longer than a phone can show.
	let extrasOpen = $state(false);

	// «استدعاء ولي الأمر»
	let summonOpen = $state(false);

	// «الاختبار القادم» — the exam this student is working towards.
	let nextExam = $state<UpcomingExam | null>(null);
	let examOpen = $state(false);
	let examSaving = $state(false);
	let examForm = $state({ scheduled_date: '', part: '', exam_from: '', exam_to: '', notes: '' });

	/** The halaqah's next scheduled session after the day being recorded. */
	const nextSession = $derived(nextSessionDate(halaqah?.schedule, date));

	/** Short Arabic summary of what was recited (exam range and/or revision). */
	function reciteSummary(r: DailyRecord): string {
		const bits: string[] = [];
		if (r.exam_from != null && r.exam_to != null) {
			bits.push(`من ${r.exam_from} إلى ${r.exam_to}`);
		} else if (r.exam_to != null) {
			bits.push(`إلى ${r.exam_to}`);
		} else if (r.exam_from != null) {
			bits.push(`من ${r.exam_from}`);
		} else if (r.exam_total != null) {
			bits.push(`${r.exam_total} صفحة`);
		}
		if (r.revision_lesson) bits.push('مراجعة');
		return bits.join(' · ') || '—';
	}

	let form = $state({
		exam_from: '',
		exam_to: '',
		exam_total: '',
		rating: null as number | null,
		revision_rating: null as number | null,
		homework: '',
		attitude: null as number | null,
		added_points: 0 as number | null,
		notes: '',
		problems: '',
		problem_ids: [] as string[]
	});
	let revisions = $state<RevisionRow[]>([]);

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

	/** How many of the collapsed extras carry a value (shown on the toggle). */
	const extrasCount = $derived(
		(form.notes.trim() ? 1 : 0) + (form.problems.trim() ? 1 : 0) + form.problem_ids.length
	);

	onMount(load);

	async function load() {
		if (!auth.teacher) return;
		status = 'loading';
		try {
			const [s, h, rec, scoring, probs, latest] = await Promise.all([
				repo.getStudent(studentId),
				repo.getHalaqah(halaqahId),
				repo.getDayRecord(studentId, date),
				repo.getScoring(),
				repo.listProblems(),
				// No date window: a student's last recitation must show even after a
				// long absence (the old three-month lookback hid it).
				repo.latestRecitations([studentId], date)
			]);
			student = s;
			halaqah = h;
			settings = scoring;
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
				revisions = parseRevisions(record.revision_lesson);
				extrasOpen = !!(record.notes || record.problems || record.tagged_problems.length);
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

	/** The page *count* may be fractional; accept the Arabic decimal mark too. */
	function amountInput(event: Event) {
		const el = event.currentTarget as HTMLInputElement;
		const cleaned = el.value
			.replace('٫', '.')
			.replace(',', '.')
			.replace(/[^\d.]/g, '')
			.replace(/(\..*)\./g, '$1'); // at most one decimal point
		if (cleaned !== el.value) el.value = cleaned;
	}

	function addRevision() {
		// Default the review to the whole juzʼ (كله).
		revisions = [...revisions, { part: 1, half: 0, success: true }];
	}
	function removeRevision(i: number) {
		revisions = revisions.filter((_, idx) => idx !== i);
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
			exam_total: amountOrNull(form.exam_total) ?? null,
			rating: (form.rating as Rating | null) ?? null,
			revision_lesson: serializeRevisions(revisions),
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
</script>

<TopBar
	title={student?.full_name ?? 'الطالب'}
	subtitle="التسميع والمراجعة — {formatDateArabic(date)}"
	backHref={`/halaqat/${halaqahId}`}
/>

<main class="mx-auto max-w-2xl space-y-3 px-3 pb-28 pt-[4.5rem]" dir="rtl">
	{#if status === 'loading'}
		<Spinner label="جارٍ التحميل…" />
	{:else if status === 'error'}
		<EmptyState icon="error" title="حدث خطأ" hint={error} />
	{:else}
		<!-- ===== Context strip: points + what was required today + next session ===== -->
		<section class="rounded-3xl border border-outline-variant/15 bg-primary/5 p-3.5 shadow-card">
			<div class="flex items-center justify-between gap-2">
				<div class="flex min-w-0 items-center gap-1.5">
					<Icon name="history" class="text-base text-primary" />
					<span class="text-[13px] font-bold text-on-surface-variant">المطلوب اليوم</span>
				</div>
				<div class="flex shrink-0 items-baseline gap-1 text-primary">
					<span class="font-jakarta text-2xl font-bold leading-none">{scores.total}</span>
					<span class="text-[11px] font-medium">نقطة</span>
				</div>
			</div>

			<div class="mt-2.5 grid grid-cols-2 gap-x-3 gap-y-2">
				<div class="min-w-0">
					<p class="text-[10px] font-medium text-on-surface-variant/50">آخر تسميع</p>
					{#if prevRecitation}
						<p class="truncate text-[13px] font-bold text-on-surface">
							{reciteSummary(prevRecitation)}
						</p>
						<p class="text-[10px] text-on-surface-variant/60">
							{formatDateShort(prevRecitation.record_date)}{prevRecitation.rating != null
								? ` · ${ratingLabel(prevRecitation.rating)}`
								: ''}
						</p>
					{:else}
						<p class="text-[13px] font-bold text-on-surface-variant/40">لا يوجد</p>
					{/if}
				</div>
				<div class="min-w-0">
					<p class="text-[10px] font-medium text-on-surface-variant/50">الوظيفة المطلوبة</p>
					<p class="truncate text-[13px] font-bold text-on-surface">
						{toLatinDigits(requiredHomework) || 'لا يوجد واجب'}
					</p>
				</div>
			</div>

			{#if nextSession}
				<div
					class="mt-2.5 flex items-center gap-1.5 border-t border-outline-variant/15 pt-2 text-[11px]"
				>
					<Icon name="event_upcoming" class="text-[15px] text-primary" />
					<span class="text-on-surface-variant/60">التسميع القادم</span>
					<span class="font-bold text-on-surface">{formatDateArabic(nextSession)}</span>
				</div>
			{/if}
		</section>

		<!-- ===== الاختبار القادم ===== -->
		<section
			class="rounded-3xl border border-outline-variant/15 bg-surface-container-lowest p-3.5 shadow-card"
		>
			<div class="flex items-center justify-between gap-2">
				<div class="flex min-w-0 items-center gap-1.5">
					<Icon name="event_upcoming" class="text-base text-primary" />
					<span class="text-[13px] font-bold text-on-surface-variant">الاختبار القادم</span>
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

			{#if nextExam}
				<div class="mt-2 flex items-baseline justify-between gap-2">
					<span class="truncate text-[13px] font-bold text-on-surface">{nextExam.summary}</span>
					<span class="shrink-0 text-[11px] text-on-surface-variant/70">
						{formatDateArabic(nextExam.scheduled_date)}
					</span>
				</div>
				{#if nextExam.notes}
					<p class="mt-1 truncate text-[11px] text-on-surface-variant/60">{nextExam.notes}</p>
				{/if}
			{:else}
				<p class="mt-2 text-[12px] text-on-surface-variant/50">لم يُحدَّد اختبار قادم.</p>
			{/if}

			{#if examOpen}
				<div class="mt-3 space-y-2.5 border-t border-outline-variant/15 pt-3">
					<div class="space-y-1">
						<span class="pr-1 text-[11px] font-bold text-on-surface-variant">تاريخ الاختبار</span>
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
		</section>

		<!-- ===== التسميع ===== -->
		<section
			class="space-y-3 rounded-3xl border border-outline-variant/15 bg-surface-container-lowest p-3.5 shadow-card"
		>
			<Field label="التسميع" icon="menu_book" hint="(من / إلى / المجموع — يقبل 0.5)">
				<div class="grid grid-cols-3 gap-2">
					<input
						bind:value={form.exam_from}
						inputmode="numeric"
						oninput={digitsOnly}
						placeholder="من"
						class="rounded-xl bg-surface-container-low px-2 py-2 text-center text-sm text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none focus:ring-2 focus:ring-primary/20"
					/>
					<input
						bind:value={form.exam_to}
						inputmode="numeric"
						oninput={digitsOnly}
						placeholder="إلى"
						class="rounded-xl bg-surface-container-low px-2 py-2 text-center text-sm text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none focus:ring-2 focus:ring-primary/20"
					/>
					<input
						bind:value={form.exam_total}
						inputmode="decimal"
						oninput={amountInput}
						placeholder="المجموع"
						class="rounded-xl bg-surface-container-low px-2 py-2 text-center text-sm text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none focus:ring-2 focus:ring-primary/20"
					/>
				</div>
			</Field>

			<Field label="التقدير" icon="grade">
				<PillGroup bind:value={form.rating} options={RATING_OPTIONS} />
			</Field>
		</section>

		<!-- ===== المراجعة — one compact line per revised part ===== -->
		<section
			class="space-y-3 rounded-3xl border border-outline-variant/15 bg-surface-container-lowest p-3.5 shadow-card"
		>
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-1.5">
					<Icon name="history_edu" class="text-base text-primary" />
					<span class="text-[13px] font-bold text-on-surface-variant">المراجعة</span>
					{#if revisions.length > 0}
						<span class="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-bold text-primary"
							>{revisions.length}</span
						>
					{/if}
				</div>
				<button
					onclick={addRevision}
					class="flex items-center gap-1 rounded-full bg-primary/10 px-2.5 py-1 text-[11px] font-bold text-primary active:scale-95"
				>
					<Icon name="add" class="text-sm" /> إضافة
				</button>
			</div>

			{#if revisions.length === 0}
				<p
					class="rounded-xl bg-surface-container-low px-3 py-3 text-center text-[11px] text-on-surface-variant/60"
				>
					لا توجد مراجعات. اضغط «إضافة» لإضافة جزء.
				</p>
			{:else}
				<div class="space-y-1.5">
					{#each revisions as rev, i (i)}
						<div class="flex items-center gap-1.5">
							<select
								bind:value={rev.part}
								aria-label="الجزء"
								class="min-w-0 flex-1 rounded-xl border border-outline-variant/30 bg-surface-container-low px-2 py-2 text-[13px] text-on-surface focus:outline-none focus:ring-2 focus:ring-primary/20"
							>
								{#each QURAN_PARTS as p (p)}
									<option value={p}>الجزء {p}</option>
								{/each}
							</select>
							<select
								bind:value={rev.half}
								aria-label="النصف"
								class="min-w-0 flex-1 rounded-xl border border-outline-variant/30 bg-surface-container-low px-2 py-2 text-[13px] text-on-surface focus:outline-none focus:ring-2 focus:ring-primary/20"
							>
								{#each HALF_OPTIONS as h (h.value)}
									<option value={h.value}>{h.label}</option>
								{/each}
							</select>
							<!-- one tap flips نجح ⇄ أخفق -->
							<button
								type="button"
								onclick={() => (rev.success = !rev.success)}
								class={'flex w-[4.5rem] shrink-0 items-center justify-center gap-1 rounded-full border py-2 text-[11px] font-bold transition active:scale-95 ' +
									(rev.success
										? 'border-emerald-500 bg-emerald-500 text-white'
										: 'border-error bg-error text-on-error')}
							>
								<Icon name={rev.success ? 'check_circle' : 'cancel'} filled class="text-[13px]" />
								{rev.success ? 'نجح' : 'أخفق'}
							</button>
							<button
								onclick={() => removeRevision(i)}
								class="shrink-0 rounded-full p-1.5 text-error active:scale-90"
								aria-label="حذف المراجعة"
							>
								<Icon name="delete" class="text-base" />
							</button>
						</div>
					{/each}
				</div>
			{/if}

			<div class="border-t border-outline-variant/15 pt-3">
				<Field label="تقييم المراجعة" icon="grade">
					<PillGroup bind:value={form.revision_rating} options={RATING_OPTIONS} />
				</Field>
			</div>
		</section>

		<!-- ===== الواجب · الأدب · نقاط ===== -->
		<section
			class="space-y-3 rounded-3xl border border-outline-variant/15 bg-surface-container-lowest p-3.5 shadow-card"
		>
			<Field label="الواجب القادم" icon="assignment">
				<input
					bind:value={form.homework}
					placeholder="مثال: حفظ نصف صفحة"
					class="w-full rounded-xl bg-surface-container-low px-3 py-2.5 text-sm text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none focus:ring-2 focus:ring-primary/20"
				/>
			</Field>

			<Field label="الأدب" icon="volunteer_activism">
				<PillGroup bind:value={form.attitude} options={ATTITUDE_OPTIONS} />
			</Field>

			<!-- Free entry, positive or negative: the institute asked for points to be
			     added *and* deducted rather than picked from a fixed list. The chips are
			     shortcuts, not the only way in. -->
			<Field label="نقاط إضافية / حسم" icon="star" hint="(بالسالب للحسم)">
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
						{#each ADDED_POINTS_OPTIONS as v (v)}
							<button
								type="button"
								onclick={() => (form.added_points = v)}
								class={'rounded-full border px-3 py-1 text-[11px] font-bold transition active:scale-95 ' +
									((form.added_points ?? 0) === v
										? 'border-primary bg-primary text-on-primary'
										: 'border-outline-variant/30 bg-surface-container-low text-on-surface-variant')}
							>
								{v === 0 ? 'لا شيء' : `+${v}`}
							</button>
						{/each}
						{#each [-5, -10] as v (v)}
							<button
								type="button"
								onclick={() => (form.added_points = v)}
								class={'rounded-full border px-3 py-1 text-[11px] font-bold transition active:scale-95 ' +
									((form.added_points ?? 0) === v
										? 'border-error bg-error text-on-error'
										: 'border-outline-variant/30 bg-surface-container-low text-error')}
							>
								{v}
							</button>
						{/each}
					</div>
				</div>
			</Field>
		</section>

		<!-- ===== ملاحظات وصعوبات — collapsed unless used ===== -->
		<section
			class="rounded-3xl border border-outline-variant/15 bg-surface-container-lowest shadow-card"
		>
			<button
				type="button"
				onclick={() => (extrasOpen = !extrasOpen)}
				class="flex w-full items-center gap-2 px-3.5 py-3 text-right"
			>
				<Icon name="edit_note" class="text-base text-primary" />
				<span class="flex-1 text-[13px] font-bold text-on-surface-variant">ملاحظات وصعوبات</span>
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
					<Field label="ملاحظات" icon="edit_note">
						<textarea
							bind:value={form.notes}
							rows="2"
							placeholder="اكتب ملاحظاتك هنا…"
							class="w-full resize-none rounded-xl bg-surface-container-low p-3 text-sm text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none focus:ring-2 focus:ring-primary/20"
						></textarea>
					</Field>

					<Field label="ملاحظات الصعوبات" icon="report">
						<input
							bind:value={form.problems}
							placeholder="مثال: ضعف في مخارج الحروف"
							class="w-full rounded-xl bg-surface-container-low px-3 py-2.5 text-sm text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none focus:ring-2 focus:ring-primary/20"
						/>
					</Field>

					{#if problemsByLevel.length > 0}
						<Field label="الصعوبات المحددة" icon="label">
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
						</Field>
					{/if}
				</div>
			{/if}
		</section>
		<!-- ===== استدعاء ولي الأمر ===== -->
		<button
			type="button"
			onclick={() => (summonOpen = true)}
			class="flex w-full items-center justify-center gap-2 rounded-3xl border border-error/25 bg-error/5 py-3.5 text-[13px] font-bold text-error active:scale-[0.98]"
		>
			<Icon name="groups" class="text-lg" /> طلب استدعاء ولي الأمر
		</button>
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
