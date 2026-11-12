import { describe, expect, it } from "vitest";
import { lineStates, tokenizeLine } from "@/workbench/xmlTokens";

/** Each line's tokens written as `kind:text`, so a failure reads like the line. */
function shown(source: string) {
  const lines = source.split("\n");
  const states = lineStates(lines);
  return lines.map((line, at) => tokenizeLine(line, states[at] ?? 0).map(({ kind, text }) => `${kind}:${text}`));
}

describe("XML tokens", () => {
  it("colours an element's tag name, attributes, values and text apart", () => {
    expect(shown('<Amt Ccy="EUR">10.00</Amt>')).toEqual([
      [
        "punct:<",
        "tag:Amt",
        "text: ",
        "attr:Ccy",
        "punct:=",
        'value:"EUR"',
        "punct:>",
        "text:10.00",
        "punct:</",
        "tag:Amt",
        "punct:>",
      ],
    ]);
  });

  it("colours a self-closing tag's slash as punctuation", () => {
    expect(shown("<Cd/> <Prtry a='1' />")).toEqual([
      [
        "punct:<",
        "tag:Cd",
        "punct:/",
        "punct:>",
        "text: ",
        "punct:<",
        "tag:Prtry",
        "text: ",
        "attr:a",
        "punct:=",
        "value:'1'",
        "text: ",
        "punct:/",
        "punct:>",
      ],
    ]);
  });

  it("colours the XML declaration's name as a declaration", () => {
    expect(shown('<?xml version="1.0"?>')).toEqual([
      ["punct:<?", "decl:xml", "text: ", "attr:version", "punct:=", 'value:"1.0"', "punct:?", "punct:>"],
    ]);
  });

  it("keeps a comment that spans lines a comment, and colours the lines after it again", () => {
    expect(shown("<A><!-- a <B> here\n<C x='1'> still\nend --><D>")).toEqual([
      ["punct:<", "tag:A", "punct:>", "comment:<!--", "comment: a <B> here"],
      ["comment:<C x='1'> still"],
      ["comment:end ", "comment:-->", "punct:<", "tag:D", "punct:>"],
    ]);
  });

  it("carries a CDATA section, a tag and a quoted value across lines", () => {
    expect(shown("<![CDATA[a <b>\n]]><E\n  k='v\nw'>t")).toEqual([
      ["punct:<![CDATA[", "text:a <b>"],
      ["punct:]]>", "punct:<", "tag:E"],
      ["text:  ", "attr:k", "punct:=", "value:'v"],
      ["value:w'", "punct:>", "text:t"],
    ]);
  });
});
