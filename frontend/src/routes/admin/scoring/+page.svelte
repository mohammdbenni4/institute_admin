<script lang="ts">
	import PageHeader from '$lib/components/shared/PageHeader.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import Input from '$lib/components/ui/Input.svelte';
	import Label from '$lib/components/ui/Label.svelte';
	import {
		ApiError,
		scoringApi,
		scoringPresetsApi,
		type ScoringPreset,
		type ScoringSettings
	} from '$lib/api';
	import { ChevronDown, Layers, Plus, Save, SlidersHorizontal, Trash2 } from '@lucide/svelte';

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
		excused_points: 0,
		late_points: 5
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

	// ===== أنظمة التسعير المخصصة =====
	// A preset is a *complete* set of weights, so a student pinned to one is never
	// affected by later edits to the institute defaults above. Teachers assign them
	// from the app (إعدادات الحلقة); authoring them is admin-only, i.e. here.

	let presets = $state<ScoringPreset[]>([]);
	let presetsLoading = $state(true);
	let presetError = $state('');
	/** Which preset's editor is expanded — only one at a time keeps the page readable. */
	let openPresetId = $state<string | null>(null);
	/** Local edit buffers keyed by preset id, so a half-typed change never mutates the list. */
	let drafts = $state<Record<string, ScoringPreset>>({});
	let savingPresetId = $state<string | null>(null);
	let deletingId = $state<string | null>(null);
	let creating = $state(false);

	async function loadPresets() {
		presetsLoading = true;
		try {
			presets = (await scoringPresetsApi.list()).items;
			drafts = Object.fromEntries(presets.map((p) => [p.id, { ...p }]));
		} catch (e) {
			presetError = e instanceof ApiError ? e.message : 'تعذّر تحميل أنظمة التسعير.';
		} finally {
			presetsLoading = false;
		}
	}

	$effect(() => {
		loadPresets();
	});

	/** A new preset starts as a copy of the institute defaults — the admin then edits
	 *  only the weights that should differ, instead of typing all fifteen. */
	async function createPreset() {
		if (creating) return;
		creating = true;
		presetError = '';
		try {
			const base = { ...form, name: `نظام ${presets.length + 1}` };
			const created = await scoringPresetsApi.create(base);
			presets = [...presets, created].sort((a, b) => a.name.localeCompare(b.name, 'ar'));
			drafts = { ...drafts, [created.id]: { ...created } };
			openPresetId = created.id;
		} catch (e) {
			presetError = e instanceof ApiError ? e.message : 'تعذّر إنشاء النظام.';
		} finally {
			creating = false;
		}
	}

	async function savePreset(id: string) {
		const draft = drafts[id];
		if (!draft || savingPresetId) return;
		savingPresetId = id;
		presetError = '';
		try {
			const { id: _id, name, ...weights } = draft;
			const body = {
				name: name.trim(),
				...(Object.fromEntries(
					Object.entries(weights).map(([k, v]) => [k, Number(v)])
				) as unknown as ScoringSettings)
			};
			const updated = await scoringPresetsApi.update(id, body);
			presets = presets.map((p) => (p.id === id ? updated : p));
			drafts = { ...drafts, [id]: { ...updated } };
		} catch (e) {
			presetError = e instanceof ApiError ? e.message : 'تعذّر حفظ النظام.';
		} finally {
			savingPresetId = null;
		}
	}

	async function deletePreset(preset: ScoringPreset) {
		if (deletingId) return;
		if (
			!confirm(`حذف «${preset.name}»؟ سيعود كل طالب مرتبط به إلى إعدادات النقاط العامة للمعهد.`)
		) {
			return;
		}
		deletingId = preset.id;
		presetError = '';
		try {
			await scoringPresetsApi.remove(preset.id);
			presets = presets.filter((p) => p.id !== preset.id);
			const { [preset.id]: _dropped, ...rest } = drafts;
			drafts = rest;
			if (openPresetId === preset.id) openPresetId = null;
		} catch (e) {
			presetError = e instanceof ApiError ? e.message : 'تعذّر حذف النظام.';
		} finally {
			deletingId = null;
		}
	}

	/** «5 حضور · 7/5/3/0 تسميع» — enough to tell two presets apart without expanding either. */
	function presetSummary(p: ScoringPreset): string {
		return [
			`${p.present_points} حضور`,
			`${p.rating_4_points}/${p.rating_3_points}/${p.rating_2_points}/${p.rating_1_points} تسميع`,
			`${p.attitude_3_points}/${p.attitude_2_points}/${p.attitude_1_points} أدب`
		].join(' · ');
	}
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
						<Input
							id="present"
							type="number"
							min="-100"
							max="100"
							bind:value={form.present_points}
						/>
					</div>
					<div class="space-y-2">
						<Label for="late_points">متأخر</Label>
						<Input
							id="late_points"
							type="number"
							min="-100"
							max="100"
							bind:value={form.late_points}
						/>
					</div>
					<div class="space-y-2">
						<Label for="excused_points">أذن (غياب بعذر)</Label>
						<Input
							id="excused_points"
							type="number"
							min="-100"
							max="100"
							bind:value={form.excused_points}
						/>
					</div>
					<div class="space-y-2">
						<Label for="absent_points">غياب (بلا عذر)</Label>
						<Input
							id="absent_points"
							type="number"
							min="-100"
							max="100"
							bind:value={form.absent_points}
						/>
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
							<Input id={f.key} type="number" min="-100" max="100" bind:value={form[f.key]} />
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
							<Input id={f.key} type="number" min="-100" max="100" bind:value={form[f.key]} />
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
							<Input id={f.key} type="number" min="-100" max="100" bind:value={form[f.key]} />
						</div>
					{/each}
				</div>
			</div>
		</div>
	</div>

	<!-- ===== أنظمة التسعير المخصصة ===== -->
	<div class="glass-card p-5">
		<div class="mb-4 flex flex-wrap items-center justify-between gap-3">
			<div class="flex items-start gap-2">
				<Layers class="mt-0.5 h-5 w-5 shrink-0 text-primary" />
				<div>
					<h2 class="font-bold text-foreground">أنظمة تسعير مخصصة</h2>
					<p class="text-sm text-muted-foreground">
						لطلاب يُحسبون بأوزان مختلفة (مثل طلاب الرشيدي). يربط الأستاذ الطالب بالنظام من التطبيق،
						ومن لا نظام له يُحسب بالإعدادات العامة أعلاه.
					</p>
				</div>
			</div>
			<Button variant="outline" onclick={createPreset} disabled={creating || loading}>
				<Plus class="h-4 w-4" />{creating ? 'جارٍ الإنشاء…' : 'نظام جديد'}
			</Button>
		</div>

		{#if presetError}
			<p class="mb-3 rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">
				{presetError}
			</p>
		{/if}

		{#if presetsLoading}
			<p class="text-sm text-muted-foreground">جارٍ التحميل…</p>
		{:else if presets.length === 0}
			<p
				class="rounded-lg border border-dashed border-border px-3 py-6 text-center text-sm text-muted-foreground"
			>
				لا توجد أنظمة مخصصة — جميع الطلاب يُحسبون بالإعدادات العامة.
			</p>
		{:else}
			<div class="space-y-2">
				{#each presets as p (p.id)}
					{@const open = openPresetId === p.id}
					<div class="rounded-xl border border-border">
						<div class="flex items-center gap-2 p-3">
							<button
								type="button"
								onclick={() => (openPresetId = open ? null : p.id)}
								class="flex min-w-0 flex-1 items-center gap-2 text-right"
								aria-expanded={open}
							>
								<ChevronDown
									class="h-4 w-4 shrink-0 text-muted-foreground transition-transform {open
										? 'rotate-180'
										: ''}"
								/>
								<span class="min-w-0">
									<span class="block truncate font-bold text-foreground">{p.name}</span>
									<span class="block truncate text-xs text-muted-foreground"
										>{presetSummary(p)}</span
									>
								</span>
							</button>
							<Button
								variant="ghost"
								size="icon"
								onclick={() => deletePreset(p)}
								disabled={deletingId === p.id}
								aria-label={`حذف ${p.name}`}
							>
								<Trash2 class="h-4 w-4 text-destructive" />
							</Button>
						</div>

						{#if open && drafts[p.id]}
							<div class="space-y-5 border-t border-border p-4">
								<div class="space-y-2">
									<Label for={`name-${p.id}`}>اسم النظام</Label>
									<Input id={`name-${p.id}`} bind:value={drafts[p.id].name} maxlength={120} />
								</div>

								<div>
									<h3 class="mb-2 font-bold text-foreground">الحضور</h3>
									<div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
										{#each [{ key: 'present_points', label: 'نقاط الحضور' }, { key: 'late_points', label: 'متأخر' }, { key: 'excused_points', label: 'أذن (غياب بعذر)' }, { key: 'absent_points', label: 'غياب (بلا عذر)' }] as const as f (f.key)}
											<div class="space-y-2">
												<Label for={`${f.key}-${p.id}`}>{f.label}</Label>
												<Input
													id={`${f.key}-${p.id}`}
													type="number"
													min="-100"
													max="100"
													bind:value={drafts[p.id][f.key]}
												/>
											</div>
										{/each}
									</div>
								</div>

								<div>
									<h3 class="mb-2 font-bold text-foreground">التقدير (التسميع والاختبار)</h3>
									<div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
										{#each ratingFields as f (f.key)}
											<div class="space-y-2">
												<Label for={`${f.key}-${p.id}`}>{f.label}</Label>
												<Input
													id={`${f.key}-${p.id}`}
													type="number"
													min="-100"
													max="100"
													bind:value={drafts[p.id][f.key]}
												/>
											</div>
										{/each}
									</div>
								</div>

								<div>
									<h3 class="mb-2 font-bold text-foreground">المراجعة</h3>
									<div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
										{#each revisionFields as f (f.key)}
											<div class="space-y-2">
												<Label for={`${f.key}-${p.id}`}>{f.label}</Label>
												<Input
													id={`${f.key}-${p.id}`}
													type="number"
													min="-100"
													max="100"
													bind:value={drafts[p.id][f.key]}
												/>
											</div>
										{/each}
									</div>
								</div>

								<div>
									<h3 class="mb-2 font-bold text-foreground">الأدب</h3>
									<div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
										{#each attitudeFields as f (f.key)}
											<div class="space-y-2">
												<Label for={`${f.key}-${p.id}`}>{f.label}</Label>
												<Input
													id={`${f.key}-${p.id}`}
													type="number"
													min="-100"
													max="100"
													bind:value={drafts[p.id][f.key]}
												/>
											</div>
										{/each}
									</div>
								</div>

								<div class="flex justify-end">
									<Button onclick={() => savePreset(p.id)} disabled={savingPresetId === p.id}>
										<Save class="h-4 w-4" />
										{savingPresetId === p.id ? 'جارٍ الحفظ…' : 'حفظ النظام'}
									</Button>
								</div>
							</div>
						{/if}
					</div>
				{/each}
			</div>
		{/if}
	</div>
</div>
