import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

/** Merge Tailwind classes, resolving conflicts (last wins). */
export function cn(...inputs: ClassValue[]): string {
	return twMerge(clsx(inputs));
}

/** Today's date as a local `YYYY-MM-DD` (not UTC — avoids off-by-one at night). */
export function todayIso(): string {
	const d = new Date();
	const m = String(d.getMonth() + 1).padStart(2, '0');
	const day = String(d.getDate()).padStart(2, '0');
	return `${d.getFullYear()}-${m}-${day}`;
}

/** Add `days` to an ISO date string and return a new ISO date string. */
export function addDays(iso: string, days: number): string {
	const d = new Date(iso + 'T00:00:00');
	d.setDate(d.getDate() + days);
	const m = String(d.getMonth() + 1).padStart(2, '0');
	const day = String(d.getDate()).padStart(2, '0');
	return `${d.getFullYear()}-${m}-${day}`;
}

const _dateFmt = new Intl.DateTimeFormat('ar', {
	weekday: 'long',
	day: 'numeric',
	month: 'long',
	year: 'numeric'
});

/** A long, human Arabic date, e.g. "الأربعاء ١٨ يونيو ٢٠٢٦". */
export function formatDateArabic(iso: string): string {
	return _dateFmt.format(new Date(iso + 'T00:00:00'));
}

const _shortFmt = new Intl.DateTimeFormat('ar', { day: 'numeric', month: 'short' });

export function formatDateShort(iso: string): string {
	return _shortFmt.format(new Date(iso + 'T00:00:00'));
}

/** Build a WhatsApp deep link from a phone (+ optional message); null if empty. */
export function whatsappLink(phone: string | null | undefined, message = ''): string | null {
	if (!phone) return null;
	let digits = phone.replace(/\D/g, '');
	if (digits.startsWith('00')) digits = digits.slice(2);
	if (!digits) return null;
	const query = message ? `?text=${encodeURIComponent(message)}` : '';
	return `https://wa.me/${digits}${query}`;
}

/** Up to two leading letters for an avatar fallback. */
export function initials(name: string): string {
	const parts = name.trim().split(/\s+/).filter(Boolean);
	if (parts.length === 0) return '؟';
	if (parts.length === 1) return parts[0].slice(0, 2);
	return parts[0][0] + parts[1][0];
}

/** First and last ISO dates of the month that `iso` (default today) falls in. */
export function monthRange(iso: string = todayIso()): { from: string; to: string; days: number } {
	const [y, m] = iso.split('-').map(Number);
	const last = new Date(y, m, 0).getDate();
	const mm = String(m).padStart(2, '0');
	return { from: `${y}-${mm}-01`, to: `${y}-${mm}-${String(last).padStart(2, '0')}`, days: last };
}

/** Day-of-month (1..31) of an ISO date. */
export function dayOfMonth(iso: string): number {
	return Number(iso.slice(8, 10));
}

const _arabicDigits = ['٠', '١', '٢', '٣', '٤', '٥', '٦', '٧', '٨', '٩'];
/** Render a number with Arabic-Indic digits, e.g. 29 → ٢٩. */
export function arabicNum(n: number | string): string {
	return String(n).replace(/[0-9]/g, (d) => _arabicDigits[Number(d)]);
}
