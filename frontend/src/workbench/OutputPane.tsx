import type { ReactNode } from "react";
import { VersionTile } from "@/workbench/VersionTile";

export function Tile({ label, children }: { label: string; children: ReactNode }) {
  return (
    // biome-ignore lint/a11y/useSemanticElements: a summary tile is a labelled group with no form controls, so fieldset is the wrong element
    <div role="group" aria-label={label} className="rounded-xl border bg-card px-5 py-4">
      <div className="text-muted-foreground text-xs uppercase tracking-wide">{label}</div>
      <div className="mt-1 font-semibold text-2xl tabular-nums">{children}</div>
    </div>
  );
}

/** Summary tiles above the results; before the first generate, the empty state (spec 13.3). */
export function OutputPane() {
  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
        <Tile label="Transactions">–</Tile>
        <Tile label="Hits">–</Tile>
        <Tile label="Seed">–</Tile>
        <VersionTile />
      </div>
      <div className="flex min-h-[420px] flex-col items-center justify-center rounded-xl border border-dashed text-center">
        <p className="font-medium text-lg">No Sample File yet</p>
        <p className="mt-2 max-w-md text-muted-foreground text-sm">
          Set up the file on the left and press Generate. The Answer Key, the XML and any warnings will show here.
        </p>
      </div>
    </div>
  );
}
