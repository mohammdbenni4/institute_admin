<script lang="ts">
	import PageHeader from '$lib/components/shared/PageHeader.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import Input from '$lib/components/ui/Input.svelte';
	import Label from '$lib/components/ui/Label.svelte';
	import { ApiError, scoringApi, type ScoringSettings } from '$lib/api';
	import { Save, SlidersHorizontal } from '@lucide/svelte';

	let form = $state<ScoringSettings>({
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
		excused_points: 0
	});
	let loading = $state(true);
	let saving = $state(false);
	let error = $state('');
	let saved = $state(false);

	async function load() {
		loading = true;
		try {
			form = await scoringApi.get();
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'تعذّر تحميل الإعدادات.';
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		load();
	});

	async function save() {
		if (saving) return;
		saving = true;
		error = '';
		saved = false;
		try {
			const body = Object.fromEntries(
				Object.entries(form).map(([k, v]) => [k, Number(v)])
			) as unknown as ScoringSettings;
			form = await scoringApi.update(body);
			saved = true;
			setTimeout(() => (saved = false), 2500);
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'تعذّر حفظ الإعدادات.';
		} finally {
			saving = false;
		}
	}

	const ratingFields = [
		{ key: 'rating_4_points', label: 'ممتاز (4)' },
		{ key: 'rating_3_points', label: 'جيد جداً (3)' },
		{ key: 'rating_2_points', label: 'جيد (2)' },
		{ key: 'rating_1_points', label: 'ضعيف (1)' }
	] as const;

	const revisionFields = [
		{ key: 'revision_4_points', label: 'ممتاز (4)' },
		{ key: 'revision_3_points', label: 'جيد جداً (3)' },
		{ key: 'revision_2_points', label: 'جيد (2)' },
		{ key: 'revision_1_points', label: 'ضعيف (1)' }
	] as const;

	const attitudeFields = [
		{ key: 'attitude_3_points', label: 'مؤدب (3)' },
		{ key: 'attitude_2_points', label: 'متوسط (2)' },
		{ key: 'attitude_1_points', label: 'مشاغب (1)' }
	] as const;
</script>

<div class="page-container">
	<PageHeader
		title="إعدادات النقاط"
		subtitle="تخصيص أوزان بطاقة النقاط للمعهد"
		breadcrumbs={[{ label: 'لوحة التحكم' }, { label: 'إعدادات النقاط' }]}
	>
		{#snippet actions()}
			<Button onclick={save} disabled={saving || loading}>
				<Save class="h-4 w-4" />{saving ? 'جارٍ الحفظ…' : 'حفظ'}
			</Button>
		{/snippet}
	</PageHeader>

	{#if error}
		<p class="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>
	{/if}
	{#if saved}
		<p class="rounded-lg bg-success/10 px-3 py-2 text-sm text-success">تم حفظ الإعدادات بنجاح.</p>
	{/if}

	<div class="glass-card p-5">
		<div class="mb-4 flex items-center gap-2">
			<SlidersHorizontal class="h-5 w-5 text-primary" />
			<p class="text-sm text-muted-foreground">
				تُطبَّق هذه الأوزان عند تسجيل السجلات الجديدة. السجلات السابقة تحتفظ بنقاطها.
			</p>
		</div>

		<div class="space-y-6">
			<!-- الحضور: نقاط الحضور + الغياب والعذر في صف واحد -->
			<div>
				<h3 class="mb-2 font-bold text-foreground">الحضور</h3>
				<div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
					<div class="space-y-2">
						<Label for="present">نقاط الحضور</Label>
						<Input id="present" type="number" min="0" bind:value={form.present_points} />
					</div>
					<div class="space-y-2">
						<Label for="excused_points">أذن (غياب بعذر)</Label>
						<Input id="excused_points" type="number" min="0" bind:value={form.excused_points} />
					</div>
					<div class="space-y-2">
						<Label for="absent_points">غياب (بلا عذر)</Label>
						<Input id="absent_points" type="number" min="0" bind:value={form.absent_points} />
					</div>
				</div>
			</div>

			<!-- التقدير: السماع والاختبار -->
			<div>
				<h3 class="mb-2 font-bold text-foreground">التقدير (التسميع والاختبار)</h3>
				<div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
					{#each ratingFields as f (f.key)}
						<div class="space-y-2">
							<Label for={f.key}>{f.label}</Label>
							<Input id={f.key} type="number" min="0" bind:value={form[f.key]} />
						</div>
					{/each}
				</div>
			</div>

			<!-- المراجعة -->
			<div>
				<h3 class="mb-2 font-bold text-foreground">المراجعة</h3>
				<div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
					{#each revisionFields as f (f.key)}
						<div class="space-y-2">
							<Label for={f.key}>{f.label}</Label>
							<Input id={f.key} type="number" min="0" bind:value={form[f.key]} />
						</div>
					{/each}
				</div>
			</div>

			<!-- الأدب -->
			<div>
				<h3 class="mb-2 font-bold text-foreground">الأدب</h3>
				<div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
					{#each attitudeFields as f (f.key)}
						<div class="space-y-2">
							<Label for={f.key}>{f.label}</Label>
							<Input id={f.key} type="number" min="0" bind:value={form[f.key]} />
						</div>
					{/each}
				</div>
			</div>
		</div>
	</div>
</div>
