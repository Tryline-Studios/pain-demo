import type { components } from "@/api/schema";

type ValidationProblem = components["schemas"]["ValidationProblem"];

/** Every Validation Problem in report order: code, line, message, then the path and the parser's raw cause. */
export function ProblemRail({ problems }: { problems: ValidationProblem[] }) {
  return (
    <ol aria-label="Validation Problems" className="flex flex-col gap-3">
      {problems.map((problem) => (
        <li
          // Problems carry no id; this tuple is unique within one report.
          key={`${problem.line}:${problem.column}:${problem.code}:${problem.path}:${problem.message}`}
          className="rounded-xl border bg-card px-4 py-3 text-sm"
        >
          <div className="flex items-center gap-2">
            <code className="rounded bg-destructive/10 px-1.5 py-0.5 text-destructive text-xs">{problem.code}</code>
            <span className="text-muted-foreground text-xs tabular-nums">
              {problem.line === null ? "No line" : `Line ${problem.line}`}
            </span>
          </div>
          <p className="mt-2">{problem.message}</p>
          {problem.path === null ? null : (
            <p className="mt-2 break-all font-mono text-muted-foreground text-xs">{problem.path}</p>
          )}
          {problem.cause === null ? null : (
            <p className="mt-1 break-words text-muted-foreground text-xs">{problem.cause}</p>
          )}
        </li>
      ))}
    </ol>
  );
}
