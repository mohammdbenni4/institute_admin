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

// Arabic wording, Latin digits. `-u-nu-latn` keeps the weekday names Arabic while
// forcing 0-9 instead of ٠-٩, so every number in the app reads the same way.
const AR_LATN = 'ar-u-nu-latn';

// Levantine Gregorian month names. `Intl('ar')` returns the Egyptian/Gulf set
// («يوليو»), but the institute is Syrian and its printed report says «تموز» — the
// app and the report must not name the same month two different ways.
const LEVANT_MONTHS = [
	'كانون الثاني',
	'شباط',
	'آذار',
	'نيسان',
	'أيار',
	'حزيران',
	'تموز',
	'آب',
	'أيلول',
	'تشرين الأول',
	'تشرين الثاني',
	'كانون الأول'
] as const;

/** Short Levantine month name for an ISO date. */
function levantMonth(iso: string): string {
	return LEVANT_MONTHS[Number(iso.slice(5, 7)) - 1] ?? '';
}

const _weekdayFmt = new Intl.DateTimeFormat(AR_LATN, { weekday: 'long' });

/** A long, human date, e.g. "الأربعاء، 18 حزيران 2026". */
export function formatDateArabic(iso: string): string {
	const weekday = _weekdayFmt.format(new Date(iso + 'T00:00:00'));
	return `${weekday}، ${Number(iso.slice(8, 10))} ${levantMonth(iso)} ${iso.slice(0, 4)}`;
}

/** Day + month, e.g. "18 حزيران". */
export function formatDateShort(iso: string): string {
	return `${Number(iso.slice(8, 10))} ${levantMonth(iso)}`;
}

/** Month + year, e.g. "حزيران 2026". */
export function formatMonthArabic(iso: string): string {
	return `${levantMonth(iso)} ${iso.slice(0, 4)}`;
}

/** Add `delta` months to an ISO date, returning a new `YYYY-MM-DD`. */
export function addMonths(iso: string, delta: number): string {
	const [y, m, d] = iso.split('-').map(Number);
	const dt = new Date(y, m - 1 + delta, d);
	const mm = String(dt.getMonth() + 1).padStart(2, '0');
	const day = String(dt.getDate()).padStart(2, '0');
	return `${dt.getFullYear()}-${mm}-${day}`;
}

/** The `YYYY-MM` value for an `<input type="month">`. */
export function monthInputValue(iso: string): string {
	return iso.slice(0, 7);
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

// Weekday keys as the backend stores them, indexed by JS `Date.getDay()`
// (0 = Sunday … 6 = Saturday).
const WEEKDAY_KEYS = [
	'sunday',
	'monday',
	'tuesday',
	'wednesday',
	'thursday',
	'friday',
	'saturday'
] as const;

/**
 * The halaqah's next session strictly after `fromIso`, from its weekly timetable.
 * Returns null when the halaqah has no schedule set. Scans two weeks so a single
 * weekly session is still found.
 */
export function nextSessionDate(
	schedule: Record<string, { from: string; to: string }> | undefined,
	fromIso: string
): string | null {
	if (!schedule || Object.keys(schedule).length === 0) return null;
	for (let step = 1; step <= 14; step++) {
		const iso = addDays(fromIso, step);
		const day = new Date(iso + 'T00:00:00').getDay();
		if (schedule[WEEKDAY_KEYS[day]]) return iso;
	}
	return null;
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

/**
 * Force Latin digits in a string that may carry Arabic-Indic ones.
 *
 * Numbers are written in Latin digits everywhere in the app now. This exists for
 * *stored* text written by older versions — e.g. a `revision_lesson` saved as
 * "الجزء ٢٩ (النصف الأول): نجح" — so history renders consistently with new records.
 */
export function toLatinDigits(value: string | number | null | undefined): string {
	if (value == null) return '';
	return String(value).replace(/[٠-٩۰-۹]/g, (d) => {
		const code = d.charCodeAt(0);
		const base = code >= 0x06f0 ? 0x06f0 : 0x0660;
		return String(code - base);
	});
}
