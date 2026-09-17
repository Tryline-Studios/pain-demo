import type { KeyboardEvent } from "react";
import { cn } from "@/lib/utils";
import { OutputPane } from "@/workbench/OutputPane";
import { SettingsPane } from "@/workbench/SettingsPane";
import { SETTINGS_WIDTH_MAX, SETTINGS_WIDTH_MIN, useSettingsPaneWidth } from "@/workbench/useSettingsPaneWidth";

/** One screen, no router: settings on the left, output on the right, a drag handle between them (spec 13.1). */
export function Workbench() {
  const { width, dragging, startResize, resizeByKey } = useSettingsPaneWidth();

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
      <aside aria-label="Settings" className="min-w-0" style={{ width: `${width}px` }}>
        <SettingsPane />
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
      <section aria-label="Output" className="min-w-0">
        <OutputPane />
      </section>
    </div>
  );
}
