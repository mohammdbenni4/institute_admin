<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import PageHeader from '$lib/components/shared/PageHeader.svelte';
	import KPICard from '$lib/components/shared/KPICard.svelte';
	import StatusBadge from '$lib/components/shared/StatusBadge.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import { ApiError, halaqahsApi, teachersApi, type Halaqah, type Teacher } from '$lib/api';
	import { formatDate } from '$lib/labels';
	import { ArrowRight, BookOpen, GraduationCap, Mail, UserCheck, Users } from '@lucide/svelte';

	let id = $derived($page.params.id ?? '');

	let teacher = $state<Teacher | null>(null);
	let halaqahs = $state<Halaqah[]>([]);
	let loading = $state(true);
	let error = $state('');

	async function load() {
		loading = true;
		error = '';
		try {
			const [t, hs] = await Promise.all([
				teachersApi.get(id),
				halaqahsApi.list({ teacher_id: id, limit: 200 })
			]);
			teacher = t;
			halaqahs = hs.items;
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'تعذّر تحميل بيانات المعلم.';
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		if (id) load();
	});

	let totalStudents = $derived(halaqahs.reduce((sum, h) => sum + h.number_of_students, 0));
</script>

<div class="page-container">
	<PageHeader
		title={teacher?.full_name ?? 'ملف المعلم'}
		subtitle={teacher?.email ?? ''}
		breadcrumbs={[
			{ label: 'لوحة التحكم' },
			{ label: 'المعلمون' },
			{ label: teacher?.full_name ?? '…' }
		]}
	>
		{#snippet actions()}
			<Button variant="outline" onclick={() => goto('/admin/teachers')}>
				<ArrowRight class="h-4 w-4" />رجوع
			</Button>
		{/snippet}
	</PageHeader>

	{#if error}
		<p class="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>
	{/if}

	<!-- Teacher info -->
	<div class="glass-card p-5">
		<div class="flex flex-wrap items-start justify-between gap-4">
			<div class="flex items-center gap-3">
				<div class="rounded-2xl bg-primary/10 p-3 text-primary"><UserCheck class="h-6 w-6" /></div>
				<div>
					<p class="text-lg font-bold text-foreground">{teacher?.full_name ?? '…'}</p>
					<p class="flex items-center gap-1 text-sm text-muted-foreground">
						<Mail class="h-3.5 w-3.5" /><span dir="ltr">{teacher?.email ?? '—'}</span>
					</p>
				</div>
			</div>
			<div class="flex flex-wrap items-center gap-2">
				<StatusBadge
					label={teacher?.is_active ? 'نشط' : 'موقوف'}
					tone={teacher?.is_active ? 'success' : 'neutral'}
				/>
				{#if teacher?.is_assistant}<StatusBadge label="معلم مساعد" tone="info" />{/if}
			</div>
		</div>
		<dl
			class="mt-4 grid grid-cols-2 gap-x-8 gap-y-2 border-t border-border/60 pt-4 text-sm sm:grid-cols-3"
		>
			<div>
				<dt class="text-muted-foreground">المؤهل الأكاديمي</dt>
				<dd class="font-medium">{teacher?.academic_study ?? '—'}</dd>
			</div>
			<div>
				<dt class="text-muted-foreground">المؤهل الشرعي</dt>
				<dd class="font-medium">{teacher?.islamic_study ?? '—'}</dd>
			</div>
			<div>
				<dt class="text-muted-foreground">تاريخ الميلاد</dt>
				<dd class="font-medium">{formatDate(teacher?.date_of_birth)}</dd>
			</div>
		</dl>
	</div>

	<!-- KPIs -->
	<div class="grid grid-cols-2 gap-4 sm:grid-cols-3">
		<KPICard title="عدد الحلقات" value={loading ? '…' : halaqahs.length} icon={BookOpen} />
		<KPICard title="إجمالي الطلاب" value={loading ? '…' : totalStudents} icon={Users} />
	</div>

	<!-- Halaqahs led -->
	<div>
		<h2 class="section-title mb-3">الحلقات التي يشرف عليها</h2>
		{#if loading}
			<div class="glass-card p-8 text-center text-muted-foreground">جارٍ التحميل…</div>
		{:else if halaqahs.length === 0}
			<div class="glass-card p-8 text-center text-muted-foreground">
				لا توجد حلقات مُسندة لهذا المعلم.
			</div>
		{:else}
			<div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
				{#each halaqahs as h (h.id)}
					<div class="glass-card p-5">
						<div class="mb-2 flex items-center gap-2">
							<div class="rounded-xl bg-primary/10 p-2 text-primary">
								<GraduationCap class="h-5 w-5" />
							</div>
							<p class="font-bold text-foreground">{h.name}</p>
						</div>
						<p class="text-sm text-muted-foreground">
							{h.halaqah_type_name}{h.level ? ` · ${h.level}` : ''}
						</p>
						<div class="mt-3 flex items-center justify-between text-sm">
							<span class="text-muted-foreground">{h.age ?? '—'}</span>
							<span class="flex items-center gap-1 font-medium text-primary">
								<Users class="h-4 w-4" />{h.number_of_students} طالب
							</span>
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</div>
</div>
