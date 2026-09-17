import { OutputPane } from "@/workbench/OutputPane";
import { SettingsPane } from "@/workbench/SettingsPane";
import { SETTINGS_WIDTH_MAX, SETTINGS_WIDTH_MIN, useSettingsPaneWidth } from "@/workbench/useSettingsPaneWidth";

export { SETTINGS_WIDTH_KEY } from "@/workbench/useSettingsPaneWidth";

/** One screen, no router: settings on the left, output on the right, a drag handle between them (spec 13.1). */
export function Workbench() {
  const { width, dragging, startResize } = useSettingsPaneWidth();

  return (
    <div
      className="mx-auto grid min-h-screen max-w-[1800px] gap-x-2 px-6 py-6"
      style={{ gridTemplateColumns: `${width}px 14px minmax(0, 1fr)`, cursor: dragging ? "col-resize" : undefined }}
    >
      <aside aria-label="Settings" className="min-w-0" style={{ width: `${width}px` }}>
        <SettingsPane />
      </aside>
      {/* biome-ignore lint/a11y/useSemanticElements: an interactive resize handle; hr is non-interactive and cannot carry the grip */}
      <div
        role="separator"
        aria-label="Resize settings pane"
        aria-orientation="vertical"
        aria-valuemin={SETTINGS_WIDTH_MIN}
        aria-valuemax={SETTINGS_WIDTH_MAX}
        aria-valuenow={width}
        title="Drag to resize"
        onMouseDown={startResize}
        className={`sticky top-6 h-[calc(100vh-3rem)] cursor-col-resize select-none rounded-md transition-colors hover:bg-accent ${dragging ? "bg-accent" : ""}`}
      >
        <div className="mx-auto mt-[calc(50vh-2.5rem)] h-10 w-1 rounded-full bg-border" />
      </div>
      <section aria-label="Output" className="min-w-0">
        <OutputPane />
      </section>
    </div>
  );
}
