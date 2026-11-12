import type { components } from "@/api/schema";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

type Hit = components["schemas"]["Hit"];

/** What a tester checks a Hit by; the rest is in the Answer Key JSON (spec 13.3, 11.3). */
const COLUMNS: [string, (hit: Hit) => string | number | null | undefined][] = [
  ["Hit", (hit) => hit.id],
  ["Scope", (hit) => hit.scope],
  ["Transaction", (hit) => hit.transaction_number],
  ["End-to-end id", (hit) => hit.end_to_end_id],
  ["XPath", (hit) => hit.xpath],
  ["Placement", (hit) => hit.placement],
  ["Rendering mode", (hit) => hit.rendering_mode],
  ["Entity", (hit) => hit.entity.id],
  ["Name Variant", (hit) => hit.name?.variant],
  ["Rendered name", (hit) => hit.name?.rendered],
  ["BIC", (hit) => hit.bic?.value],
  ["LEI", (hit) => hit.lei],
  ["Triggers", (hit) => hit.triggers.map((trigger) => trigger.kind).join(", ")],
  ["Lists", (hit) => [...new Set(hit.entity.listings.map((listing) => listing.list))].join(", ")],
];

/** One row per Hit, in Answer Key order. */
export function AnswerKeyTable({ hits }: { hits: Hit[] }) {
  if (hits.length === 0) {
    return <p className="text-muted-foreground text-sm">No Hits: this Sample File is clean.</p>;
  }
  return (
    <div className="rounded-xl border bg-card">
      <Table className="text-xs">
        <TableHeader>
          <TableRow>
            {COLUMNS.map(([label]) => (
              <TableHead key={label}>{label}</TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {hits.map((hit) => (
            <TableRow key={hit.id}>
              {COLUMNS.map(([label, value]) =>
                label === "XPath" ? (
                  // Long paths are cut to keep the table readable; the tooltip has the whole one.
                  <TableCell key={label} className="max-w-56 truncate" title={hit.xpath}>
                    {hit.xpath}
                  </TableCell>
                ) : (
                  <TableCell key={label}>{value(hit)}</TableCell>
                ),
              )}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
