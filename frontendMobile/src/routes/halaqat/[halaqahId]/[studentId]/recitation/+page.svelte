<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import {
		ApiError,
		auth,
		type Attitude,
		type DailyRecord,
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
		serializeRevisions,
		type RevisionRow
	} from '$lib/labels';
	import { arabicNum, formatDateArabic, todayIso } from '$lib/utils';
	import TopBar from '$lib/components/TopBar.svelte';
	import Spinner from '$lib/components/Spinner.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import Field from '$lib/components/Field.svelte';
	import PillGroup from '$lib/components/PillGroup.svelte';
	import Icon from '$lib/components/Icon.svelte';

	const halaqahId = $derived($page.params.halaqahId ?? '');
	const studentId = $derived($page.params.studentId ?? '');
	const date = $derived($page.url.searchParams.get('date') || todayIso());

	let status = $state<'loading' | 'ready' | 'error'>('loading');
	let error = $state('');
	let student = $state<Student | null>(null);
	let settings = $state<ScoringSettings | null>(null);
	let record = $state<DailyRecord | null>(null);
	let allProblems = $state<Problem[]>([]);

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
				rating: form.rating,
				revision_rating: form.revision_rating,
				attitude: form.attitude,
				added_points: form.added_points ?? 0
			},
			settings
		)
	);

	onMount(load);

	async function load() {
		if (!auth.teacher) return;
		status = 'loading';
		try {
			const [s, rec, scoring, probs] = await Promise.all([
				repo.getStudent(studentId),
				repo.getDayRecord(studentId, date),
				repo.getScoring(),
				repo.listProblems()
			]);
			student = s;
			settings = scoring;
			allProblems = probs;
			record = rec;
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
			}
			status = 'ready';
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'تعذّر تحميل البيانات';
			status = 'error';
		}
	}

	function orNull(s: string): string | null {
		const t = s.trim();
		return t === '' ? null : t;
	}
	function numOrNull(s: string): number | null {
		const t = s.trim();
		if (t === '') return null;
		const n = Number(t);
		return Number.isFinite(n) ? n : null;
	}

	function addRevision() {
		revisions = [...revisions, { part: 1, half: 1, success: true }];
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
		saving = true;
		feedback = null;
		// Everything except attendance (present/excused) — that is set on the الحضور tab.
		const fields = {
			exam_from: numOrNull(form.exam_from),
			exam_to: numOrNull(form.exam_to),
			exam_total: numOrNull(form.exam_total),
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
			setTimeout(() => goto(`/halaqat/${halaqahId}`), 600);
		} catch (e) {
			flash('err', e instanceof ApiError ? e.message : 'تعذّر حفظ السجل');
			saving = false;
		}
	}
</script>

<TopBar
	title={student?.full_name ?? 'الطالب'}
	subtitle="التسميع والمراجعة — {formatDateArabic(date)}"
	backHref={`/halaqat/${halaqahId}`}
/>

<main class="mx-auto max-w-2xl space-y-4 px-4 pb-32 pt-20" dir="rtl">
	{#if status === 'loading'}
		<Spinner label="جارٍ التحميل…" />
	{:else if status === 'error'}
		<EmptyState icon="error" title="حدث خطأ" hint={error} />
	{:else}
		<!-- Total points -->
		<section
			class="flex items-center justify-between rounded-[2rem] border border-outline-variant/15 bg-primary/5 px-5 py-4 shadow-card"
		>
			<div class="flex flex-col">
				<span class="text-[11px] font-medium text-on-surface-variant/70">مجموع نقاط اليوم</span>
				<div class="flex flex-wrap gap-2 pt-1 text-[10px] text-on-surface-variant/60">
					<span>حضور {scores.present}</span>
					<span>· تسميع {scores.exam}</span>
					<span>· مراجعة {scores.revision}</span>
					<span>· أدب {scores.attitude}</span>
					<span>· إضافية {form.added_points ?? 0}</span>
				</div>
			</div>
			<div class="flex items-baseline gap-1 text-primary">
				<span class="font-jakarta text-3xl font-bold leading-none">{scores.total}</span>
				<span class="text-xs font-medium">نقطة</span>
			</div>
		</section>

		<!-- التسميع -->
		<section
			class="space-y-5 rounded-[2rem] border border-outline-variant/15 bg-surface-container-lowest p-5 shadow-card"
		>
			<Field label="التسميع" icon="menu_book" hint="(من / إلى / المجموع)">
				<div class="grid grid-cols-3 gap-2">
					<input
						bind:value={form.exam_from}
						inputmode="numeric"
						placeholder="من"
						class="rounded-2xl bg-surface-container-low px-3 py-2.5 text-center text-sm text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none focus:ring-2 focus:ring-primary/20"
					/>
					<input
						bind:value={form.exam_to}
						inputmode="numeric"
						placeholder="إلى"
						class="rounded-2xl bg-surface-container-low px-3 py-2.5 text-center text-sm text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none focus:ring-2 focus:ring-primary/20"
					/>
					<input
						bind:value={form.exam_total}
						inputmode="numeric"
						placeholder="المجموع"
						class="rounded-2xl bg-surface-container-low px-3 py-2.5 text-center text-sm text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none focus:ring-2 focus:ring-primary/20"
					/>
				</div>
			</Field>

			<Field label="التقدير" icon="grade">
				<PillGroup bind:value={form.rating} options={RATING_OPTIONS} />
			</Field>
		</section>

		<!-- المراجعة -->
		<section
			class="space-y-4 rounded-[2rem] border border-outline-variant/15 bg-surface-container-lowest p-5 shadow-card"
		>
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-1.5">
					<Icon name="history_edu" class="text-base text-primary" />
					<span class="text-[13px] font-bold text-on-surface-variant">المراجعة</span>
					{#if revisions.length > 0}
						<span class="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-bold text-primary"
							>{arabicNum(revisions.length)}</span
						>
					{/if}
				</div>
				<button
					onclick={addRevision}
					class="flex items-center gap-1 rounded-full bg-primary/10 px-3 py-1.5 text-[11px] font-bold text-primary active:scale-95"
				>
					<Icon name="add" class="text-sm" /> إضافة مراجعة
				</button>
			</div>

			{#if revisions.length === 0}
				<p
					class="rounded-2xl bg-surface-container-low px-4 py-6 text-center text-xs text-on-surface-variant/60"
				>
					لا توجد مراجعات. اضغط «إضافة مراجعة» لإضافة جزء.
				</p>
			{:else}
				<div class="space-y-3">
					{#each revisions as rev, i (i)}
						<div
							class="space-y-3 rounded-2xl border border-outline-variant/20 bg-surface-container-low p-3"
						>
							<div class="flex items-center justify-between">
								<span class="text-[11px] font-bold text-on-surface-variant/70"
									>مراجعة {arabicNum(i + 1)}</span
								>
								<button
									onclick={() => removeRevision(i)}
									class="rounded-full p-1 text-error active:scale-90"
									aria-label="حذف"
								>
									<Icon name="delete" class="text-base" />
								</button>
							</div>
							<!-- part -->
							<div class="flex items-center gap-2">
								<span class="w-12 text-[12px] font-medium text-on-surface-variant">الجزء</span>
								<select
									bind:value={rev.part}
									class="flex-1 rounded-xl border border-outline-variant/30 bg-surface-container-lowest px-3 py-2 text-sm text-on-surface focus:outline-none focus:ring-2 focus:ring-primary/20"
								>
									{#each QURAN_PARTS as p (p)}
										<option value={p}>الجزء {arabicNum(p)}</option>
									{/each}
								</select>
							</div>
							<!-- half -->
							<div class="flex items-center gap-2">
								<span class="w-12 text-[12px] font-medium text-on-surface-variant">النصف</span>
								<select
									bind:value={rev.half}
									class="flex-1 rounded-xl border border-outline-variant/30 bg-surface-container-lowest px-3 py-2 text-sm text-on-surface focus:outline-none focus:ring-2 focus:ring-primary/20"
								>
									{#each HALF_OPTIONS as h (h.value)}
										<option value={h.value}>{h.label}</option>
									{/each}
								</select>
							</div>
							<!-- status -->
							<div class="grid grid-cols-2 gap-2">
								<button
									type="button"
									onclick={() => (rev.success = true)}
									class={'flex items-center justify-center gap-1 rounded-full border py-2 text-xs font-bold transition active:scale-95 ' +
										(rev.success
											? 'border-emerald-500 bg-emerald-500 text-white'
											: 'border-outline-variant/30 bg-surface-container-lowest text-on-surface-variant')}
								>
									<Icon name="check_circle" class="text-sm" filled={rev.success} /> نجح
								</button>
								<button
									type="button"
									onclick={() => (rev.success = false)}
									class={'flex items-center justify-center gap-1 rounded-full border py-2 text-xs font-bold transition active:scale-95 ' +
										(!rev.success
											? 'border-error bg-error text-on-error'
											: 'border-outline-variant/30 bg-surface-container-lowest text-on-surface-variant')}
								>
									<Icon name="cancel" class="text-sm" filled={!rev.success} /> أخفق
								</button>
							</div>
						</div>
					{/each}
				</div>
			{/if}

			<div class="border-t border-outline-variant/15 pt-4">
				<Field label="تقييم المراجعة" icon="grade">
					<PillGroup bind:value={form.revision_rating} options={RATING_OPTIONS} />
				</Field>
			</div>
		</section>

		<!-- الواجب والأدب -->
		<section
			class="space-y-5 rounded-[2rem] border border-outline-variant/15 bg-surface-container-lowest p-5 shadow-card"
		>
			<Field label="الواجب القادم" icon="assignment">
				<input
					bind:value={form.homework}
					placeholder="مثال: حفظ نصف صفحة"
					class="w-full rounded-2xl bg-surface-container-low px-4 py-3 text-sm text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none focus:ring-2 focus:ring-primary/20"
				/>
			</Field>

			<Field label="الأدب" icon="volunteer_activism">
				<PillGroup bind:value={form.attitude} options={ATTITUDE_OPTIONS} />
			</Field>
		</section>

		<!-- نقاط إضافية وملاحظات -->
		<section
			class="space-y-5 rounded-[2rem] border border-outline-variant/15 bg-surface-container-lowest p-5 shadow-card"
		>
			<Field label="نقاط إضافية" icon="star">
				<PillGroup
					bind:value={form.added_points}
					allowNull={false}
					options={ADDED_POINTS_OPTIONS.map((v) => ({
						value: v,
						label: v === 0 ? 'لا شيء' : `+${v}`
					}))}
				/>
			</Field>

			<Field label="ملاحظات" icon="edit_note">
				<textarea
					bind:value={form.notes}
					rows="3"
					placeholder="اكتب ملاحظاتك هنا…"
					class="w-full resize-none rounded-2xl bg-surface-container-low p-4 text-sm text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none focus:ring-2 focus:ring-primary/20"
				></textarea>
			</Field>
		</section>

		<!-- الصعوبات -->
		<section
			class="space-y-5 rounded-[2rem] border border-outline-variant/15 bg-surface-container-lowest p-5 shadow-card"
		>
			<Field label="ملاحظات الصعوبات" icon="report">
				<input
					bind:value={form.problems}
					placeholder="مثال: ضعف في مخارج الحروف"
					class="w-full rounded-2xl bg-surface-container-low px-4 py-3 text-sm text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none focus:ring-2 focus:ring-primary/20"
				/>
			</Field>

			{#if problemsByLevel.length > 0}
				<Field label="الصعوبات المحددة" icon="label">
					<div class="space-y-3">
						{#each problemsByLevel as group}
							<div>
								<p class="mb-1.5 text-[11px] font-semibold text-on-surface-variant/70">
									{group.levelName}
								</p>
								<div class="flex flex-wrap gap-2">
									{#each group.items as p (p.id)}
										{@const selected = form.problem_ids.includes(p.id)}
										<button
											type="button"
											onclick={() => toggleProblem(p.id)}
											class={'rounded-full border px-3 py-1 text-xs font-medium transition active:scale-95 ' +
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
		</section>
	{/if}
</main>

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
			<Icon name="progress_activity" class="animate-spin text-3xl" />
		{:else}
			<Icon name="check" class="text-3xl" />
		{/if}
	</button>
{/if}
