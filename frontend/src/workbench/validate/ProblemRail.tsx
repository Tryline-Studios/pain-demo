import type { components } from "@/api/schema";

type ValidationProblem = components["schemas"]["ValidationProblem"];

/**
 * Every Validation Problem in report order: code, line, message, then the path and the parser's raw cause.
 * A problem with a line in the source is a button that jumps the source view to it; one without a line, or with
 * a line past the end of a source of `lineCount` lines, stays in the rail only.
 */
export function ProblemRail({
  problems,
  lineCount,
  onJump,
}: {
  problems: ValidationProblem[];
  lineCount: number;
  onJump: (line: number) => void;
}) {
  return (
    <ol aria-label="Validation Problems" className="flex flex-col gap-3">
      {problems.map((problem) => {
        const { line } = problem;
        // Spans, not paragraphs: a button holds phrasing content only.
        const body = (
          <>
            <span className="flex items-center gap-2">
              <code className="rounded bg-destructive/10 px-1.5 py-0.5 text-destructive text-xs">{problem.code}</code>
              <span className="text-muted-foreground text-xs tabular-nums">
                {line === null ? "No line" : `Line ${line}`}
              </span>
            </span>
            <span className="mt-2 block">{problem.message}</span>
            {problem.path === null ? null : (
              <span className="mt-2 block break-all font-mono text-muted-foreground text-xs">{problem.path}</span>
            )}
            {problem.cause === null ? null : (
              <span className="mt-1 block break-words text-muted-foreground text-xs">{problem.cause}</span>
            )}
          </>
        );
        return (
          <li
            // Problems carry no id; this tuple is unique within one report.
            key={`${line}:${problem.column}:${problem.code}:${problem.path}:${problem.message}`}
            className="rounded-xl border bg-card text-sm"
          >
            {line === null || line > lineCount ? (
              <div className="px-4 py-3">{body}</div>
            ) : (
              <button
                type="button"
                onClick={() => onJump(line)}
                className="block w-full rounded-xl px-4 py-3 text-left hover:bg-accent focus-visible:outline-2 focus-visible:outline-ring"
              >
                {body}
              </button>
            )}
          </li>
        );
      })}
    </ol>
  );
}
