import { startTagLines } from "@/workbench/xmlTokens";

/** What one XPath Query returns: an error, a scalar (number, string or boolean), or its matches in document order. */
export type QueryResult =
  | { kind: "error"; message: string }
  | { kind: "scalar"; value: string }
  /** `lines[i]` is the line of match i's owning element; null for the document or a node outside the root element. */
  | { kind: "nodes"; lines: (number | null)[]; describe: (index: number) => string };

// Browsers report a parse failure as an element in one of these namespaces, never in the message's own.
const PARSE_ERROR_NAMESPACES = ["http://www.w3.org/1999/xhtml", "http://www.mozilla.org/newlayout/xml/parsererror.xml"];

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
export function buildXPathQuery(source: string, lines: string[]): XPathQuery | null {
  const parsed = new DOMParser().parseFromString(source, "application/xml");
  const errors = parsed.getElementsByTagName("parsererror");
  for (const error of errors) {
    if (PARSE_ERROR_NAMESPACES.includes(error.namespaceURI ?? "")) {
      return null;
    }
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

  /** The element a match belongs to; null for the document itself and for comments beside the root element. */
  const owner = (node: Node): Element | null =>
    node instanceof Attr
      ? node.ownerElement
      : node.nodeType === Node.ELEMENT_NODE
        ? (node as Element)
        : node.parentNode?.nodeType === Node.ELEMENT_NODE
          ? (node.parentNode as Element)
          : null;

  const describe = (node: Node) => {
    if (node.nodeType === Node.ELEMENT_NODE) {
      return `${pathOf(node as Element)} ${stateOf(node as Element)}`;
    }
    if (node.nodeType === Node.DOCUMENT_NODE) {
      return "/ (no value)";
    }
    const step = node instanceof Attr ? `@${node.name}` : node.nodeType === Node.TEXT_NODE ? "text()" : "comment()";
    const value = (node.nodeValue ?? "").trim();
    const element = owner(node);
    return `${element === null ? "" : pathOf(element)}/${step} ${value ? `= ${value}` : "(empty)"}`;
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
    const matchLines: (number | null)[] = [];
    for (let at = 0; at < result.snapshotLength; at++) {
      const node = result.snapshotItem(at) as Node;
      const element = owner(node);
      nodes.push(node);
      matchLines.push(element === null ? null : (lineOf.get(element) ?? null));
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
