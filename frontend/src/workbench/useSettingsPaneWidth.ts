import { useCallback, useEffect, useRef, useState } from "react";

/** The settings pane opens at 560px and resizes between 380px and 900px, remembered per browser (spec 13.1). */
export const SETTINGS_WIDTH_DEFAULT = 560;
export const SETTINGS_WIDTH_MIN = 380;
export const SETTINGS_WIDTH_MAX = 900;
export const SETTINGS_WIDTH_KEY = "workbench.settingsWidth";
export const KEYBOARD_STEP = 16;

function clamp(width: number): number {
  return Math.min(SETTINGS_WIDTH_MAX, Math.max(SETTINGS_WIDTH_MIN, width));
}

function rememberedWidth(): number {
  try {
    const stored = Number(window.localStorage.getItem(SETTINGS_WIDTH_KEY));
    if (Number.isFinite(stored) && stored >= SETTINGS_WIDTH_MIN && stored <= SETTINGS_WIDTH_MAX) {
      return stored;
    }
  } catch {
    // localStorage can be blocked; the default width is fine.
  }
  return SETTINGS_WIDTH_DEFAULT;
}

function rememberWidth(width: number): void {
  try {
    window.localStorage.setItem(SETTINGS_WIDTH_KEY, String(width));
  } catch {
    // Not remembering the width is not an error.
  }
}

export function useSettingsPaneWidth() {
  const [width, setWidth] = useState(rememberedWidth);
  const [dragging, setDragging] = useState(false);
  // The latest width as set by an event handler, independent of React's commit timing, so a mouseup right after
  // the last mousemove remembers the width that move produced.
  const latest = useRef(width);
  const drag = useRef<{ startX: number; startWidth: number } | null>(null);

  const apply = useCallback((next: number) => {
    latest.current = clamp(next);
    setWidth(latest.current);
  }, []);

  const startResize = useCallback((event: { clientX: number; preventDefault(): void }) => {
    event.preventDefault();
    drag.current = { startX: event.clientX, startWidth: latest.current };
    setDragging(true);
  }, []);

  const resizeByKey = useCallback(
    (key: string): boolean => {
      const steps: Record<string, number> = {
        ArrowLeft: latest.current - KEYBOARD_STEP,
        ArrowRight: latest.current + KEYBOARD_STEP,
        Home: SETTINGS_WIDTH_MIN,
        End: SETTINGS_WIDTH_MAX,
      };
      const next = steps[key];
      if (next === undefined) {
        return false;
      }
      apply(next);
      rememberWidth(latest.current);
      return true;
    },
    [apply],
  );

  useEffect(() => {
    if (!dragging) {
      return;
    }
    const move = (event: MouseEvent) => {
      if (drag.current !== null) {
        apply(drag.current.startWidth + event.clientX - drag.current.startX);
      }
    };
    const stop = () => {
      drag.current = null;
      setDragging(false);
      rememberWidth(latest.current);
    };
    window.addEventListener("mousemove", move);
    window.addEventListener("mouseup", stop);
    return () => {
      window.removeEventListener("mousemove", move);
      window.removeEventListener("mouseup", stop);
    };
  }, [dragging, apply]);

  return { width, dragging, startResize, resizeByKey };
}
