import { useState } from "react";
import type { components } from "@/api/schema";
import { ProblemBlock } from "@/workbench/ProblemBlock";
import { Tile } from "@/workbench/Tile";
import { ProblemRail } from "@/workbench/validate/ProblemRail";
import { SourceView } from "@/workbench/validate/SourceView";
import type { Validation } from "@/workbench/validate/useValidation";

type ValidationProblem = components["schemas"]["ValidationProblem"];

/** The right pane in Validate mode: summary tiles, the file line and the problems (spec 17.9). */
export function ValidationReportPane({ validation }: { validation: Validation }) {
  const report = validation.data;

  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-2 gap-4 xl:grid-cols-5">
        <Tile label="Verdict">{validation.isPending ? "…" : report ? (report.valid ? "Valid" : "Invalid") : "–"}</Tile>
        <Tile label="Message Version">{report?.message_version ?? "–"}</Tile>
        <Tile label="Transactions">{report?.transaction_count ?? "–"}</Tile>
        <Tile label="Problems">{report ? (report.truncated ? "100+" : report.problems.length) : "–"}</Tile>
        <Tile label="Encoding">{report?.encoding ?? "–"}</Tile>
      </div>
      {validation.isError ? <ProblemBlock error={validation.error} /> : null}
      {validation.isIdle ? (
        <div className="flex min-h-[420px] flex-col items-center justify-center rounded-xl border border-dashed text-center">
          <p className="font-medium text-lg">No message validated yet</p>
          <p className="mt-2 max-w-md text-muted-foreground text-sm">
            Choose a file or paste XML on the left. The verdict and every Validation Problem will show here.
          </p>
        </div>
      ) : null}
      {report === undefined ? null : (
        <>
          <p className="flex flex-wrap gap-x-3 text-muted-foreground text-sm">
            <span className="font-medium text-foreground">{report.file.name ?? "Pasted XML"}</span>
            <span>{report.file.size_bytes.toLocaleString("en")} bytes</span>
            <span className="font-mono" title={report.file.sha256}>
              sha256 {report.file.sha256.slice(0, 12)}
            </span>
          </p>
          {report.valid ? (
            <div className="rounded-xl border border-green-600/40 bg-green-600/5 p-8 text-center">
              <p className="font-medium text-lg">No problems found</p>
            </div>
          ) : null}
          {report.truncated ? <p className="text-muted-foreground text-sm">Only the first 100 problems are shown.</p> : null}
          {/* Keyed by submission so a new report starts at the top with no line marked. */}
          <SourceAndRail key={validation.submittedAt} source={validation.source} problems={report.problems} />
        </>
      )}
    </div>
  );
}

/** The source view with the problem rail on its right; clicking a problem scrolls the source to its line. */
function SourceAndRail({ source, problems }: { source: string; problems: ValidationProblem[] }) {
  const [target, setTarget] = useState<{ line: number } | null>(null);
  if (problems.length === 0) {
    return <SourceView source={source} problems={problems} target={null} />;
  }
  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_340px]">
      <SourceView source={source} problems={problems} target={target} />
      <div className="lg:max-h-[70vh] lg:overflow-auto">
        <ProblemRail problems={problems} onJump={(line) => setTarget({ line })} />
      </div>
    </div>
  );
}
