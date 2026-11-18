import { Check, CircleAlert, FileText } from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import { ProblemBlock } from "@/workbench/ProblemBlock";
import { MonoValue, TILES, Tile } from "@/workbench/Tile";
import { ProblemRail } from "@/workbench/validate/ProblemRail";
import { QueryBar } from "@/workbench/validate/QueryBar";
import { type Found, SourceView, splitLines } from "@/workbench/validate/SourceView";
import type { Validation, ValidationProblem } from "@/workbench/validate/useValidation";
import { buildXPathQuery } from "@/workbench/validate/xpathQuery";

/** The right pane in Validate mode: summary tiles, the file line and the problems (spec 17.9). */
export function ValidationReportPane({ validation }: { validation: Validation }) {
  const report = validation.data;
  // Kept across uploads, so the same query runs again on the next message.
  const [query, setQuery] = useState("");

  return (
    <div className="flex flex-col gap-6">
      {report === undefined ? null : (
        <div className="flex items-center gap-3 rounded-[10px] border bg-card px-[18px] py-4">
          <FileText className="size-5 shrink-0 text-muted-foreground" aria-hidden />
          <div className="min-w-0">
            <div className="truncate font-medium font-mono text-[13px]">{report.file.name ?? "Pasted XML"}</div>
            <div className="flex flex-wrap gap-x-3 text-muted-foreground text-xs">
              <span>{report.file.size_bytes.toLocaleString("en")} bytes</span>
              <span className="font-mono" title={report.file.sha256}>
                sha256 {report.file.sha256.slice(0, 12)}
              </span>
            </div>
          </div>
        </div>
      )}
      <div className={TILES}>
        <Tile label="Verdict" tone={report === undefined ? undefined : report.valid ? "valid" : "invalid"}>
          {report === undefined ? null : report.valid ? (
            <Check className="size-5" strokeWidth={2.4} aria-hidden />
          ) : (
            <CircleAlert className="size-5" strokeWidth={2.4} aria-hidden />
          )}
          <span className="text-xl">{verdict(validation)}</span>
        </Tile>
        <Tile label="Problems">{problemCount(validation.data)}</Tile>
        <Tile label="Message Version">
          <MonoValue>{report?.message_version ?? "–"}</MonoValue>
        </Tile>
        <Tile label="Transactions">{report?.transaction_count ?? "–"}</Tile>
        <Tile label="Encoding">
          <MonoValue>{report?.encoding ?? "–"}</MonoValue>
        </Tile>
      </div>
      {validation.isError ? <ProblemBlock error={validation.error} /> : null}
      {validation.isIdle ? (
        <div className="flex min-h-[420px] flex-col items-center justify-center rounded-[10px] border border-border-strong border-dashed bg-card px-4 text-center">
          <p className="font-semibold text-lg">No message validated yet</p>
          <p className="mt-2 max-w-md text-muted-foreground text-sm">
            Choose a file or paste XML on the left. The verdict and every Validation Problem will show here.
          </p>
        </div>
      ) : null}
      {report === undefined ? null : (
        <>
          {report.valid ? (
            <div className="rounded-[10px] border border-success bg-success-soft p-8 text-center text-success">
              <p className="font-semibold text-lg">No problems found</p>
            </div>
          ) : null}
          {report.truncated ? (
            <p className="text-muted-foreground text-sm">Only the first 100 problems are shown.</p>
          ) : null}
          {/* Keyed by submission so a new report starts at the top with no line marked. */}
          <SourceAndRail
            key={validation.submittedAt}
            source={validation.source}
            problems={report.problems}
            query={query}
            onQueryChange={setQuery}
          />
        </>
      )}
    </div>
  );
}

function verdict({ isPending, data }: Validation) {
  if (isPending) {
    return "…";
  }
  if (data === undefined) {
    return "–";
  }
  return data.valid ? "Valid" : "Invalid";
}

/** The report caps its problems at 100 and says so with `truncated`. */
function problemCount(report: Validation["data"]) {
  if (report === undefined) {
    return "–";
  }
  return report.truncated ? "100+" : report.problems.length;
}

const MALFORMED = "XPath Query is off: the Uploaded Message is not well-formed XML";

/** Why the XPath Query is off: the browser parser must never see a malformed message or a DTD (spec 17.3, 17.10). */
function unavailableReason(problems: ValidationProblem[]) {
  if (problems.some((problem) => problem.code === "malformed_xml")) {
    return MALFORMED;
  }
  if (problems.some((problem) => problem.code === "dtd_not_allowed")) {
    return "XPath Query is off: the Uploaded Message carries a DTD";
  }
  return null;
}

/**
 * The XPath Query bar over the source view, with the problem rail on its right. Clicking a problem scrolls the source
 * to its line; the query's matches stay tinted, and whichever jump came last decides where the source is.
 */
function SourceAndRail({
  source,
  problems,
  query,
  onQueryChange,
}: {
  source: string;
  problems: ValidationProblem[];
  query: string;
  onQueryChange: (query: string) => void;
}) {
  // `key` tells apart two problems on one line, so only the chosen card is marked.
  const [target, setTarget] = useState<{ line: number; key: string } | null>(null);
  const [found, setFound] = useState<Found>({ lines: [], current: null });
  const lines = useMemo(() => splitLines(source), [source]);
  const blocked = unavailableReason(problems);
  const xpath = useMemo(() => (blocked === null ? buildXPathQuery(lines) : null), [blocked, lines]);
  const onMatches = useCallback(
    (matched: number[], current: number | null) =>
      setFound({ lines: matched, current: current === null ? null : { line: current } }),
    [],
  );
  const sourcePanel = (
    <div className="flex flex-col gap-2">
      <QueryBar
        xpath={xpath}
        unavailable={blocked ?? (xpath === null ? MALFORMED : null)}
        query={query}
        onQueryChange={onQueryChange}
        onMatches={onMatches}
      />
      <SourceView lines={lines} problems={problems} target={target} found={found} />
    </div>
  );
  if (problems.length === 0) {
    return sourcePanel;
  }
  return (
    <div className="flex flex-wrap items-start gap-4">
      <div className="min-w-0 flex-[999_1_520px]">{sourcePanel}</div>
      <section aria-labelledby="problems-heading" className="flex min-w-0 flex-[1_1_340px] flex-col gap-2.5">
        <div className="flex items-center justify-between">
          <h2 id="problems-heading" className="font-semibold text-sm">
            Validation Problems
          </h2>
          <span className="text-muted-foreground text-xs">XSD layer</span>
        </div>
        <div className="lg:max-h-[70vh] lg:overflow-auto">
          <ProblemRail
            problems={problems}
            lineCount={lines.length}
            selected={target?.key ?? null}
            onJump={(line, key) => setTarget({ line, key })}
          />
        </div>
      </section>
    </div>
  );
}
