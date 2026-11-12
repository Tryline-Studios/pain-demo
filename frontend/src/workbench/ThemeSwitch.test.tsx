import { act, fireEvent, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { renderWithQueries } from "@/test/render";
import { THEME_KEY } from "@/workbench/ThemeSwitch";
import { Workbench } from "@/workbench/Workbench";

/** A `prefers-color-scheme: dark` query the test can flip, as the OS would. */
function mockSystemScheme(dark: boolean) {
  const listeners = new Set<() => void>();
  let matches = dark;
  window.matchMedia = vi.fn(
    () =>
      ({
        get matches() {
          return matches;
        },
        addEventListener: (_type: string, listener: () => void) => listeners.add(listener),
        removeEventListener: (_type: string, listener: () => void) => listeners.delete(listener),
      }) as unknown as MediaQueryList,
  );
  return (next: boolean) => {
    matches = next;
    act(() => {
      for (const listener of listeners) {
        listener();
      }
    });
  };
}

function themeButton(name: string) {
  return within(screen.getByRole("group", { name: "Colour theme" })).getByRole("button", { name });
}

function isDark() {
  return document.documentElement.classList.contains("dark");
}

describe("Theme switch", () => {
  it("follows the system colour scheme by default, live", () => {
    const setSystemDark = mockSystemScheme(true);
    renderWithQueries(<Workbench />);

    expect(themeButton("Match system theme")).toHaveAttribute("aria-pressed", "true");
    expect(isDark()).toBe(true);
    setSystemDark(false);
    expect(isDark()).toBe(false);
    setSystemDark(true);
    expect(isDark()).toBe(true);
  });

  it("applies Light and Dark whatever the system says", () => {
    const setSystemDark = mockSystemScheme(true);
    renderWithQueries(<Workbench />);

    fireEvent.click(themeButton("Light theme"));
    expect(themeButton("Light theme")).toHaveAttribute("aria-pressed", "true");
    expect(themeButton("Match system theme")).toHaveAttribute("aria-pressed", "false");
    expect(isDark()).toBe(false);

    fireEvent.click(themeButton("Dark theme"));
    setSystemDark(false);
    expect(isDark()).toBe(true);
  });

  it("remembers the choice across a remount", () => {
    mockSystemScheme(false);
    const first = renderWithQueries(<Workbench />);
    fireEvent.click(themeButton("Dark theme"));
    expect(window.localStorage.getItem(THEME_KEY)).toBe("dark");
    first.unmount();

    renderWithQueries(<Workbench />);
    expect(themeButton("Dark theme")).toHaveAttribute("aria-pressed", "true");
    expect(isDark()).toBe(true);
  });

  it("falls back to System when the store is blocked", () => {
    mockSystemScheme(true);
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new DOMException("blocked", "SecurityError");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("blocked", "SecurityError");
    });
    renderWithQueries(<Workbench />);

    expect(themeButton("Match system theme")).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(themeButton("Light theme"));
    expect(isDark()).toBe(false);
  });
});
