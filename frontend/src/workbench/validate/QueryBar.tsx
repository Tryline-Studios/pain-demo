import { ChevronDown, ChevronUp } from "lucide-react";
import { type KeyboardEvent, useEffect, useId, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { INPUT } from "@/workbench/generate/FileSection";
import { rank } from "@/workbench/validate/fuzzyRank";
import type { QueryResult, XPathQuery } from "@/workbench/validate/xpathQuery";

const PLACEHOLDER = "/Document/CstmrCdtTrfInitn";
const PAUSE_MS = 150;
// Typeahead is for plain paths only: names, `/` and `//`.
const NOT_PLAIN = /[[(@| ]/;

/**
 * The XPath Query bar above the source view (spec 17.10): a combobox with path typeahead, Previous and Next buttons,
 * and a polite status line. A query runs 150 ms after the last keystroke; `onMatches` gets every match's line and the
 * current match's line (null for a scalar, no matches or an empty box), and is not called while the query is invalid.
 * `unavailable` disables the bar and says why.
 */
export function QueryBar({
  xpath,
  unavailable,
  query,
  onQueryChange,
  onMatches,
}: {
  xpath: XPathQuery | null;
  unavailable: string | null;
  query: string;
  onQueryChange: (query: string) => void;
  onMatches: (lines: number[], current: number | null) => void;
}) {
  const [result, setResult] = useState<QueryResult | null>(null);
  const [index, setIndex] = useState(0);
  const [listOpen, setListOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const listId = useId();

  const execute = (text: string) => {
    if (xpath === null) {
      return;
    }
    const next = text.trim() === "" ? null : xpath.run(text);
    setResult(next);
    setIndex(0);
    if (next === null || next.kind === "scalar") {
      onMatches([], null);
    } else if (next.kind === "nodes") {
      onMatches(next.lines, next.lines[0] ?? null);
    }
  };

  // biome-ignore lint/correctness/useExhaustiveDependencies: runs once per pause in typing and per message, not per render
  useEffect(() => {
    const timer = setTimeout(() => execute(query), PAUSE_MS);
    return () => clearTimeout(timer);
  }, [query, xpath]);

  const options = useMemo(
    () => (xpath === null || query === "" || NOT_PLAIN.test(query) ? [] : rank(query, xpath.paths)),
    [query, xpath],
  );
  const shown = listOpen && options.length > 0;
  const matches = result?.kind === "nodes" ? result.lines : [];

  const step = (delta: number) => {
    if (matches.length === 0) {
      return;
    }
    const next = (index + delta + matches.length) % matches.length;
    setIndex(next);
    onMatches(matches, matches[next] ?? null);
  };

  const accept = (path: string) => {
    onQueryChange(path);
    setListOpen(false);
    setActive(-1);
    execute(path);
  };

  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    const chosen = shown ? options[active] : undefined;
    if (shown && (event.key === "ArrowDown" || event.key === "ArrowUp")) {
      event.preventDefault();
      setActive(
        event.key === "ArrowDown" ? (active + 1) % options.length : (active <= 0 ? options.length : active) - 1,
      );
    } else if ((event.key === "Enter" || event.key === "Tab") && chosen !== undefined) {
      event.preventDefault();
      accept(chosen);
    } else if (event.key === "Enter") {
      event.preventDefault();
      setListOpen(false);
      step(event.shiftKey ? -1 : 1);
    } else if (event.key === "Tab" && query === "" && !event.shiftKey) {
      event.preventDefault();
      onQueryChange(PLACEHOLDER);
    } else if (event.key === "Escape" && shown) {
      event.preventDefault();
      setListOpen(false);
      setActive(-1);
    }
  };

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center gap-2">
        <div className="relative min-w-0 flex-1">
          <input
            type="text"
            role="combobox"
            aria-label="XPath Query"
            aria-autocomplete="list"
            aria-expanded={shown}
            aria-controls={listId}
            aria-activedescendant={shown && active >= 0 ? `${listId}-${active}` : undefined}
            className={INPUT}
            placeholder={PLACEHOLDER}
            spellCheck={false}
            autoComplete="off"
            disabled={unavailable !== null}
            value={query}
            onChange={(event) => {
              onQueryChange(event.target.value);
              setListOpen(true);
              setActive(-1);
            }}
            onKeyDown={onKeyDown}
            onBlur={() => setListOpen(false)}
          />
          <div
            id={listId}
            role="listbox"
            aria-label="Paths"
            hidden={!shown}
            className="absolute inset-x-0 top-full z-10 mt-1 overflow-hidden rounded-md border bg-popover py-1 font-mono text-xs shadow-md"
          >
            {shown
              ? options.map((path, at) => (
                  // The combobox pattern keeps focus and keys in the box (aria-activedescendant); options take clicks only.
                  // biome-ignore lint/a11y/useFocusableInteractive: focus stays in the combobox
                  // biome-ignore lint/a11y/useKeyWithClickEvents: the combobox handles the keys
                  <div
                    key={path}
                    id={`${listId}-${at}`}
                    role="option"
                    aria-selected={at === active}
                    className={cn("cursor-pointer truncate px-2.5 py-1", {
                      "bg-primary-soft text-primary": at === active,
                    })}
                    // Keeps focus in the box, so blur does not close the list before the click lands.
                    onMouseDown={(event) => event.preventDefault()}
                    onClick={() => accept(path)}
                  >
                    {path}
                  </div>
                ))
              : null}
          </div>
        </div>
        <Button
          variant="outline"
          size="icon"
          aria-label="Previous match"
          disabled={matches.length === 0}
          onClick={() => step(-1)}
        >
          <ChevronUp aria-hidden />
        </Button>
        <Button
          variant="outline"
          size="icon"
          aria-label="Next match"
          disabled={matches.length === 0}
          onClick={() => step(1)}
        >
          <ChevronDown aria-hidden />
        </Button>
      </div>
      <p role="status" aria-live="polite" className="min-h-4 truncate font-mono text-muted-foreground text-xs">
        {unavailable ?? statusOf(result, index)}
      </p>
    </div>
  );
}

function statusOf(result: QueryResult | null, index: number) {
  if (result === null) {
    return "";
  }
  if (result.kind === "error") {
    return `XPath error: ${result.message}`;
  }
  if (result.kind === "scalar") {
    return result.value;
  }
  const count = result.lines.length;
  if (count === 0) {
    return "0 matches";
  }
  return `${count} ${count === 1 ? "match" : "matches"} · ${index + 1} of ${count} · ${result.describe(index)}`;
}
