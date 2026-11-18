import { startTagLines } from "@/workbench/xmlTokens";

/** What one XPath Query returns: an error, a scalar (number, string or boolean), or its matches in document order. */
export type QueryResult =
  | { kind: "error"; message: string }
  | { kind: "scalar"; value: string }
  | { kind: "nodes"; lines: number[]; describe: (index: number) => string };

export type XPathQuery = {
  run: (query: string) => QueryResult;
  /** Every distinct element path, without position indexes, once each in document order: the typeahead's candidates. */
  paths: string[];
};

/**
 * An Uploaded Message ready to query (spec 17.10), or null if the browser cannot parse it. Queries run on a private
 * copy with namespaces stripped, as the `xpath-query` CLI does, so one query works for every Message Version. Match
 * paths and states follow the CLI: lxml `getpath` paths, then `= value`, `(no value)` or `(empty)`.
 */
export function buildXPathQuery(lines: string[]): XPathQuery | null {
  const parsed = new DOMParser().parseFromString(lines.join("\n"), "application/xml");
  if (parsed.getElementsByTagName("parsererror").length > 0) {
    return null;
  }
  const tagLines = startTagLines(lines);
  const doc = document.implementation.createDocument(null, null, null);
  const lineOf = new Map<Node, number>();
  const paths = new Set<string>();

  // The nth element copied is the nth start tag, since both run in document order.
  const copy = (from: Node, into: Node, path: string) => {
    for (let child = from.firstChild; child !== null; child = child.nextSibling) {
      if (child.nodeType === Node.ELEMENT_NODE) {
        const element = child as Element;
        const stripped = doc.createElementNS(null, element.localName);
        for (const attribute of element.attributes) {
          if (attribute.name !== "xmlns" && attribute.prefix !== "xmlns") {
            stripped.setAttributeNS(attribute.namespaceURI, attribute.name, attribute.value);
          }
        }
        lineOf.set(stripped, tagLines[lineOf.size] ?? 1);
        const childPath = `${path}/${element.localName}`;
        paths.add(childPath);
        into.appendChild(stripped);
        copy(element, stripped, childPath);
      } else if (child.nodeType === Node.TEXT_NODE || child.nodeType === Node.CDATA_SECTION_NODE) {
        into.appendChild(doc.createTextNode(child.nodeValue ?? ""));
      } else if (child.nodeType === Node.COMMENT_NODE) {
        into.appendChild(doc.createComment(child.nodeValue ?? ""));
      }
    }
  };
  copy(parsed, doc, "");

  const owner = (node: Node): Element =>
    node instanceof Attr && node.ownerElement !== null
      ? node.ownerElement
      : node.nodeType === Node.ELEMENT_NODE
        ? (node as Element)
        : node.parentNode?.nodeType === Node.ELEMENT_NODE
          ? (node.parentNode as Element)
          : (doc.documentElement as Element);

  const describe = (node: Node) => {
    if (node.nodeType === Node.ELEMENT_NODE) {
      return `${pathOf(node as Element)} ${stateOf(node as Element)}`;
    }
    const step = node instanceof Attr ? `@${node.name}` : node.nodeType === Node.TEXT_NODE ? "text()" : "comment()";
    const value = (node.nodeValue ?? "").trim();
    const where = node.nodeType === Node.DOCUMENT_NODE ? "" : `${pathOf(owner(node))}/${step}`;
    return `${where || "/"} ${value ? `= ${value}` : "(empty)"}`;
  };

  const run = (query: string): QueryResult => {
    let result: XPathResult;
    try {
      result = doc.evaluate(query, doc, null, XPathResult.ANY_TYPE, null);
      if (result.resultType === XPathResult.NUMBER_TYPE) {
        return { kind: "scalar", value: String(result.numberValue) };
      }
      if (result.resultType === XPathResult.STRING_TYPE) {
        return { kind: "scalar", value: result.stringValue };
      }
      if (result.resultType === XPathResult.BOOLEAN_TYPE) {
        return { kind: "scalar", value: String(result.booleanValue) };
      }
      // ANY_TYPE may hand back an unordered iterator; ask again for document order.
      result = doc.evaluate(query, doc, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
    } catch (error) {
      return { kind: "error", message: (error instanceof Error && error.message) || "not a valid XPath 1.0 query" };
    }
    const nodes: Node[] = [];
    const matchLines: number[] = [];
    for (let at = 0; at < result.snapshotLength; at++) {
      const node = result.snapshotItem(at) as Node;
      nodes.push(node);
      matchLines.push(lineOf.get(owner(node)) ?? 1);
    }
    return { kind: "nodes", lines: matchLines, describe: (index) => describe(nodes[index] as Node) };
  };

  return { run, paths: [...paths] };
}

/** lxml's `getpath`: a step gets `[n]` only when its parent has more than one child element of that name. */
function pathOf(element: Element) {
  const steps: string[] = [];
  for (let at: Element | null = element; at !== null; at = at.parentElement) {
    let index = 1;
    let shared = false;
    for (let sibling = at.previousElementSibling; sibling !== null; sibling = sibling.previousElementSibling) {
      if (sibling.localName === at.localName) {
        index++;
        shared = true;
      }
    }
    for (let sibling = at.nextElementSibling; !shared && sibling !== null; sibling = sibling.nextElementSibling) {
      shared = sibling.localName === at.localName;
    }
    steps.unshift(shared ? `${at.localName}[${index}]` : at.localName);
  }
  return `/${steps.join("/")}`;
}

/** The CLI's states: the element's own text, trimmed; `(no value)` if it has child elements; `(empty)` otherwise. */
function stateOf(element: Element) {
  let text = "";
  for (let child = element.firstChild; child !== null; child = child.nextSibling) {
    if (child.nodeType === Node.TEXT_NODE) {
      text += child.nodeValue;
    }
  }
  text = text.trim();
  if (text) {
    return `= ${text}`;
  }
  return element.firstElementChild === null ? "(empty)" : "(no value)";
}
