import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

/** A summary tile: a label and one value (spec 13.3). A verdict tile is red when invalid and green when valid. */
export function Tile({ label, tone, children }: { label: string; tone?: "valid" | "invalid"; children: ReactNode }) {
  return (
    // biome-ignore lint/a11y/useSemanticElements: a summary tile is a labelled group with no form controls, so fieldset is the wrong element
    <div
      role="group"
      aria-label={label}
      className={cn("min-w-0 rounded-[10px] border bg-card px-[18px] py-4 shadow-xs", {
        "border-destructive bg-destructive-soft text-destructive": tone === "invalid",
        "border-success bg-success-soft text-success": tone === "valid",
      })}
    >
      <div className={cn("font-medium text-xs", tone === undefined ? "text-label" : "text-inherit")}>{label}</div>
      <div className="mt-1 flex min-h-9 items-center gap-2 font-semibold text-[26px] tabular-nums tracking-[-0.02em]">
        {children}
      </div>
    </div>
  );
}

/** A code-like tile value (a Message Version, a Seed, an encoding), set in the mono face. */
export function MonoValue({ children, title }: { children: ReactNode; title?: string }) {
  return (
    <span className="block truncate font-medium font-mono text-base tracking-normal" title={title}>
      {children}
    </span>
  );
}

/** The tiles' grid: as many 170px columns as fit, one per row at phone width. */
export const TILES = "grid grid-cols-[repeat(auto-fit,minmax(170px,1fr))] gap-3";
