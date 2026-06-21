<script lang="ts" module>
	import type { Component } from 'svelte';

	export interface NavItem {
		label: string;
		href: string;
		icon: Component<{ class?: string }>;
	}
</script>

<script lang="ts">
	import { page } from '$app/stores';
	import { cn } from '$lib/utils';
	import { X } from '@lucide/svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import TopHeader from './TopHeader.svelte';
	import type { Snippet } from 'svelte';

	interface Props {
		roleName: string;
		userName: string;
		navItems: NavItem[];
		basePath: string;
		children: Snippet;
	}

	let { roleName, userName, navItems, basePath, children }: Props = $props();

	let sidebarOpen = $state(false);

	function isActive(href: string): boolean {
		const path = $page.url.pathname;
		if (href === basePath) return path === basePath;
		return path.startsWith(href);
	}
</script>

<div class="flex min-h-screen w-full">
	<!-- Overlay -->
	{#if sidebarOpen}
		<div
			class="fixed inset-0 z-40 bg-foreground/20 lg:hidden"
			role="presentation"
			onclick={() => (sidebarOpen = false)}
		></div>
	{/if}

	<!-- Sidebar -->
	<aside
		class={cn(
			'fixed right-0 top-0 z-50 flex h-screen w-64 flex-col bg-sidebar text-sidebar-foreground transition-transform duration-200 lg:sticky lg:translate-x-0',
			sidebarOpen ? 'translate-x-0' : 'translate-x-full'
		)}
	>
		<div class="flex items-center justify-between border-b border-sidebar-border p-4">
			<div>
				<h2 class="text-sm font-bold text-sidebar-primary-foreground">نظام إدارة معهد القرآن</h2>
				<p class="mt-0.5 text-xs text-sidebar-foreground/70">{roleName}</p>
			</div>
			<Button
				variant="ghost"
				size="icon"
				class="text-sidebar-foreground lg:hidden"
				onclick={() => (sidebarOpen = false)}
			>
				<X class="h-4 w-4" />
			</Button>
		</div>

		<nav class="flex-1 space-y-0.5 overflow-y-auto px-2 py-3">
			{#each navItems as item (item.href)}
				{@const Icon = item.icon}
				<a
					href={item.href}
					onclick={() => (sidebarOpen = false)}
					class={cn(
						'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors',
						isActive(item.href)
							? 'bg-sidebar-accent font-medium text-sidebar-accent-foreground'
							: 'text-sidebar-foreground/80 hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground'
					)}
				>
					<Icon class="h-[18px] w-[18px] shrink-0" />
					<span>{item.label}</span>
				</a>
			{/each}
		</nav>
	</aside>

	<!-- Main content -->
	<div class="flex min-h-screen flex-1 flex-col">
		<TopHeader {userName} {roleName} onToggleSidebar={() => (sidebarOpen = true)} />
		<main class="flex-1">
			{@render children()}
		</main>
	</div>
</div>
