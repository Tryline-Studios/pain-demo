import { ChevronDown, ChevronUp } from "lucide-react";
import { type KeyboardEvent, useEffect, useId, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { INPUT } from "@/workbench/generate/FileSection";
import { rank } from "@/workbench/validate/fuzzyRank";
import type { QueryResult, XPathQuery } from "@/workbench/validate/xpathQuery";

const PLACEHOLDER = "/Document/CstmrCdtTrfInitn";
const PAUSE_MS = 150;

type Ran = { text: string; result: QueryResult | null };
// Typeahead is for plain paths only: names, `/` and `//`.
const NOT_PLAIN = /[[(@| ]/;

/**
 * The XPath Query bar above the source view (spec 17.10): a combobox with path typeahead, Previous and Next buttons,
 * and a polite status line. A query runs 150 ms after the last keystroke, or at once when a suggestion is accepted or
 * Enter, Previous or Next comes first. `onMatches` gets every match's line and the current match's line (null for a
 * scalar, an error, no matches or an empty box). `getXPath` builds the message's query engine on first use.
 * `unavailable` disables the bar and says why.
 */
export function QueryBar({
  getXPath,
  unavailable,
  query,
  onQueryChange,
  onMatches,
}: {
  getXPath: () => XPathQuery | null;
  unavailable: string | null;
  query: string;
  onQueryChange: (query: string) => void;
  onMatches: (lines: (number | null)[], current: number | null) => void;
}) {
  // The last query run and its result; `text` tells whether the box has changed since.
  const [ran, setRan] = useState<Ran>({ text: "", result: null });
  const [index, setIndex] = useState(0);
  const [listOpen, setListOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const listId = useId();

  const execute = (text: string): Ran => {
    const xpath = text.trim() === "" ? null : getXPath();
    const result =
      text.trim() === ""
        ? null
        : (xpath?.run(text) ?? { kind: "error" as const, message: "the browser cannot parse this message" });
    const next = { text, result };
    setRan(next);
    setIndex(0);
    if (result?.kind === "nodes") {
      onMatches(result.lines, result.lines[0] ?? null);
    } else {
      // Highlights never outlive the query that made them, even while the new one is invalid.
      onMatches([], null);
    }
    return next;
  };

  // biome-ignore lint/correctness/useExhaustiveDependencies: runs once per pause in typing, not per render
  useEffect(() => {
    if (ran.text === query) {
      return;
    }
    const timer = setTimeout(() => execute(query), PAUSE_MS);
    return () => clearTimeout(timer);
  }, [query, ran.text]);

  const options = useMemo(() => {
    const xpath = query === "" || NOT_PLAIN.test(query) ? null : getXPath();
    return xpath === null ? [] : rank(query, xpath.paths);
  }, [query, getXPath]);
  const shown = listOpen && options.length > 0;
  const { result } = ran;
  const matches = result?.kind === "nodes" ? result.lines : [];

  const step = (delta: number) => {
    // A query still inside its pause runs first, so the step lands on its matches, not the last query's.
    const fresh = ran.text === query ? null : execute(query).result;
    const lines = fresh === null ? matches : fresh.kind === "nodes" ? fresh.lines : [];
    if (lines.length === 0) {
      return;
    }
    const next = ((fresh === null ? index : 0) + delta + lines.length) % lines.length;
    setIndex(next);
    onMatches(lines, lines[next] ?? null);
  };

  const accept = (path: string) => {
    onQueryChange(path);
    setListOpen(false);
    setActive(-1);
    execute(path);
  };

  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    const chosen = shown ? options[active] : undefined;
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      if (options.length === 0) {
        return;
      }
      event.preventDefault();
      setListOpen(true);
      const from = shown ? active : -1;
      setActive(event.key === "ArrowDown" ? (from + 1) % options.length : (from <= 0 ? options.length : from) - 1);
    } else if ((event.key === "Enter" || (event.key === "Tab" && !event.shiftKey)) && chosen !== undefined) {
      event.preventDefault();
      accept(chosen);
    } else if (event.key === "Enter") {
      event.preventDefault();
      setListOpen(false);
      step(event.shiftKey ? -1 : 1);
    } else if (event.key === "Tab" && query === "" && !event.shiftKey && !shown) {
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
    return result.value === "" ? "(empty string)" : result.value;
  }
  const count = result.lines.length;
  if (count === 0) {
    return "0 matches";
  }
  return `${count} ${count === 1 ? "match" : "matches"} · ${index + 1} of ${count} · ${result.describe(index)}`;
}
