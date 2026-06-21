import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

/** Merge Tailwind class names, resolving conflicts (shadcn-style `cn` helper). */
export function cn(...inputs: ClassValue[]) {
	return twMerge(clsx(inputs));
}

/**
 * Build a WhatsApp deep link (`https://wa.me/<intl-number>`) from a phone, with
 * an optional prefilled message. Returns `null` when there are no digits.
 * Numbers should include a country code; a leading `00` is stripped.
 */
export function whatsappLink(phone: string | null | undefined, message = ''): string | null {
	if (!phone) return null;
	let digits = phone.replace(/\D/g, '');
	if (digits.startsWith('00')) digits = digits.slice(2);
	if (!digits) return null;
	const query = message ? `?text=${encodeURIComponent(message)}` : '';
	return `https://wa.me/${digits}${query}`;
}
