import { type KeyboardEvent, useState } from "react";
import { cn } from "@/lib/utils";
import { AppVersion } from "@/workbench/AppVersion";
import { useGeneration } from "@/workbench/generate/useGeneration";
import { OutputPane } from "@/workbench/OutputPane";
import { SettingsPane } from "@/workbench/SettingsPane";
import { segmentClass, segmentedGroupClass } from "@/workbench/segmented";
import { ThemeSwitch } from "@/workbench/ThemeSwitch";
import { SETTINGS_WIDTH_MAX, SETTINGS_WIDTH_MIN, useSettingsPaneWidth } from "@/workbench/useSettingsPaneWidth";
import { useValidation } from "@/workbench/validate/useValidation";
import { ValidateInput } from "@/workbench/validate/ValidateInput";
import { ValidationReportPane } from "@/workbench/validate/ValidationReportPane";

const MODES = ["Validate", "Generate"] as const;

/**
 * One screen, no router: settings on the left, output on the right, a drag handle between them (spec 13.1).
 * The Validate | Generate toggle (Validate by default) swaps what the two panes hold (spec 17.9).
 */
export function Workbench() {
  const { width, dragging, startResize, resizeByKey } = useSettingsPaneWidth();
  const [mode, setMode] = useState<(typeof MODES)[number]>("Validate");
  const validation = useValidation();
  const generation = useGeneration();
  const panes = {
    Generate: {
      inputLabel: "Settings",
      input: <SettingsPane generation={generation} />,
      outputLabel: "Output",
      output: (
        <OutputPane
          generation={generation}
          onValidate={(file) => {
            setMode("Validate");
            validation.validateFile(file);
          }}
        />
      ),
    },
    Validate: {
      inputLabel: "Message",
      input: <ValidateInput validation={validation} />,
      outputLabel: "Validation Report",
      output: <ValidationReportPane validation={validation} />,
    },
  }[mode];

  const onHandleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (resizeByKey(event.key)) {
      event.preventDefault();
    }
  };

  return (
    <div className={cn("flex min-h-screen flex-col", { "cursor-col-resize": dragging })}>
      <header className="flex flex-wrap items-center gap-x-6 gap-y-4 border-b bg-card px-6 py-3">
        <div className="flex flex-[1_1_200px] items-center gap-2.5">
          <svg width="28" height="28" viewBox="0 0 28 28" aria-hidden="true" className="shrink-0">
            <rect width="28" height="28" rx="6" className="fill-primary" />
            <g
              className="stroke-primary-foreground"
              fill="none"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M8 19V9h6.5a3.5 3.5 0 0 1 0 7H8" />
              <path d="M16 19h4" />
            </g>
          </svg>
          <div className="flex flex-wrap items-baseline gap-x-2">
            <h1 className="font-bold text-[15px] tracking-[-0.01em]">pain-workbench</h1>
            <span className="text-[13px] text-muted-foreground">ISO 20022 pain.001 Workbench</span>
          </div>
        </div>
        {/* biome-ignore lint/a11y/useSemanticElements: a toggle of two pressed-state buttons, not a form fieldset */}
        <div role="group" aria-label="Mode" className={segmentedGroupClass}>
          {MODES.map((name) => (
            <button
              key={name}
              type="button"
              aria-pressed={mode === name}
              onClick={() => setMode(name)}
              className={segmentClass}
            >
              {name}
            </button>
          ))}
        </div>
        <div className="flex flex-[1_1_200px] items-center justify-end gap-3.5">
          <ThemeSwitch />
          <AppVersion />
        </div>
      </header>
      <div className="flex flex-1 flex-col md:grid md:grid-cols-[auto_9px_minmax(0,1fr)]">
        <aside
          aria-label={panes.inputLabel}
          className="min-w-0 border-b bg-card p-6 max-md:w-full! md:border-b-0"
          style={{ width: `${width}px` }}
        >
          {panes.input}
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
            "cursor-col-resize select-none border-l outline-none transition-colors hover:bg-accent focus-visible:bg-accent focus-visible:ring-2 focus-visible:ring-ring max-md:hidden",
            { "bg-accent": dragging },
          )}
        >
          <div className="sticky top-[calc(50vh-1.25rem)] mx-auto mt-[calc(50vh-6rem)] h-10 w-1 rounded-full bg-border-strong" />
        </div>
        <section aria-label={panes.outputLabel} className="min-w-0 px-4 py-7 sm:px-8">
          {panes.output}
        </section>
      </div>
    </div>
  );
}
