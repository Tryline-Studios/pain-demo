/** How a piece of an XML line is coloured. CDATA content counts as text. */
export type TokenKind = "tag" | "attr" | "value" | "punct" | "decl" | "comment" | "text";

export type Token = { kind: TokenKind; text: string };

/** Where a line starts: in text, or inside a comment, CDATA section, tag or quoted value an earlier line opened. */
const TEXT = 0;
const COMMENT = 1;
const CDATA = 2;
const TAG = 3;
const DOUBLE = 4;
const SINGLE = 5;

// `<`, `</`, `<?` or `<!`, then the name. A name after `<?` or `<!` is the XML declaration, a processing instruction
// or a DOCTYPE, coloured as a declaration.
const OPEN = /<([/?!]?)([^\s<>/?=!"']*)/y;
// Inside a tag: whitespace, an attribute name, or one punctuation character (`=`, `/`, `?`, ...).
const IN_TAG = /(\s+)|([^\s<>/?=!"']+)|[\s\S]/y;

/**
 * Walks one line from `state`, calling `emit` for each token, and returns the state the next line starts in. Without
 * `emit` it only tracks state, which is cheap enough to run over every line of a 10 MB upload.
 */
function scan(line: string, start: number, emit?: (kind: TokenKind, from: number, to: number) => void) {
  let state = start;
  let at = 0;
  const push = (kind: TokenKind, to: number) => {
    if (to > at) {
      emit?.(kind, at, to);
    }
    at = to;
  };
  while (at < line.length) {
    if (state === TEXT) {
      const open = line.indexOf("<", at);
      if (open < 0) {
        push("text", line.length);
      } else {
        push("text", open);
        if (line.startsWith("<!--", at)) {
          push("comment", at + 4);
          state = COMMENT;
        } else if (line.startsWith("<![CDATA[", at)) {
          push("punct", at + 9);
          state = CDATA;
        } else {
          OPEN.lastIndex = at;
          const [, kind = "", name = ""] = OPEN.exec(line) ?? [];
          push("punct", at + 1 + kind.length);
          push(kind === "?" || kind === "!" ? "decl" : "tag", at + name.length);
          state = TAG;
        }
      }
    } else if (state === COMMENT || state === CDATA) {
      const close = line.indexOf(state === COMMENT ? "-->" : "]]>", at);
      push(state === COMMENT ? "comment" : "text", close < 0 ? line.length : close);
      if (close >= 0) {
        push(state === COMMENT ? "comment" : "punct", at + 3);
        state = TEXT;
      }
    } else if (state === DOUBLE || state === SINGLE) {
      const close = line.indexOf(state === DOUBLE ? '"' : "'", at);
      push("value", close < 0 ? line.length : close + 1);
      if (close >= 0) {
        state = TAG;
      }
    } else {
      const char = line[at];
      if (char === ">") {
        push("punct", at + 1);
        state = TEXT;
      } else if (char === '"' || char === "'") {
        // The opening quote belongs to the value; the quoted states then look for the closing one.
        state = char === '"' ? DOUBLE : SINGLE;
        const close = line.indexOf(char, at + 1);
        push("value", close < 0 ? line.length : close + 1);
        if (close >= 0) {
          state = TAG;
        }
      } else {
        IN_TAG.lastIndex = at;
        const match = IN_TAG.exec(line);
        push(match?.[1] ? "text" : match?.[2] ? "attr" : "punct", IN_TAG.lastIndex);
      }
    }
  }
  return state;
}

/** The state each line starts in, from one pass over the whole source. Compute once per source and keep it. */
export function lineStates(lines: string[]) {
  const states = new Uint8Array(lines.length);
  let state = TEXT;
  for (let at = 0; at < lines.length; at++) {
    states[at] = state;
    state = scan(lines[at] ?? "", state);
  }
  return states;
}

/**
 * The line (from 1) of every start tag, in source order: the nth entry is the line of the nth element in document
 * order. Tags inside comments, CDATA sections and quoted values are skipped, as the tokenizer already tracks them.
 */
export function startTagLines(lines: string[]) {
  const found: number[] = [];
  let state = TEXT;
  for (let at = 0; at < lines.length; at++) {
    const line = lines[at] ?? "";
    // A bare `<` punctuation token opens a start tag; `</`, `<?`, `<!` and `<![CDATA[` are longer.
    state = scan(line, state, (kind, from, to) => {
      if (kind === "punct" && to - from === 1 && line[from] === "<") {
        found.push(at + 1);
      }
    });
  }
  return found;
}

/** One line's tokens, starting in `state` (from `lineStates`; 0 for a line that starts in text). */
export function tokenizeLine(line: string, state: number) {
  const tokens: Token[] = [];
  scan(line, state, (kind, from, to) => {
    tokens.push({ kind, text: line.slice(from, to) });
  });
  return tokens;
}
