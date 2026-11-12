import { useEffect, useMemo, useRef, useState } from "react";
import type { components } from "@/api/schema";
import { cn } from "@/lib/utils";

type ValidationProblem = components["schemas"]["ValidationProblem"];

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
}: {
  lines: string[];
  problems: ValidationProblem[];
  target: { line: number } | null;
}) {
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

  const scroller = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = useState(0);

  useEffect(() => {
    const element = scroller.current;
    if (target === null || element === null) {
      return;
    }
    const top = Math.max(0, (tops[target.line - 1] ?? 0) - element.clientHeight / 3);
    element.scrollTop = top;
    setScrollTop(top);
  }, [target, tops]);

  // The scroller is at most 70vh tall, so the window height always covers it (and jsdom has no layout to measure).
  const start = Math.max(0, lineAt(tops, scrollTop) - 10);
  const end = Math.min(lines.length, lineAt(tops, scrollTop + window.innerHeight) + 10);
  const total = tops[lines.length] ?? 0;

  return (
    <div
      ref={scroller}
      onScroll={(event) => setScrollTop(event.currentTarget.scrollTop)}
      className="h-[70vh] overflow-auto rounded-xl border bg-muted/30 font-mono text-xs leading-5"
    >
      <ol
        aria-label="Source"
        className="w-max min-w-full"
        style={{ paddingTop: tops[start], paddingBottom: total - (tops[end] ?? total) }}
      >
        {lines.slice(start, end).map((text, at) => {
          const line = start + at + 1;
          const lineProblems = byLine.get(line);
          return (
            <li
              key={line}
              aria-current={target?.line === line ? "location" : undefined}
              className={cn({
                "bg-destructive/10": lineProblems,
                "outline-2 outline-primary -outline-offset-2": target?.line === line,
              })}
            >
              <div className="flex h-5">
                <span className="sticky left-0 w-16 shrink-0 select-none bg-inherit pr-3 text-right text-muted-foreground tabular-nums">
                  {line}
                </span>
                <span className="whitespace-pre pr-4">{text}</span>
              </div>
              {lineProblems?.map((problem) => (
                <div
                  key={`${problem.column}:${problem.code}:${problem.path}:${problem.message}`}
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
  );
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
