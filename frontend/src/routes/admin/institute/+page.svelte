<script lang="ts">
	import PageHeader from '$lib/components/shared/PageHeader.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import Input from '$lib/components/ui/Input.svelte';
	import Label from '$lib/components/ui/Label.svelte';
	import { ApiError, instituteApi, type InstituteSettings } from '$lib/api';
	import { Building2, Save, Trash2, Upload } from '@lucide/svelte';

	// These defaults mirror the institute's existing paper report; the server seeds
	// the same values, so an untouched installation prints exactly like the original.
	let form = $state<InstituteSettings>({
		name: 'معهد الحسن بن علي',
		subtitle: 'لتحفيظ القرآن الكريم وعلومه',
		phone: '0936277686',
		logo_url: null,
		report_footer: 'تعاد الورقة إلى المعهد',
		report_note: 'وفقنا الله وإياكم لخدمة القرآن الكريم.'
	});
	let loading = $state(true);
	let saving = $state(false);
	let error = $state('');
	let saved = $state(false);

	/** Logos are inlined as data URIs so the printed report needs no extra request. */
	const MAX_LOGO_BYTES = 400_000;

	async function load() {
		loading = true;
		try {
			form = await instituteApi.get();
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'تعذّر تحميل بيانات المعهد.';
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		load();
	});

	function pickLogo(event: Event) {
		const input = event.target as HTMLInputElement;
		const file = input.files?.[0];
		if (!file) return;
		if (file.size > MAX_LOGO_BYTES) {
			error = 'حجم الشعار كبير جداً (الحد الأقصى 400 كيلوبايت).';
			input.value = '';
			return;
		}
		const reader = new FileReader();
		reader.onload = () => {
			form.logo_url = String(reader.result);
			error = '';
		};
		reader.readAsDataURL(file);
	}

	async function save() {
		if (saving) return;
		saving = true;
		error = '';
		saved = false;
		try {
			form = await instituteApi.update(form);
			saved = true;
			setTimeout(() => (saved = false), 2500);
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'تعذّر حفظ بيانات المعهد.';
		} finally {
			saving = false;
		}
	}
</script>

<div class="page-container">
	<PageHeader
		title="بيانات المعهد"
		subtitle="الاسم والشعار ورقم التواصل — تظهر في ترويسة تقرير الطالب الشهري"
		breadcrumbs={[{ label: 'لوحة التحكم' }, { label: 'بيانات المعهد' }]}
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
		<p class="rounded-lg bg-emerald-500/10 px-3 py-2 text-sm text-emerald-600">تم حفظ البيانات.</p>
	{/if}

	<div class="grid gap-5 lg:grid-cols-3">
		<!-- ─── Identity ─── -->
		<div class="glass-card space-y-4 p-5 lg:col-span-2">
			<div class="flex items-center gap-2 text-sm font-bold text-foreground">
				<Building2 class="h-4 w-4 text-primary" />الهوية
			</div>

			<div class="space-y-1.5">
				<Label for="name">اسم المعهد</Label>
				<Input id="name" bind:value={form.name} placeholder="معهد الحسن بن علي" />
			</div>

			<div class="space-y-1.5">
				<Label for="subtitle">العبارة تحت الاسم</Label>
				<Input id="subtitle" bind:value={form.subtitle} placeholder="لتحفيظ القرآن الكريم وعلومه" />
			</div>

			<div class="space-y-1.5">
				<Label for="phone">رقم المعهد</Label>
				<Input id="phone" bind:value={form.phone} dir="ltr" placeholder="0936277686" />
			</div>

			<div class="space-y-1.5">
				<Label for="report_note">ملاحظة الإدارة في التقرير</Label>
				<Input
					id="report_note"
					bind:value={form.report_note}
					placeholder="وفقنا الله وإياكم لخدمة القرآن الكريم."
				/>
			</div>

			<div class="space-y-1.5">
				<Label for="report_footer">تذييل التقرير</Label>
				<Input
					id="report_footer"
					bind:value={form.report_footer}
					placeholder="تعاد الورقة إلى المعهد"
				/>
			</div>
		</div>

		<!-- ─── Logo ─── -->
		<div class="glass-card space-y-4 p-5">
			<div class="text-sm font-bold text-foreground">الشعار</div>
			<div
				class="flex h-40 items-center justify-center rounded-xl border border-dashed border-border bg-muted/30 p-3"
			>
				{#if form.logo_url}
					<img src={form.logo_url} alt="شعار المعهد" class="max-h-full max-w-full object-contain" />
				{:else}
					<span class="text-xs text-muted-foreground">لا يوجد شعار</span>
				{/if}
			</div>
			<div class="flex gap-2">
				<label
					class="inline-flex flex-1 cursor-pointer items-center justify-center gap-2 rounded-lg border border-border px-3 py-2 text-xs font-medium hover:bg-muted"
				>
					<Upload class="h-3.5 w-3.5" />رفع شعار
					<input type="file" accept="image/*" class="hidden" onchange={pickLogo} />
				</label>
				{#if form.logo_url}
					<button
						type="button"
						onclick={() => (form.logo_url = null)}
						class="inline-flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-xs text-destructive hover:bg-destructive/10"
					>
						<Trash2 class="h-3.5 w-3.5" />حذف
					</button>
				{/if}
			</div>
			<p class="text-[11px] leading-relaxed text-muted-foreground">
				يُحفظ الشعار داخل قاعدة البيانات ويُطبع مع التقرير مباشرة (بدون طلب خارجي). الحد الأقصى 400
				كيلوبايت.
			</p>
		</div>
	</div>
</div>
