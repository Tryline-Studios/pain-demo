import type { components } from "@/api/schema";

/** The problem details body our API sends for a refused request (spec 12.3); `errors` only on a 422. */
type ProblemDetails = Partial<components["schemas"]["RequestValidationProblem"]>;

/** A refused request, shown where its result would have gone (spec 13.3). A network failure has no body. */
export function ProblemBlock({ error }: { error: unknown }) {
  const problem: ProblemDetails =
    error instanceof Error
      ? { title: "The request failed", detail: error.message }
      : typeof error === "object" && error !== null
        ? (error as ProblemDetails)
        : {};

  return (
    <div role="alert" className="rounded-xl border border-destructive/50 bg-destructive/5 p-5 text-sm">
      <p className="font-medium text-destructive">
        {problem.title ?? "The request was refused"}
        {problem.status === undefined ? null : <span className="ml-2 tabular-nums">({problem.status})</span>}
      </p>
      {problem.detail === undefined ? null : <p className="mt-1">{problem.detail}</p>}
      {problem.errors === undefined ? null : (
        <ul className="mt-2 list-disc pl-5">
          {problem.errors.map((fieldError) => (
            <li key={`${fieldError.field}:${fieldError.message}`}>
              <code className="text-xs">{fieldError.field}</code>: {fieldError.message}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
