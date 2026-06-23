// Parse the institute's "Member.xlsx" `student` sheet into create-ready rows.
//
// The sheet's columns are matched by their Arabic headers (robust to column
// reordering). Halaqah names are resolved against existing halaqahs; rows whose
// halaqah has no match are flagged so the UI can block the import until the
// missing halaqahs are created. Missing father name/number become the
// placeholder "—" (the source data legitimately lacks them for many students).

import type { Halaqah, StudentCreate } from '$lib/api';

export const PLACEHOLDER = '—';

export interface ParsedRow extends StudentCreate {
	/** Raw halaqah name as written in the sheet. */
	halaqahName: string;
	/** True when the halaqah name matched an existing halaqah. */
	halaqahMatched: boolean;
	fatherNamePlaceholder: boolean;
	fatherNumberPlaceholder: boolean;
}

export interface ParseResult {
	rows: ParsedRow[];
	/** Distinct halaqah names from the sheet that have no existing match. */
	unmatchedHalaqahs: string[];
	totalRows: number;
	placeholderFatherName: number;
	placeholderFatherNumber: number;
	skippedNoName: number;
}

/** Normalise Arabic text for tolerant matching (alef/hamza/ya/ta, spaces, diacritics). */
function normalize(value: unknown): string {
	return String(value ?? '')
		.replace(/[ً-ْـ]/g, '') // diacritics + tatweel
		.replace(/[أإآ]/g, 'ا')
		.replace(/ى/g, 'ي')
		.replace(/ة/g, 'ه')
		.replace(/\s+/g, ' ')
		.trim();
}

/** Headers we care about, keyed by a normalized form of the sheet's header text. */
const HEADER_ALIASES: Record<string, keyof ColumnIndex> = {
	'اسم الحلقه': 'halaqah',
	'اسم الطالب': 'fullName',
	'اسم الاب': 'fatherName',
	'رقم الاب': 'fatherNumber',
	'رقم الام': 'motherNumber',
	'تاريخ الولاده': 'birth',
	يتيم: 'orphan',
	'مكان الاقامه': 'area',
	'تاريخ القبول': 'accepted',
	'ملاحظات الطالب': 'notes'
};

interface ColumnIndex {
	halaqah: number;
	fullName: number;
	fatherName: number;
	fatherNumber: number;
	motherNumber: number;
	birth: number;
	orphan: number;
	area: number;
	accepted: number;
	notes: number;
}

function buildColumnIndex(header: unknown[]): ColumnIndex {
	const idx: ColumnIndex = {
		halaqah: -1,
		fullName: -1,
		fatherName: -1,
		fatherNumber: -1,
		motherNumber: -1,
		birth: -1,
		orphan: -1,
		area: -1,
		accepted: -1,
		notes: -1
	};
	header.forEach((cell, i) => {
		const key = HEADER_ALIASES[normalize(cell)];
		if (key && idx[key] === -1) idx[key] = i;
	});
	return idx;
}

function pad2(n: number): string {
	return String(n).padStart(2, '0');
}

/** Coerce a cell into an ISO date (`YYYY-MM-DD`), synthesising Jan 1 for bare years. */
function toIsoDate(value: unknown): string | null {
	if (value == null || value === '') return null;
	if (value instanceof Date && !Number.isNaN(value.getTime())) {
		return `${value.getFullYear()}-${pad2(value.getMonth() + 1)}-${pad2(value.getDate())}`;
	}
	if (typeof value === 'number') {
		const year = Math.trunc(value);
		return year >= 1900 && year <= 2099 ? `${year}-01-01` : null;
	}
	const s = String(value).trim();
	if (/^\d{4}$/.test(s)) return `${s}-01-01`;
	const parsed = new Date(s);
	if (!Number.isNaN(parsed.getTime())) {
		return `${parsed.getFullYear()}-${pad2(parsed.getMonth() + 1)}-${pad2(parsed.getDate())}`;
	}
	return null;
}

function cellText(value: unknown): string {
	if (value == null) return '';
	if (typeof value === 'number') return String(Math.round(value));
	return String(value).trim();
}

export async function parseStudentsSheet(file: File, halaqahs: Halaqah[]): Promise<ParseResult> {
	const XLSX = await import('xlsx');
	const buf = await file.arrayBuffer();
	const wb = XLSX.read(buf, { cellDates: true });

	const sheetName = wb.SheetNames.find((n) => normalize(n) === 'student') ?? wb.SheetNames[0];
	const ws = wb.Sheets[sheetName];
	const aoa = XLSX.utils.sheet_to_json<unknown[]>(ws, {
		header: 1,
		raw: true,
		blankrows: false
	});

	if (aoa.length < 2) {
		return {
			rows: [],
			unmatchedHalaqahs: [],
			totalRows: 0,
			placeholderFatherName: 0,
			placeholderFatherNumber: 0,
			skippedNoName: 0
		};
	}

	const col = buildColumnIndex(aoa[0]);
	const halaqahByName = new Map(halaqahs.map((h) => [normalize(h.name), h]));

	const rows: ParsedRow[] = [];
	const unmatched = new Set<string>();
	let placeholderFatherName = 0;
	let placeholderFatherNumber = 0;
	let skippedNoName = 0;

	for (let r = 1; r < aoa.length; r++) {
		const raw = aoa[r];
		const get = (i: number) => (i >= 0 ? raw[i] : undefined);

		const fullName = cellText(get(col.fullName));
		if (!fullName) {
			skippedNoName++;
			continue;
		}

		const fatherNameRaw = cellText(get(col.fatherName));
		const fatherNumberRaw = cellText(get(col.fatherNumber));
		const fatherNamePlaceholder = !fatherNameRaw;
		const fatherNumberPlaceholder = !fatherNumberRaw;
		if (fatherNamePlaceholder) placeholderFatherName++;
		if (fatherNumberPlaceholder) placeholderFatherNumber++;

		const halaqahName = cellText(get(col.halaqah));
		const matched = halaqahName ? halaqahByName.get(normalize(halaqahName)) : undefined;
		if (halaqahName && !matched) unmatched.add(halaqahName);

		const area = cellText(get(col.area));
		const motherNumber = cellText(get(col.motherNumber));

		rows.push({
			full_name: fullName,
			father_name: fatherNameRaw || PLACEHOLDER,
			father_number: fatherNumberRaw || PLACEHOLDER,
			date_of_birth: toIsoDate(get(col.birth)),
			mother_number: motherNumber || null,
			orphan_of: null,
			residential_area: area || null,
			accepted_at: toIsoDate(get(col.accepted)),
			notes: null,
			halaqah_id: matched?.id ?? null,
			halaqahName: halaqahName || PLACEHOLDER,
			halaqahMatched: !!matched,
			fatherNamePlaceholder,
			fatherNumberPlaceholder
		});
	}

	return {
		rows,
		unmatchedHalaqahs: [...unmatched].sort((a, b) => a.localeCompare(b, 'ar')),
		totalRows: rows.length,
		placeholderFatherName,
		placeholderFatherNumber,
		skippedNoName
	};
}

/** Re-match every row's halaqah against an updated halaqah list (after creating some). */
export function resolveHalaqahs(
	rows: ParsedRow[],
	halaqahs: Halaqah[]
): { rows: ParsedRow[]; unmatchedHalaqahs: string[] } {
	const byName = new Map(halaqahs.map((h) => [normalize(h.name), h]));
	const unmatched = new Set<string>();
	const next = rows.map((row) => {
		// A row already ignored (matched with no halaqah) stays unassigned.
		if (row.halaqahMatched && row.halaqah_id === null) return row;
		const name = row.halaqahName === PLACEHOLDER ? '' : row.halaqahName;
		const match = name ? byName.get(normalize(name)) : undefined;
		if (name && !match) unmatched.add(name);
		return { ...row, halaqah_id: match?.id ?? null, halaqahMatched: !!match };
	});
	return { rows: next, unmatchedHalaqahs: [...unmatched].sort((a, b) => a.localeCompare(b, 'ar')) };
}

/** Treat all unmatched halaqahs as "no halaqah": rows import unassigned. */
export function ignoreUnmatchedHalaqahs(rows: ParsedRow[]): ParsedRow[] {
	return rows.map((row) =>
		row.halaqahMatched ? row : { ...row, halaqah_id: null, halaqahMatched: true }
	);
}

/** Strip the preview-only fields, leaving a clean StudentCreate payload. */
export function toCreatePayload(row: ParsedRow): StudentCreate {
	return {
		full_name: row.full_name,
		father_name: row.father_name,
		father_number: row.father_number,
		date_of_birth: row.date_of_birth,
		mother_number: row.mother_number,
		orphan_of: row.orphan_of,
		residential_area: row.residential_area,
		accepted_at: row.accepted_at,
		notes: row.notes,
		halaqah_id: row.halaqah_id
	};
}
