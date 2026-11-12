import { useMemo } from "react";
import type { components } from "@/api/schema";

type Hit = components["schemas"]["Hit"];

/**
 * Each line's XPath, written the way the Answer Key writes a Hit's (`CdtTrfTxInf[n]` is the only indexed step), for
 * the lines that hold a leaf element. Walks the pretty-printed XML the generator emits: one element per line, leaf
 * elements opened and closed on the same line.
 * shortcut: assumes that one-element-per-line layout and a single PmtInf; switch to DOMParser if either changes.
 */
function leafPaths(lines: string[]) {
  const stack: string[] = [];
  let transaction = 0;
  return lines.map((line) => {
    const trimmed = line.trim();
    if (trimmed.startsWith("</")) {
      stack.pop();
      return null;
    }
    const name = /^<([\w:]+)/.exec(trimmed)?.[1];
    if (name === undefined || trimmed.endsWith("/>")) {
      return null;
    }
    const step = name === "CdtTrfTxInf" ? `${name}[${++transaction}]` : name;
    if (trimmed.endsWith(`</${name}>`)) {
      return `/${[...stack, step].join("/")}`;
    }
    stack.push(step);
    return null;
  });
}

/** The Sample File with each Hit's name marked on the line its XPath points at (spec 13.3). */
export function HighlightedXml({ xml, hits }: { xml: string; hits: Hit[] }) {
  const lines = useMemo(() => {
    const byPath = new Map(hits.map((hit) => [hit.xpath, hit]));
    const split = xml.split("\n");
    const paths = leafPaths(split);
    return split.map((text, at) => ({ text, hit: byPath.get(paths[at] ?? "") }));
  }, [xml, hits]);

  return (
    <pre className="max-h-[70vh] overflow-auto rounded-xl border bg-card p-4 font-mono text-xs">
      {lines.map(({ text, hit }, at) => {
        const end = at === lines.length - 1 ? "" : "\n";
        if (hit === undefined) {
          return text + end;
        }
        // The element's text sits between the opening tag's `>` and the closing tag's `<`.
        const open = text.indexOf(">") + 1;
        const close = text.lastIndexOf("<");
        return (
          // biome-ignore lint/suspicious/noArrayIndexKey: lines are positional and never reorder
          <span key={at}>
            {text.slice(0, open)}
            <mark title={hit.id} className="rounded-sm bg-amber-200 px-0.5 text-foreground dark:bg-amber-500/40">
              {text.slice(open, close)}
            </mark>
            {text.slice(close)}
            {end}
          </span>
        );
      })}
    </pre>
  );
}
