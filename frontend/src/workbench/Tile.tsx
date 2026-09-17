import type { ReactNode } from "react";

/** A summary tile: a label and one value (spec 13.3). */
export function Tile({ label, children }: { label: string; children: ReactNode }) {
  return (
    // biome-ignore lint/a11y/useSemanticElements: a summary tile is a labelled group with no form controls, so fieldset is the wrong element
    <div role="group" aria-label={label} className="rounded-xl border bg-card px-5 py-4">
      <div className="text-muted-foreground text-xs uppercase tracking-wide">{label}</div>
      <div className="mt-1 font-semibold text-2xl tabular-nums">{children}</div>
    </div>
  );
}
