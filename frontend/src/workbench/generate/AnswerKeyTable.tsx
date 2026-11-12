import type { components } from "@/api/schema";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";

type Hit = components["schemas"]["Hit"];
type Exposure = components["schemas"]["Exposure"];

/** What a tester checks a Hit by; the rest is in the Answer Key JSON (spec 13.3, 11.3). */
const COLUMNS: [string, (hit: Hit) => string | number | null | undefined][] = [
  ["Hit", (hit) => hit.id],
  ["Scope", (hit) => hit.scope],
  ["Transaction", (hit) => hit.transaction_number],
  ["End-to-end id", (hit) => hit.end_to_end_id],
  ["XPath", (hit) => hit.xpath],
  ["Placement", (hit) => hit.placement],
  ["Element", (hit) => hit.element],
  ["Rendering mode", (hit) => hit.rendering_mode],
  ["Entity", (hit) => hit.entity.id],
  ["Name Variant", (hit) => hit.name?.variant],
  ["Rendered name", (hit) => hit.name?.rendered],
  ["Scheme", (hit) => hit.name?.scheme],
  ["Operations", (hit) => hit.name?.operations?.join(" | ")],
  ["BIC", (hit) => hit.bic?.value],
  ["LEI", (hit) => hit.lei],
  ["Triggers", (hit) => hit.triggers.map((trigger) => trigger.kind).join(", ")],
  ["Lists", (hit) => [...new Set(hit.entity.listings.map((listing) => listing.list))].join(", ")],
  ["Origin", (hit) => hit.origin],
  ["Paired with", (hit) => hit.paired_with],
];

const CELL = "px-3.5 py-3";
const HEAD =
  "h-auto bg-secondary px-3.5 py-2.5 font-semibold text-[11px] text-muted-foreground uppercase tracking-[0.06em]";
const MONO = new Set(["Hit", "Transaction", "Element", "Entity"]);

/** One row per Hit, in Answer Key order. */
export function AnswerKeyTable({ hits }: { hits: Hit[] }) {
  if (hits.length === 0) {
    return <p className="p-[18px] text-muted-foreground text-sm">No Hits: this Sample File is clean.</p>;
  }
  return (
    <Table className="text-[13px]">
      <TableHeader>
        <TableRow>
          {COLUMNS.map(([label]) => (
            <TableHead key={label} className={HEAD}>
              {label}
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {hits.map((hit) => (
          <TableRow key={hit.id}>
            {COLUMNS.map(([label, value]) =>
              label === "XPath" ? (
                // Long paths are cut to keep the table readable; the tooltip has the whole one.
                <TableCell
                  key={label}
                  className={cn(CELL, "max-w-56 truncate font-mono text-label text-xs")}
                  title={hit.xpath}
                >
                  {hit.xpath}
                </TableCell>
              ) : label === "Placement" ? (
                <TableCell key={label} className={CELL}>
                  <span className="inline-flex h-[22px] items-center rounded px-2 font-medium text-primary text-xs bg-primary-soft">
                    {hit.placement}
                  </span>
                </TableCell>
              ) : (
                <TableCell key={label} className={cn(CELL, { "font-mono": MONO.has(label) })}>
                  {value(hit)}
                </TableCell>
              ),
            )}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

const EXPOSURE_COLUMNS: [string, (exposure: Exposure) => string | number][] = [
  ["Transaction", (exposure) => exposure.transaction_number],
  ["End-to-end id", (exposure) => exposure.end_to_end_id],
  ["Country", (exposure) => exposure.country],
  ["Currency", (exposure) => exposure.currency],
  ["Elements", (exposure) => exposure.elements.join(", ")],
];

/** One row per Exposure (spec 11.5): neither a Hit nor clean, so apart from the Hits. */
export function ExposuresTable({ exposures }: { exposures: Exposure[] }) {
  return (
    <Table aria-label="Exposures" className="text-[13px]">
      <TableHeader>
        <TableRow>
          {EXPOSURE_COLUMNS.map(([label]) => (
            <TableHead key={label} className={HEAD}>
              {label}
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {exposures.map((exposure) => (
          <TableRow key={exposure.transaction_number}>
            {EXPOSURE_COLUMNS.map(([label, value]) => (
              <TableCell key={label} className={cn(CELL, { "font-mono": label === "Transaction" })}>
                {value(exposure)}
              </TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
