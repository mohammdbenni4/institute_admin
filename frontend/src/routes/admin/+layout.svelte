<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import RoleLayout, { type NavItem } from '$lib/components/shared/RoleLayout.svelte';
	import { auth, isSuperAdmin, loadCurrentUser } from '$lib/api/auth.svelte';
	import {
		AlertTriangle,
		BookOpen,
		CalendarCheck,
		Clock,
		GraduationCap,
		LayoutDashboard,
		Layers,
		Loader2,
		SlidersHorizontal,
		UserCheck,
		Users
	} from '@lucide/svelte';
	import type { Snippet } from 'svelte';

	let { children }: { children: Snippet } = $props();

	let ready = $state(false);

	onMount(async () => {
		if (!auth.loaded) await loadCurrentUser();
		if (!isSuperAdmin(auth.user)) {
			await goto('/login');
			return;
		}
		ready = true;
	});

	const adminNav: NavItem[] = [
		{ label: 'لوحة التحكم', href: '/admin', icon: LayoutDashboard },
		{ label: 'المستخدمون', href: '/admin/users', icon: Users },
		{ label: 'المعلمون', href: '/admin/teachers', icon: UserCheck },
		{ label: 'الطلاب', href: '/admin/students', icon: GraduationCap },
		{ label: 'الحضور والغياب', href: '/admin/attendance', icon: CalendarCheck },
		{ label: 'الحلقات', href: '/admin/halaqahs', icon: BookOpen },
		{ label: 'أنواع الحلقات', href: '/admin/halaqah-types', icon: Layers },
		{ label: 'الأوقات', href: '/admin/times', icon: Clock },
		{ label: 'إعدادات النقاط', href: '/admin/scoring', icon: SlidersHorizontal },
		{ label: 'الصعوبات', href: '/admin/problems', icon: AlertTriangle }
	];
</script>

{#if ready && auth.user}
	<RoleLayout
		roleName="المدير العام"
		userName={auth.user.full_name}
		navItems={adminNav}
		basePath="/admin"
	>
		{@render children()}
	</RoleLayout>
{:else}
	<div class="flex min-h-screen items-center justify-center">
		<Loader2 class="h-6 w-6 animate-spin text-primary" />
	</div>
{/if}
