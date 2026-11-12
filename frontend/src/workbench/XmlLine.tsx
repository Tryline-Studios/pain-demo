import { type TokenKind, tokenizeLine } from "@/workbench/xmlTokens";

const COLOUR: Record<Exclude<TokenKind, "text">, string> = {
  tag: "text-tk-tag",
  attr: "text-tk-attr",
  value: "text-tk-value",
  punct: "text-tk-punct",
  decl: "text-tk-decl",
  // Comments have no colour of their own in the design; italics set them apart from punctuation.
  comment: "text-tk-punct italic",
};

/** One line of XML, syntax-coloured. Colours change only the text, so a line's highlight shows through. */
export function XmlLine({ line, state = 0 }: { line: string; state?: number }) {
  return tokenizeLine(line, state).map(({ kind, text }, at) =>
    kind === "text" ? (
      text
    ) : (
      // biome-ignore lint/suspicious/noArrayIndexKey: tokens are positional and never reorder
      <span key={at} className={COLOUR[kind]}>
        {text}
      </span>
    ),
  );
}
