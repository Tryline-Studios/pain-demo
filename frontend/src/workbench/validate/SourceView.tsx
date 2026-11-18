import { type RefObject, useEffect, useMemo, useRef, useState } from "react";
import { cn } from "@/lib/utils";
import { problemKey, type ValidationProblem } from "@/workbench/validate/useValidation";
import { XmlLine } from "@/workbench/XmlLine";
import { lineStates } from "@/workbench/xmlTokens";

/** Every source line and every inline problem is one row of this many pixels, so offsets are plain sums. */
const ROW = 20;

/**
 * The Uploaded Message with line numbers, each problem's `code` and `message` inline under its line (spec 17.9).
 * Windowed by hand: only the lines inside the viewport are in the DOM, so a 10 MB message stays responsive.
 * `lines` is the source split by `splitLines`. `target` scrolls to a line and marks it; pass a new object to jump again.
 */
export function SourceView({
  lines,
  problems,
  target,
  found = NOTHING_FOUND,
}: {
  lines: string[];
  problems: ValidationProblem[];
  target: { line: number } | null;
  /** The XPath Query's match lines (accent tint) and current match (accent bar); a new `current` scrolls to it. */
  found?: Found;
}) {
  const matched = useMemo(() => new Set(found.lines), [found.lines]);
  const currentLine = found.current?.line ?? null;
  const byLine = useMemo(() => {
    const grouped = new Map<number, ValidationProblem[]>();
    for (const problem of problems) {
      if (problem.line !== null) {
        grouped.set(problem.line, [...(grouped.get(problem.line) ?? []), problem]);
      }
    }
    return grouped;
  }, [problems]);
  // tops[i] is the pixel offset of line i + 1; tops[lines.length] is the full height.
  const tops = useMemo(() => {
    const offsets = new Float64Array(lines.length + 1);
    for (let at = 0; at < lines.length; at++) {
      offsets[at + 1] = (offsets[at] ?? 0) + ROW * (1 + (byLine.get(at + 1)?.length ?? 0));
    }
    return offsets;
  }, [lines, byLine]);
  // One cheap pass per source, so a comment or CDATA section opened above the window still colours lines inside it.
  const states = useMemo(() => lineStates(lines), [lines]);

  const scroller = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = useState(0);
  const topsRef = useRef(tops);
  topsRef.current = tops;

  // A problem jump and a query jump are separate targets; whichever changed last decides where the source is.
  useJump(target, topsRef, scroller, setScrollTop);
  useJump(found.current, topsRef, scroller, setScrollTop);

  // The scroller is at most 70vh tall, so the window height always covers it (and jsdom has no layout to measure).
  const start = Math.max(0, lineAt(tops, scrollTop) - 10);
  const end = Math.min(lines.length, lineAt(tops, scrollTop + window.innerHeight) + 10);
  const total = tops[lines.length] ?? 0;

  return (
    <div className="overflow-hidden rounded-[10px] border bg-card shadow-xs">
      <div className="flex items-center justify-between border-b px-[18px] py-3">
        <h2 className="font-semibold text-sm">Source</h2>
        <span className="font-mono text-muted-foreground text-xs">{lines.length.toLocaleString("en")} lines</span>
      </div>
      <div
        ref={scroller}
        onScroll={(event) => setScrollTop(event.currentTarget.scrollTop)}
        className="h-[70vh] overflow-auto bg-code font-mono text-xs leading-5"
      >
        <ol
          aria-label="Source"
          className="w-max min-w-full"
          style={{ paddingTop: tops[start], paddingBottom: total - (tops[end] ?? total) }}
        >
          {lines.slice(start, end).map((text, at) => {
            const line = start + at + 1;
            const lineProblems = byLine.get(line);
            // Validation Problems keep their red treatment over a query's accent.
            const tint = lineProblems ? "bg-destructive-soft" : matched.has(line) ? "bg-primary-soft" : undefined;
            return (
              <li
                key={line}
                aria-current={target?.line === line ? "location" : currentLine === line ? "step" : undefined}
                className={tint}
              >
                <div className="flex h-5">
                  <span
                    className={cn(
                      "sticky left-0 w-16 shrink-0 select-none pr-3.5 text-right tabular-nums",
                      lineProblems
                        ? "bg-destructive-soft text-destructive"
                        : tint
                          ? "bg-primary-soft text-primary"
                          : "bg-code text-line-number",
                      // The marked line's bar sits on the sticky number, so it stays put on horizontal scroll.
                      target?.line === line
                        ? "shadow-[inset_3px_0_0_var(--destructive)]"
                        : { "shadow-[inset_3px_0_0_var(--primary)]": currentLine === line },
                    )}
                  >
                    {line}
                  </span>
                  <span className="whitespace-pre pr-4">
                    <XmlLine line={text} state={states[line - 1]} />
                  </span>
                </div>
                {lineProblems?.map((problem) => (
                  <div
                    key={problemKey(problem)}
                    className="ml-16 h-5 whitespace-pre border-destructive border-l-2 pr-4 pl-3 font-sans text-destructive"
                  >
                    <code className="mr-2">{problem.code}</code>
                    {problem.message}
                  </div>
                ))}
              </li>
            );
          })}
        </ol>
      </div>
    </div>
  );
}

/** A null line is a match with no line of its own (the document, a comment beside the root): counted, never tinted. */
export type Found = { lines: (number | null)[]; current: { line: number } | null };

const NOTHING_FOUND: Found = { lines: [], current: null };

/**
 * Scrolls the source so `jump`'s line sits a third of the way down, each time a new `jump` object arrives. Only the
 * jump itself triggers it (row offsets are read through a ref), so new offsets never replay an older jump.
 */
function useJump(
  jump: { line: number } | null,
  tops: RefObject<Float64Array>,
  scroller: RefObject<HTMLDivElement | null>,
  setScrollTop: (top: number) => void,
) {
  useEffect(() => {
    const element = scroller.current;
    if (jump === null || element === null) {
      return;
    }
    const top = Math.max(0, (tops.current[jump.line - 1] ?? 0) - element.clientHeight / 3);
    element.scrollTop = top;
    setScrollTop(top);
  }, [jump, tops, scroller, setScrollTop]);
}

/** The source's lines as the report counts them: libxml2 normalises CRLF and lone CR to LF. */
export function splitLines(source: string) {
  return source.split(/\r\n?|\n/);
}

/** The index of the line whose row holds pixel `y`. */
function lineAt(tops: Float64Array, y: number) {
  let low = 0;
  let high = tops.length - 2;
  while (low < high) {
    const middle = (low + high + 1) >> 1;
    if ((tops[middle] ?? 0) <= y) {
      low = middle;
    } else {
      high = middle - 1;
    }
  }
  return low;
}
