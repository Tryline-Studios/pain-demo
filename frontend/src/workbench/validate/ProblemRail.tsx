import { cn } from "@/lib/utils";
import { problemKey, type ValidationProblem } from "@/workbench/validate/useValidation";

/**
 * Every Validation Problem in report order: code, line and column, message, then the path and the parser's raw cause.
 * A problem with a line in the source is a button that jumps the source view to it, pressed while it is the chosen
 * one (`selected`, a `problemKey`); one without a line, or with a line past the end of a source of `lineCount` lines,
 * stays in the rail only.
 */
export function ProblemRail({
  problems,
  lineCount,
  selected,
  onJump,
}: {
  problems: ValidationProblem[];
  lineCount: number;
  selected: string | null;
  onJump: (line: number, key: string) => void;
}) {
  return (
    <ol aria-label="Validation Problems" className="flex flex-col gap-2.5">
      {problems.map((problem) => {
        const { line, column } = problem;
        // Spans, not paragraphs: a button holds phrasing content only.
        const body = (
          <>
            <span className="mb-2 flex flex-wrap items-center gap-2">
              <code className="rounded bg-destructive-soft px-2 py-0.5 font-medium text-destructive text-xs">
                {problem.code}
              </code>
              <span className="font-mono text-muted-foreground text-xs tabular-nums">
                {line === null ? "No line" : column === null ? `Line ${line}` : `Line ${line} · col ${column}`}
              </span>
            </span>
            <span className="block text-[13.5px] leading-normal">{problem.message}</span>
            {problem.path === null ? null : (
              <span className="mt-2 block break-all font-mono text-[11.5px] text-muted-foreground">{problem.path}</span>
            )}
            {problem.cause === null ? null : (
              <span className="mt-1 block break-words text-muted-foreground text-xs">{problem.cause}</span>
            )}
          </>
        );
        return (
          <li key={problemKey(problem)}>
            {line === null || line > lineCount ? (
              <div className="rounded-lg border bg-card p-3.5">{body}</div>
            ) : (
              <button
                type="button"
                aria-pressed={problemKey(problem) === selected}
                onClick={() => onJump(line, problemKey(problem))}
                className={cn(
                  "block w-full rounded-lg border bg-card p-3.5 text-left hover:border-border-strong focus-visible:outline-2 focus-visible:outline-ring focus-visible:outline-offset-2",
                  { "border-primary! ring-1 ring-primary": problemKey(problem) === selected },
                )}
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
