import { useCallback, useEffect, useRef, useState } from "react";

/** The settings pane opens at 560px and resizes between 380px and 900px, remembered per browser (spec 13.1). */
export const SETTINGS_WIDTH_DEFAULT = 560;
export const SETTINGS_WIDTH_MIN = 380;
export const SETTINGS_WIDTH_MAX = 900;
export const SETTINGS_WIDTH_KEY = "workbench.settingsWidth";

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
  const drag = useRef<{ startX: number; startWidth: number } | null>(null);
  const widthRef = useRef(width);
  widthRef.current = width;

  const startResize = useCallback((event: { clientX: number; preventDefault(): void }) => {
    event.preventDefault();
    drag.current = { startX: event.clientX, startWidth: widthRef.current };
    setDragging(true);
  }, []);

  useEffect(() => {
    if (!dragging) {
      return;
    }
    const move = (event: MouseEvent) => {
      if (drag.current !== null) {
        setWidth(clamp(drag.current.startWidth + event.clientX - drag.current.startX));
      }
    };
    const stop = () => {
      drag.current = null;
      setDragging(false);
      rememberWidth(widthRef.current);
    };
    window.addEventListener("mousemove", move);
    window.addEventListener("mouseup", stop);
    return () => {
      window.removeEventListener("mousemove", move);
      window.removeEventListener("mouseup", stop);
    };
  }, [dragging]);

  return { width, dragging, startResize };
}
