/** Svelte action: calls `handler` when a pointerdown occurs outside `node`. */
export function clickOutside(node: HTMLElement, handler: () => void) {
	function onPointerDown(event: PointerEvent) {
		if (node && !node.contains(event.target as Node)) {
			handler();
		}
	}
	document.addEventListener('pointerdown', onPointerDown, true);
	return {
		destroy() {
			document.removeEventListener('pointerdown', onPointerDown, true);
		}
	};
}
