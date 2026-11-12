import { type KeyboardEvent, useState } from "react";
import { cn } from "@/lib/utils";
import { OutputPane } from "@/workbench/OutputPane";
import { SettingsPane } from "@/workbench/SettingsPane";
import { SETTINGS_WIDTH_MAX, SETTINGS_WIDTH_MIN, useSettingsPaneWidth } from "@/workbench/useSettingsPaneWidth";
import { useValidation } from "@/workbench/validate/useValidation";
import { ValidateInput } from "@/workbench/validate/ValidateInput";
import { ValidationReportPane } from "@/workbench/validate/ValidationReportPane";

const MODES = ["Generate", "Validate"] as const;

/**
 * One screen, no router: settings on the left, output on the right, a drag handle between them (spec 13.1).
 * The Generate | Validate toggle swaps what the two panes hold (spec 17.9).
 */
export function Workbench() {
  const { width, dragging, startResize, resizeByKey } = useSettingsPaneWidth();
  const [mode, setMode] = useState<(typeof MODES)[number]>("Generate");
  const validation = useValidation();

  const onHandleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (resizeByKey(event.key)) {
      event.preventDefault();
    }
  };

  return (
    <div
      className={cn("mx-auto grid min-h-screen max-w-[1800px] grid-cols-[auto_14px_minmax(0,1fr)] gap-x-2 px-6 py-6", {
        "cursor-col-resize": dragging,
      })}
    >
      {/* biome-ignore lint/a11y/useSemanticElements: a toggle of two pressed-state buttons, not a form fieldset */}
      <div role="group" aria-label="Mode" className="col-span-3 mb-6 inline-flex w-fit rounded-lg border bg-card p-1">
        {MODES.map((name) => (
          <button
            key={name}
            type="button"
            aria-pressed={mode === name}
            onClick={() => setMode(name)}
            className={cn("rounded-md px-4 py-1.5 font-medium text-sm", {
              "bg-primary text-primary-foreground": mode === name,
            })}
          >
            {name}
          </button>
        ))}
      </div>
      <aside
        aria-label={mode === "Generate" ? "Settings" : "Message"}
        className="min-w-0"
        style={{ width: `${width}px` }}
      >
        {mode === "Generate" ? <SettingsPane /> : <ValidateInput validation={validation} />}
      </aside>
      {/* biome-ignore lint/a11y/useSemanticElements: an interactive resize handle; hr is non-interactive and cannot carry the grip */}
      <div
        role="separator"
        tabIndex={0}
        aria-label="Resize settings pane"
        aria-orientation="vertical"
        aria-valuemin={SETTINGS_WIDTH_MIN}
        aria-valuemax={SETTINGS_WIDTH_MAX}
        aria-valuenow={width}
        title="Drag to resize"
        onMouseDown={startResize}
        onKeyDown={onHandleKeyDown}
        className={cn(
          "sticky top-6 h-[calc(100vh-3rem)] cursor-col-resize select-none rounded-md outline-none transition-colors hover:bg-accent focus-visible:ring-2 focus-visible:ring-ring",
          { "bg-accent": dragging },
        )}
      >
        <div className="mx-auto mt-[calc(50vh-2.5rem)] h-10 w-1 rounded-full bg-border" />
      </div>
      {mode === "Generate" ? (
        <section aria-label="Output" className="min-w-0">
          <OutputPane />
        </section>
      ) : (
        <section aria-label="Validation Report" className="min-w-0">
          <ValidationReportPane validation={validation} />
        </section>
      )}
    </div>
  );
}
