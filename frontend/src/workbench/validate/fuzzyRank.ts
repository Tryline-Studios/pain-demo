/**
 * The best `limit` candidates for `typed`, best first (spec 17.10). A candidate matches when the typed text is a
 * case-insensitive subsequence of it; slashes in the typed text are ignored, so `//InstdAmt` still suggests paths.
 * Consecutive matched characters and matches at the start of a path segment score higher; ties go to the shorter
 * candidate, then to the earlier one.
 */
export function rank(typed: string, candidates: string[], limit = 8) {
  const needle = typed.toLowerCase().replaceAll("/", "");
  const scored: { candidate: string; score: number }[] = [];
  for (const candidate of candidates) {
    const score = scoreOf(needle, candidate);
    if (score !== null) {
      scored.push({ candidate, score });
    }
  }
  // Array sort is stable, so equal candidates keep document order.
  scored.sort((a, b) => b.score - a.score || a.candidate.length - b.candidate.length);
  return scored.slice(0, limit).map(({ candidate }) => candidate);
}

const CONSECUTIVE = 2;
const SEGMENT_START = 3;

/** The best score over every way `needle` sits in `candidate` as a subsequence, or null if it does not. */
function scoreOf(needle: string, candidate: string) {
  const hay = candidate.toLowerCase();
  // previous[j]: the best score with the previous needle character matched at hay[j].
  let previous = new Float64Array(hay.length).fill(Number.NEGATIVE_INFINITY);
  for (let i = 0; i < needle.length; i++) {
    const current = new Float64Array(hay.length).fill(Number.NEGATIVE_INFINITY);
    let bestBefore = i === 0 ? 0 : Number.NEGATIVE_INFINITY;
    for (let j = 0; j < hay.length; j++) {
      if (hay[j] === needle[i]) {
        const run = j > 0 ? (previous[j - 1] ?? Number.NEGATIVE_INFINITY) + CONSECUTIVE : Number.NEGATIVE_INFINITY;
        const bonus = j === 0 || hay[j - 1] === "/" ? SEGMENT_START : 0;
        current[j] = 1 + bonus + Math.max(run, bestBefore);
      }
      // Ready for j + 1: any earlier match of the previous character can precede it.
      if (i > 0) {
        bestBefore = Math.max(bestBefore, previous[j] ?? Number.NEGATIVE_INFINITY);
      }
    }
    previous = current;
  }
  const best = needle.length === 0 ? 0 : Math.max(...previous);
  return best === Number.NEGATIVE_INFINITY ? null : best;
}
