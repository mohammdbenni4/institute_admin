<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import {
		ApiError,
		auth,
		dailyRecordsApi,
		scoringApi,
		studentsApi,
		type DailyRecord,
		type DailyRecordCreate,
		type Rating,
		type Attitude,
		type ScoringSettings,
		type Student
	} from '$lib/api';
	import {
		ADDED_POINTS_OPTIONS,
		ATTITUDE_OPTIONS,
		RATING_OPTIONS,
		computeScores,
		recordSummary
	} from '$lib/labels';
	import { addDays, formatDateArabic, formatDateShort, todayIso, whatsappLink } from '$lib/utils';
	import TopBar from '$lib/components/TopBar.svelte';
	import Spinner from '$lib/components/Spinner.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import Field from '$lib/components/Field.svelte';
	import PillGroup from '$lib/components/PillGroup.svelte';
	import Icon from '$lib/components/Icon.svelte';

	const halaqahId = $derived($page.params.halaqahId ?? '');
	const studentId = $derived($page.params.studentId ?? '');

	interface FormState {
		present: boolean;
		exam_from: string;
		exam_to: string;
		exam_total: string;
		rating: number | null;
		revision_lesson: string;
		revision_rating: number | null;
		homework: string;
		problems: string;
		attitude: number | null;
		added_points: number | null;
		notes: string;
	}

	function blankForm(): FormState {
		return {
			present: true,
			exam_from: '',
			exam_to: '',
			exam_total: '',
			rating: null,
			revision_lesson: '',
			revision_rating: null,
			homework: '',
			problems: '',
			attitude: null,
			added_points: 0,
			notes: ''
		};
	}

	function toForm(r: DailyRecord): FormState {
		return {
			present: r.present,
			exam_from: r.exam_from?.toString() ?? '',
			exam_to: r.exam_to?.toString() ?? '',
			exam_total: r.exam_total?.toString() ?? '',
			rating: r.rating,
			revision_lesson: r.revision_lesson ?? '',
			revision_rating: r.revision_rating,
			homework: r.homework ?? '',
			problems: r.problems ?? '',
			attitude: r.attitude,
			added_points: r.added_points,
			notes: r.notes ?? ''
		};
	}

	const today = todayIso();

	let status = $state<'loading' | 'ready' | 'error'>('loading');
	let error = $state('');
	let student = $state<Student | null>(null);
	let records = $state<DailyRecord[]>([]);
	let settings = $state<ScoringSettings | null>(null);

	let date = $state(today);
	let form = $state<FormState>(blankForm());
	let editingId = $state<string | null>(null);

	let saving = $state(false);
	let feedback = $state<{ type: 'ok' | 'err'; text: string } | null>(null);
	let feedbackTimer: ReturnType<typeof setTimeout> | undefined;

	// The record on the selected date drives create-vs-edit mode and prefill.
	$effect(() => {
		const rec = records.find((r) => r.record_date === date) ?? null;
		editingId = rec?.id ?? null;
		form = rec ? toForm(rec) : blankForm();
	});

	const scores = $derived(
		computeScores(
			{
				present: form.present,
				rating: form.rating,
				attitude: form.attitude,
				added_points: form.added_points ?? 0
			},
			settings
		)
	);

	const waLink = $derived(
		whatsappLink(
			student?.father_number,
			`السلام عليكم ورحمة الله، بخصوص الطالب ${student?.full_name ?? ''} في حلقة القرآن.`
		)
	);

	onMount(load);

	async function load() {
		if (!auth.teacher) return;
		status = 'loading';
		try {
			const [s, history, scoring] = await Promise.all([
				studentsApi.get(studentId),
				dailyRecordsApi.list({ student_id: studentId, limit: 90 }),
				scoringApi.get().catch(() => null)
			]);
			student = s;
			records = history.items;
			settings = scoring;
			status = 'ready';
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'تعذّر تحميل بيانات الطالب';
			status = 'error';
		}
	}

	async function refreshHistory() {
		const history = await dailyRecordsApi.list({ student_id: studentId, limit: 90 });
		records = history.items;
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

	function payloadBase() {
		const present = form.present;
		return {
			present,
			record_date: date,
			added_points: form.added_points ?? 0,
			notes: orNull(form.notes),
			exam_from: present ? numOrNull(form.exam_from) : null,
			exam_to: present ? numOrNull(form.exam_to) : null,
			exam_total: present ? numOrNull(form.exam_total) : null,
			rating: present ? ((form.rating as Rating | null) ?? null) : null,
			revision_lesson: present ? orNull(form.revision_lesson) : null,
			revision_rating: present ? ((form.revision_rating as Rating | null) ?? null) : null,
			homework: present ? orNull(form.homework) : null,
			problems: present ? orNull(form.problems) : null,
			attitude: present ? ((form.attitude as Attitude | null) ?? null) : null
		};
	}

	function flash(type: 'ok' | 'err', text: string) {
		feedback = { type, text };
		clearTimeout(feedbackTimer);
		feedbackTimer = setTimeout(() => (feedback = null), 2800);
	}

	async function save() {
		if (saving || !auth.teacher) return;
		saving = true;
		feedback = null;
		try {
			const base = payloadBase();
			if (editingId) {
				await dailyRecordsApi.update(editingId, base);
			} else {
				const body: DailyRecordCreate = {
					student_id: studentId,
					teacher_id: auth.teacher.id,
					halaqah_id: halaqahId,
					...base
				};
				await dailyRecordsApi.create(body);
			}
			await refreshHistory();
			flash('ok', editingId ? 'تم تحديث السجل' : 'تم حفظ السجل');
		} catch (e) {
			flash('err', e instanceof ApiError ? e.message : 'تعذّر حفظ السجل');
		} finally {
			saving = false;
		}
	}

	async function remove() {
		if (!editingId || saving) return;
		if (!confirm('حذف السجل اليومي لهذا التاريخ؟')) return;
		saving = true;
		try {
			await dailyRecordsApi.remove(editingId);
			await refreshHistory();
			flash('ok', 'تم حذف السجل');
		} catch (e) {
			flash('err', e instanceof ApiError ? e.message : 'تعذّر حذف السجل');
		} finally {
			saving = false;
		}
	}

	function shiftDay(delta: number) {
		const next = addDays(date, delta);
		if (next > today) return;
		date = next;
	}

	const pastRecords = $derived(records.filter((r) => r.record_date !== date));
</script>

<TopBar
	title={student?.full_name ?? 'الطالب'}
	subtitle="السجل اليومي"
	backHref={`/halaqat/${halaqahId}`}
>
	{#snippet actions()}
		{#if waLink}
			<a
				href={waLink}
				target="_blank"
				rel="noopener noreferrer"
				class="rounded-full p-2 transition hover:bg-white/10 active:scale-95"
				aria-label="تواصل مع الأهل"
			>
				<Icon name="chat" />
			</a>
		{/if}
		{#if editingId}
			<button
				onclick={remove}
				class="rounded-full p-2 transition hover:bg-white/10 active:scale-95"
				aria-label="حذف السجل"
			>
				<Icon name="delete" />
			</button>
		{/if}
	{/snippet}
</TopBar>

<main class="mx-auto max-w-2xl space-y-4 px-4 pb-32 pt-20" dir="rtl">
	{#if status === 'loading'}
		<Spinner label="جارٍ التحميل…" />
	{:else if status === 'error'}
		<EmptyState icon="error" title="حدث خطأ" hint={error} />
	{:else}
		<!-- Date selector -->
		<section
			class="flex items-center justify-between rounded-[2rem] border border-white/60 bg-surface-container-lowest p-3 shadow-sm"
		>
			<button
				onclick={() => shiftDay(-1)}
				class="flex h-10 w-10 items-center justify-center rounded-full bg-surface-container-low text-primary active:scale-95"
				aria-label="اليوم السابق"
			>
				<Icon name="chevron_right" />
			</button>
			<label class="flex cursor-pointer flex-col items-center">
				<span class="text-[15px] font-bold text-on-surface">{formatDateArabic(date)}</span>
				<span class="mt-0.5 flex items-center gap-1 text-[10px] text-primary">
					<Icon name="calendar_month" class="text-sm" /> تغيير التاريخ
				</span>
				<input
					type="date"
					bind:value={date}
					max={today}
					class="sr-only"
					aria-label="اختيار التاريخ"
				/>
			</label>
			<button
				onclick={() => shiftDay(1)}
				disabled={date >= today}
				class="flex h-10 w-10 items-center justify-center rounded-full bg-surface-container-low text-primary active:scale-95 disabled:opacity-30"
				aria-label="اليوم التالي"
			>
				<Icon name="chevron_left" />
			</button>
		</section>

		<!-- Attendance + total -->
		<section
			class="space-y-4 rounded-[2rem] border border-white/60 bg-surface-container-lowest p-5 shadow-card"
		>
			<Field label="الحضور" icon="how_to_reg">
				<div class="grid grid-cols-2 gap-2">
					<button
						type="button"
						onclick={() => (form.present = true)}
						class={'rounded-full border py-2.5 text-xs font-bold transition active:scale-95 ' +
							(form.present
								? 'border-primary bg-primary text-on-primary shadow-sm'
								: 'border-outline-variant/30 bg-white/70 text-on-surface-variant')}
					>
						حاضر
					</button>
					<button
						type="button"
						onclick={() => (form.present = false)}
						class={'rounded-full border py-2.5 text-xs font-bold transition active:scale-95 ' +
							(!form.present
								? 'border-error bg-error text-on-error shadow-sm'
								: 'border-outline-variant/30 bg-white/70 text-on-surface-variant')}
					>
						غائب
					</button>
				</div>
			</Field>

			<div class="flex items-center justify-between rounded-[1.5rem] bg-primary/5 px-5 py-4">
				<div class="flex flex-col">
					<span class="text-[11px] font-medium text-on-surface-variant/70">مجموع النقاط</span>
					<div class="flex flex-wrap gap-2 pt-1 text-[10px] text-on-surface-variant/60">
						<span>حضور {scores.present}</span>
						<span>· تسميع {scores.exam}</span>
						<span>· أدب {scores.attitude}</span>
						<span>· إضافية {form.added_points ?? 0}</span>
					</div>
				</div>
				<div class="flex items-baseline gap-1 text-primary">
					<span class="font-jakarta text-3xl font-bold leading-none">{scores.total}</span>
					<span class="text-xs font-medium">نقطة</span>
				</div>
			</div>
		</section>

		{#if form.present}
			<!-- Assessment -->
			<section
				class="space-y-5 rounded-[2rem] border border-white/60 bg-surface-container-lowest p-5 shadow-card"
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

				<Field label="درس المراجعة" icon="history_edu">
					<input
						bind:value={form.revision_lesson}
						placeholder="مثال: سورة البقرة ٢٠ صفحة"
						class="w-full rounded-2xl bg-surface-container-low px-4 py-3 text-sm text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none focus:ring-2 focus:ring-primary/20"
					/>
					<div class="pt-2">
						<PillGroup bind:value={form.revision_rating} options={RATING_OPTIONS} />
					</div>
				</Field>

				<Field label="الواجب القادم" icon="assignment">
					<input
						bind:value={form.homework}
						placeholder="مثال: حفظ نصف صفحة"
						class="w-full rounded-2xl bg-surface-container-low px-4 py-3 text-sm text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none focus:ring-2 focus:ring-primary/20"
					/>
				</Field>

				<Field label="الصعوبات" icon="report">
					<input
						bind:value={form.problems}
						placeholder="مثال: ضعف في مخارج الحروف"
						class="w-full rounded-2xl bg-surface-container-low px-4 py-3 text-sm text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none focus:ring-2 focus:ring-primary/20"
					/>
				</Field>

				<Field label="الأدب" icon="volunteer_activism">
					<PillGroup bind:value={form.attitude} options={ATTITUDE_OPTIONS} />
				</Field>
			</section>
		{/if}

		<!-- Points + notes (always available) -->
		<section
			class="space-y-5 rounded-[2rem] border border-white/60 bg-surface-container-lowest p-5 shadow-card"
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

		<!-- History -->
		<section class="space-y-3">
			<div class="flex items-center gap-2 px-2">
				<Icon name="history" class="text-primary" />
				<h2 class="text-[13px] font-bold text-on-surface-variant">السجلات السابقة</h2>
			</div>
			{#if pastRecords.length === 0}
				<p class="px-2 text-xs text-on-surface-variant/50">لا توجد سجلات سابقة.</p>
			{:else}
				<ul class="space-y-2">
					{#each pastRecords as r (r.id)}
						<li>
							<button
								onclick={() => (date = r.record_date)}
								class="flex w-full items-center justify-between rounded-2xl border border-outline-variant/10 bg-surface-container-lowest p-3.5 text-right shadow-sm transition active:scale-[0.99]"
							>
								<div class="flex items-center gap-3">
									<div
										class={'flex h-9 w-9 items-center justify-center rounded-full ' +
											(r.present ? 'bg-primary/10 text-primary' : 'bg-error/10 text-error')}
									>
										<Icon name={r.present ? 'check' : 'close'} class="text-lg" />
									</div>
									<div class="flex flex-col">
										<span class="text-[13px] font-bold text-on-surface"
											>{formatDateShort(r.record_date)}</span
										>
										<span class="text-[11px] text-on-surface-variant/60">{recordSummary(r)}</span>
									</div>
								</div>
								<span class="flex items-center gap-1 text-xs font-bold text-primary">
									{r.total_points}
									<Icon name="star" filled class="text-sm" />
								</span>
							</button>
						</li>
					{/each}
				</ul>
			{/if}
		</section>
	{/if}
</main>

<!-- Feedback toast -->
{#if feedback}
	<div
		class={'fixed inset-x-0 bottom-28 z-50 mx-auto flex w-fit items-center gap-2 rounded-full px-4 py-2.5 text-sm font-bold text-white shadow-lg ' +
			(feedback.type === 'ok' ? 'bg-primary' : 'bg-error')}
	>
		<Icon name={feedback.type === 'ok' ? 'check_circle' : 'error'} class="text-lg" />
		{feedback.text}
	</div>
{/if}

<!-- Save FAB -->
{#if status === 'ready'}
	<button
		onclick={save}
		disabled={saving}
		class="fixed bottom-8 left-6 z-50 flex h-16 w-16 items-center justify-center rounded-full bg-brand text-white shadow-fab transition active:scale-95 disabled:opacity-70"
		aria-label={editingId ? 'تحديث السجل' : 'حفظ السجل'}
	>
		{#if saving}
			<Icon name="progress_activity" class="animate-spin text-3xl" />
		{:else}
			<Icon name="check" class="text-3xl" />
		{/if}
	</button>
{/if}
