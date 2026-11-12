import { Monitor, Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

/** Also read by the inline script in `index.html`, which applies the theme before first paint. */
export const THEME_KEY = "workbench.theme";

const THEMES = [
  { value: "light", label: "Light theme", Icon: Sun },
  { value: "dark", label: "Dark theme", Icon: Moon },
  { value: "system", label: "Match system theme", Icon: Monitor },
] as const;

type Theme = (typeof THEMES)[number]["value"];

function rememberedTheme(): Theme {
  try {
    const stored = window.localStorage.getItem(THEME_KEY);
    if (stored === "light" || stored === "dark") {
      return stored;
    }
  } catch {
    // localStorage can be blocked; System is the default.
  }
  return "system";
}

function rememberTheme(theme: Theme): void {
  try {
    if (theme === "system") {
      window.localStorage.removeItem(THEME_KEY);
    } else {
      window.localStorage.setItem(THEME_KEY, theme);
    }
  } catch {
    // Not remembering the theme is not an error.
  }
}

export const SEGMENTED = "inline-flex gap-0.5 rounded-lg border bg-secondary p-[3px]";
export const SEGMENT =
  "inline-flex h-8 items-center justify-center rounded-md px-3.5 font-medium text-label hover:text-foreground aria-pressed:bg-card aria-pressed:text-foreground aria-pressed:shadow-sm focus-visible:outline-2 focus-visible:outline-ring focus-visible:outline-offset-1";

/** Light, Dark or System; System follows `prefers-color-scheme` live. Toggles `.dark` on `<html>` (spec 13.1). */
export function ThemeSwitch() {
  const [theme, setTheme] = useState(rememberedTheme);

  useEffect(() => {
    const system = window.matchMedia("(prefers-color-scheme: dark)");
    const apply = () =>
      document.documentElement.classList.toggle("dark", theme === "dark" || (theme === "system" && system.matches));
    apply();
    if (theme !== "system") {
      return;
    }
    system.addEventListener("change", apply);
    return () => system.removeEventListener("change", apply);
  }, [theme]);

  return (
    // biome-ignore lint/a11y/useSemanticElements: a toggle of three pressed-state buttons, not a form fieldset
    <div role="group" aria-label="Colour theme" className={SEGMENTED}>
      {THEMES.map(({ value, label, Icon }) => (
        <button
          key={value}
          type="button"
          aria-label={label}
          title={label}
          aria-pressed={theme === value}
          onClick={() => {
            setTheme(value);
            rememberTheme(value);
          }}
          className={cn(SEGMENT, "w-8 px-0")}
        >
          <Icon className="size-4" aria-hidden />
        </button>
      ))}
    </div>
  );
}
