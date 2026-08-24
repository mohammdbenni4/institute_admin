// The «رشيدي» curriculum: a fixed 48-page primer booklet (not the mushaf), organised
// into named stages with non-overlapping page ranges. Students on this track are picked
// by صفحة/مرحلة/سطر instead of صفحة/جزء/سورة/آية — see the recitation page.

export interface RashidiStage {
	number: number;
	name: string;
	firstPage: number;
	lastPage: number;
}

export const RASHIDI_STAGES: RashidiStage[] = [
	{ number: 1, name: 'الحروف', firstPage: 5, lastPage: 15 },
	{ number: 2, name: 'الحركات', firstPage: 16, lastPage: 22 },
	{ number: 3, name: 'السكون وحروف المد', firstPage: 23, lastPage: 31 },
	{ number: 4, name: 'الشدة والتنوين', firstPage: 32, lastPage: 42 },
	{ number: 5, name: 'همزتا الوصل والقطع', firstPage: 43, lastPage: 46 },
	{ number: 6, name: 'فوائد وتنبيهات', firstPage: 47, lastPage: 48 }
];

export const RASHIDI_FIRST_PAGE = RASHIDI_STAGES[0].firstPage;
export const RASHIDI_LAST_PAGE = RASHIDI_STAGES[RASHIDI_STAGES.length - 1].lastPage;

/** Every page has the same fixed line count — confirmed by the teacher, not derived. */
export const RASHIDI_LINES_PER_PAGE = 10;

/** The stage a page (5..48) falls in, or null if out of range. */
export function rashidiStageForPage(page: number): RashidiStage | null {
	return RASHIDI_STAGES.find((s) => page >= s.firstPage && page <= s.lastPage) ?? null;
}

/** Every page number within a stage. */
export function rashidiPagesForStage(stage: RashidiStage): number[] {
	return Array.from(
		{ length: stage.lastPage - stage.firstPage + 1 },
		(_, i) => stage.firstPage + i
	);
}

/** One line describing a رشيدي position: «المرحلة الثانية (الحركات) · صفحة 18 · سطر 4». */
export function rashidiFullLabel(page: number, line: number | null): string | null {
	const stage = rashidiStageForPage(page);
	if (!stage) return null;
	const bits = [stage.name, `صفحة ${page}`];
	if (line != null) bits.push(`سطر ${line}`);
	return bits.join(' · ');
}
