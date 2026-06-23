<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import {
		ApiError,
		auth,
		dailyRecordsApi,
		scoringApi,
		studentsApi,
		type DailyRecord,
		type Attitude,
		type ScoringSettings,
		type Student
	} from '$lib/api';
	import { ADDED_POINTS_OPTIONS, ATTITUDE_OPTIONS, computeScores } from '$lib/labels';
	import { formatDateArabic, todayIso } from '$lib/utils';
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

	let form = $state({
		present: true,
		excused: false,
		homework: '',
		attitude: null as number | null,
		added_points: 0 as number | null,
		notes: ''
	});

	let saving = $state(false);
	let feedback = $state<{ type: 'ok' | 'err'; text: string } | null>(null);
	let feedbackTimer: ReturnType<typeof setTimeout> | undefined;

	// Live total uses this page's fields plus the recitation fields already saved.
	const scores = $derived(
		computeScores(
			{
				present: form.present,
				excused: form.excused,
				rating: record?.rating ?? null,
				revision_rating: record?.revision_rating ?? null,
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
			const [s, recs, scoring] = await Promise.all([
				studentsApi.get(studentId),
				dailyRecordsApi.list({ student_id: studentId, record_date: date, limit: 1 }),
				scoringApi.get().catch(() => null)
			]);
			student = s;
			settings = scoring;
			record = recs.items[0] ?? null;
			if (record) {
				form = {
					present: record.present,
					excused: record.excused,
					homework: record.homework ?? '',
					attitude: record.attitude,
					added_points: record.added_points,
					notes: record.notes ?? ''
				};
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

	function flash(type: 'ok' | 'err', text: string) {
		feedback = { type, text };
		clearTimeout(feedbackTimer);
		feedbackTimer = setTimeout(() => (feedback = null), 2400);
	}

	async function save() {
		if (saving || !auth.teacher) return;
		saving = true;
		feedback = null;
		const present = form.present;
		const excused = !present && form.excused;
		// Only the attendance-tab fields; recitation fields are left untouched.
		const fields = {
			present,
			excused,
			homework: present ? orNull(form.homework) : null,
			attitude: present ? ((form.attitude as Attitude | null) ?? null) : null,
			added_points: form.added_points ?? 0,
			notes: orNull(form.notes)
		};
		try {
			if (record) {
				await dailyRecordsApi.update(record.id, fields);
			} else {
				await dailyRecordsApi.create({
					student_id: studentId,
					teacher_id: auth.teacher.id,
					halaqah_id: halaqahId,
					record_date: date,
					...fields
				});
			}
			flash('ok', 'تم حفظ الحضور');
			setTimeout(() => goto(`/halaqat/${halaqahId}`), 600);
		} catch (e) {
			flash('err', e instanceof ApiError ? e.message : 'تعذّر حفظ السجل');
			saving = false;
		}
	}
</script>

<TopBar
	title={student?.full_name ?? 'الطالب'}
	subtitle="الحضور — {formatDateArabic(date)}"
	backHref={`/halaqat/${halaqahId}`}
/>

<main class="mx-auto max-w-2xl space-y-4 px-4 pb-32 pt-20" dir="rtl">
	{#if status === 'loading'}
		<Spinner label="جارٍ التحميل…" />
	{:else if status === 'error'}
		<EmptyState icon="error" title="حدث خطأ" hint={error} />
	{:else}
		<!-- Attendance + total -->
		<section
			class="space-y-4 rounded-[2rem] border border-outline-variant/15 bg-surface-container-lowest p-5 shadow-card"
		>
			<Field label="الحضور" icon="how_to_reg">
				<div class="grid grid-cols-3 gap-2">
					<button
						type="button"
						onclick={() => {
							form.present = true;
							form.excused = false;
						}}
						class={'rounded-full border py-2.5 text-xs font-bold transition active:scale-95 ' +
							(form.present
								? 'border-primary bg-primary text-on-primary shadow-sm'
								: 'border-outline-variant/30 bg-surface-container-low text-on-surface-variant')}
					>
						حاضر
					</button>
					<button
						type="button"
						onclick={() => {
							form.present = false;
							form.excused = true;
						}}
						class={'rounded-full border py-2.5 text-xs font-bold transition active:scale-95 ' +
							(!form.present && form.excused
								? 'border-[#1a73e8] bg-[#1a73e8] text-white shadow-sm'
								: 'border-outline-variant/30 bg-surface-container-low text-on-surface-variant')}
					>
						أذن
					</button>
					<button
						type="button"
						onclick={() => {
							form.present = false;
							form.excused = false;
						}}
						class={'rounded-full border py-2.5 text-xs font-bold transition active:scale-95 ' +
							(!form.present && !form.excused
								? 'border-error bg-error text-on-error shadow-sm'
								: 'border-outline-variant/30 bg-surface-container-low text-on-surface-variant')}
					>
						غائب
					</button>
				</div>
			</Field>

			<div class="flex items-center justify-between rounded-[1.5rem] bg-primary/5 px-5 py-4">
				<div class="flex flex-col">
					<span class="text-[11px] font-medium text-on-surface-variant/70">مجموع نقاط اليوم</span>
					<div class="flex flex-wrap gap-2 pt-1 text-[10px] text-on-surface-variant/60">
						<span>حضور {scores.present}</span>
						<span>· أدب {scores.attitude}</span>
						<span>· إضافية {form.added_points ?? 0}</span>
						{#if scores.exam > 0 || scores.revision > 0}
							<span>· تسميع/مراجعة {scores.exam + scores.revision}</span>
						{/if}
					</div>
				</div>
				<div class="flex items-baseline gap-1 text-primary">
					<span class="font-jakarta text-3xl font-bold leading-none">{scores.total}</span>
					<span class="text-xs font-medium">نقطة</span>
				</div>
			</div>
		</section>

		{#if form.present}
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
		{/if}

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
