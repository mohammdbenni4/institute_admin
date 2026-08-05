<script lang="ts">
	// «استدعاء ولي أمر» — the administration's queue.
	//
	// Every row links straight to the teacher, student and halaqah profiles, and
	// offers a WhatsApp button to the guardian, so handling a request never means
	// hunting for a phone number.
	import { ApiError, parentSummonsApi, type ParentSummon, type SummonStatus } from '$lib/api';
	import { whatsappLink } from '$lib/utils';
	import PageHeader from '$lib/components/shared/PageHeader.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import Dialog from '$lib/components/ui/Dialog.svelte';
	import {
		AlertCircle,
		CheckCircle2,
		Clock,
		Inbox,
		MessageCircle,
		Send,
		Trash2
	} from '@lucide/svelte';

	const PAGE_SIZE = 50;

	// The workflow, in order. `next` drives the one-tap "move it along" button.
	const STAGES: { key: SummonStatus; label: string; next: SummonStatus | null }[] = [
		{ key: 'new', label: 'قيد الانتظار', next: 'reviewing' },
		{ key: 'reviewing', label: 'تتم المراجعة', next: 'completed' },
		{ key: 'completed', label: 'منتهي', next: null }
	];

	let statusFilter = $state<SummonStatus | 'all'>('all');
	let items = $state<ParentSummon[]>([]);
	let counts = $state<Record<SummonStatus, number>>({ new: 0, reviewing: 0, completed: 0 });
	let total = $state(0);
	let loading = $state(true);
	let error = $state('');

	// Reply dialog
	let replying = $state<ParentSummon | null>(null);
	let replyText = $state('');
	let replyStatus = $state<SummonStatus>('completed');
	let saving = $state(false);

	async function load() {
		loading = true;
		error = '';
		try {
			const res = await parentSummonsApi.list({
				status: statusFilter === 'all' ? undefined : statusFilter,
				limit: PAGE_SIZE
			});
			items = res.items;
			counts = res.counts;
			total = res.total;
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'تعذّر تحميل الطلبات.';
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		void statusFilter;
		void load();
	});

	async function advance(item: ParentSummon) {
		const stage = STAGES.find((s) => s.key === item.status);
		if (!stage?.next) return;
		try {
			await parentSummonsApi.update(item.id, { status: stage.next });
			await load();
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'تعذّر تحديث الحالة.';
		}
	}

	function openReply(item: ParentSummon) {
		replying = item;
		replyText = item.admin_response ?? '';
		replyStatus = item.status === 'new' ? 'reviewing' : item.status;
	}

	async function saveReply() {
		if (!replying || saving) return;
		saving = true;
		try {
			await parentSummonsApi.update(replying.id, {
				status: replyStatus,
				admin_response: replyText.trim() || null
			});
			replying = null;
			await load();
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'تعذّر حفظ الرد.';
		} finally {
			saving = false;
		}
	}

	async function remove(item: ParentSummon) {
		if (!confirm(`حذف طلب استدعاء ولي أمر الطالب ${item.student_name}؟`)) return;
		try {
			await parentSummonsApi.remove(item.id);
			await load();
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'تعذّر الحذف.';
		}
	}

	function badgeClass(s: SummonStatus): string {
		if (s === 'completed') return 'bg-emerald-500/10 text-emerald-600 border-emerald-500/30';
		if (s === 'reviewing') return 'bg-amber-500/10 text-amber-600 border-amber-500/30';
		return 'bg-primary/10 text-primary border-primary/30';
	}

	/** Full date + time — the institute needs to know when a request came in. */
	function stamp(iso: string): string {
		const d = new Date(iso);
		return new Intl.DateTimeFormat('ar-u-nu-latn', {
			dateStyle: 'medium',
			timeStyle: 'short'
		}).format(d);
	}
</script>

<div class="page-container">
	<PageHeader
		title="استدعاء ولي أمر"
		subtitle="طلبات المعلمين لاستدعاء أولياء الأمور ومتابعة حالتها"
		breadcrumbs={[{ label: 'لوحة التحكم' }, { label: 'استدعاء ولي أمر' }]}
	/>

	{#if error}
		<p class="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>
	{/if}

	<!-- Queue summary doubles as the filter -->
	<div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
		<button
			onclick={() => (statusFilter = 'all')}
			class={'flex flex-col gap-1.5 rounded-xl border bg-card p-4 text-right shadow-sm transition ' +
				(statusFilter === 'all' ? 'border-primary' : 'border-border hover:border-primary/40')}
		>
			<span class="flex items-center gap-2 text-xs text-muted-foreground">
				<Inbox class="h-4 w-4" />كل الطلبات
			</span>
			<span class="text-2xl font-bold text-foreground">{total}</span>
		</button>
		{#each STAGES as stage (stage.key)}
			<button
				onclick={() => (statusFilter = stage.key)}
				class={'flex flex-col gap-1.5 rounded-xl border bg-card p-4 text-right shadow-sm transition ' +
					(statusFilter === stage.key ? 'border-primary' : 'border-border hover:border-primary/40')}
			>
				<span class="flex items-center gap-2 text-xs text-muted-foreground">
					{#if stage.key === 'new'}<AlertCircle class="h-4 w-4 text-primary" />
					{:else if stage.key === 'reviewing'}<Clock class="h-4 w-4 text-amber-500" />
					{:else}<CheckCircle2 class="h-4 w-4 text-emerald-500" />{/if}
					{stage.label}
				</span>
				<span class="text-2xl font-bold text-foreground">{counts[stage.key] ?? 0}</span>
			</button>
		{/each}
	</div>

	{#if loading}
		<div class="space-y-3">
			{#each Array(4) as _, i (i)}
				<div class="h-32 animate-pulse rounded-2xl bg-muted"></div>
			{/each}
		</div>
	{:else if items.length === 0}
		<div
			class="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-border py-16 text-center"
		>
			<Inbox class="h-10 w-10 text-muted-foreground/30" />
			<p class="font-semibold text-foreground">لا توجد طلبات</p>
			<p class="text-sm text-muted-foreground">
				{statusFilter === 'all' ? 'لم يصل أي طلب استدعاء بعد.' : 'لا توجد طلبات في هذه الحالة.'}
			</p>
		</div>
	{:else}
		<div class="space-y-3">
			{#each items as item (item.id)}
				{@const wa = whatsappLink(
					item.father_number,
					`السلام عليكم، من إدارة المعهد بخصوص الطالب ${item.student_name}. نرجو التواصل معنا.`
				)}
				{@const stage = STAGES.find((s) => s.key === item.status)}
				<div class="glass-card space-y-3 p-5">
					<!-- header: who + when + status -->
					<div class="flex flex-wrap items-start justify-between gap-3">
						<div class="min-w-0 space-y-1">
							<a
								href={`/admin/students/${item.student_id}`}
								class="text-base font-bold text-primary hover:underline"
							>
								{item.student_name}
							</a>
							<div
								class="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground"
							>
								<span>
									المعلم:
									<a
										href={`/admin/teachers/${item.teacher_id}`}
										class="font-medium text-primary hover:underline">{item.teacher_name}</a
									>
								</span>
								<span>
									الحلقة:
									<a
										href={`/admin/halaqahs/${item.halaqah_id}`}
										class="font-medium text-primary hover:underline">{item.halaqah_name}</a
									>
								</span>
								{#if item.father_name}<span>ولي الأمر: {item.father_name}</span>{/if}
							</div>
							<p class="text-[11px] text-muted-foreground">
								تاريخ الطلب: {stamp(item.created_at)}
								{#if item.handled_at}· أُنجز: {stamp(item.handled_at)}{/if}
							</p>
						</div>
						<span
							class={'shrink-0 rounded-full border px-3 py-1 text-xs font-semibold ' +
								badgeClass(item.status)}
						>
							{item.status_label}
						</span>
					</div>

					<!-- the teacher's reason -->
					<div class="rounded-xl bg-muted/50 p-3">
						<p class="text-[11px] font-medium text-muted-foreground">سبب الطلب</p>
						<p class="mt-0.5 text-sm leading-relaxed text-foreground">{item.reason}</p>
					</div>

					{#if item.admin_response}
						<div class="rounded-xl border border-emerald-500/25 bg-emerald-500/5 p-3">
							<p class="text-[11px] font-medium text-emerald-600">رد الإدارة (يظهر للمعلم)</p>
							<p class="mt-0.5 text-sm leading-relaxed text-foreground">{item.admin_response}</p>
						</div>
					{/if}

					<!-- actions -->
					<div class="flex flex-wrap items-center gap-2 border-t border-border pt-3">
						{#if wa}
							<a
								href={wa}
								target="_blank"
								rel="noopener noreferrer"
								class="inline-flex items-center gap-1.5 rounded-lg bg-emerald-500/10 px-3 py-2 text-xs font-medium text-emerald-600 transition hover:bg-emerald-500 hover:text-white"
							>
								<MessageCircle class="h-3.5 w-3.5" />واتساب ولي الأمر
							</a>
						{:else}
							<span class="text-xs text-muted-foreground">لا يوجد رقم لولي الأمر</span>
						{/if}

						{#if stage?.next}
							<Button size="sm" variant="outline" onclick={() => advance(item)}>
								<Clock class="h-3.5 w-3.5" />
								{stage.next === 'reviewing' ? 'بدء المراجعة' : 'إنهاء الطلب'}
							</Button>
						{/if}

						<Button size="sm" onclick={() => openReply(item)}>
							<Send class="h-3.5 w-3.5" />
							{item.admin_response ? 'تعديل الرد' : 'إرسال رد للمعلم'}
						</Button>

						<button
							onclick={() => remove(item)}
							class="ms-auto inline-flex items-center gap-1.5 rounded-lg px-2 py-2 text-xs text-destructive hover:bg-destructive/10"
						>
							<Trash2 class="h-3.5 w-3.5" />حذف
						</button>
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>

<!-- Reply + status dialog -->
<Dialog
	open={replying !== null}
	onOpenChange={(v) => !v && (replying = null)}
	title="الرد على المعلم"
>
	{#if replying}
		<div class="space-y-4" dir="rtl">
			<p class="text-sm text-muted-foreground">
				الطالب <span class="font-bold text-foreground">{replying.student_name}</span> — المعلم
				<span class="font-bold text-foreground">{replying.teacher_name}</span>
			</p>

			<div class="space-y-2">
				<span class="text-sm font-medium text-foreground">الحالة</span>
				<div class="flex flex-wrap gap-2">
					{#each STAGES as stage (stage.key)}
						<button
							type="button"
							onclick={() => (replyStatus = stage.key)}
							class={'rounded-lg border px-3 py-2 text-xs font-medium transition ' +
								(replyStatus === stage.key
									? 'border-primary bg-primary/10 text-primary'
									: 'border-border text-muted-foreground hover:bg-muted')}
						>
							{stage.label}
						</button>
					{/each}
				</div>
			</div>

			<div class="space-y-2">
				<span class="text-sm font-medium text-foreground">نص الرد</span>
				<textarea
					bind:value={replyText}
					rows="4"
					placeholder="مثال: تم التواصل مع والد الطالب وتفاهمنا على متابعة الحضور."
					class="w-full resize-none rounded-lg border border-input bg-background p-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
				></textarea>
				<p class="text-[11px] text-muted-foreground">
					يظهر هذا الرد للمعلم مباشرة في تطبيقه ضمن صفحة «استدعاء ولي أمر».
				</p>
			</div>

			<div class="flex justify-end gap-2">
				<Button variant="outline" onclick={() => (replying = null)}>إلغاء</Button>
				<Button onclick={saveReply} disabled={saving}>
					{saving ? 'جارٍ الحفظ…' : 'حفظ وإرسال'}
				</Button>
			</div>
		</div>
	{/if}
</Dialog>
