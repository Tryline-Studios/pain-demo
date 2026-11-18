import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { describe, expect, it } from "vitest";
import type { components } from "@/api/schema";
import { renderWithQueries } from "@/test/render";
import { server } from "@/test/server";
import { Workbench } from "@/workbench/Workbench";

type ValidationReport = components["schemas"]["ValidationReport"];

const ROOT = "/Document/CstmrCdtTrfInitn";

// A namespaced pain.001 whose start tags hide behind a multi-line comment, a CDATA section, an attribute value
// holding `>` and several elements on one line, so the element-to-line mapping is tested on each.
const message = `<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.03">
  <CstmrCdtTrfInitn>
    <GrpHdr><MsgId>MSG-1</MsgId><NbOfTxs>2</NbOfTxs></GrpHdr>
    <!-- a comment with <Fake> tags
         spanning <Lines/> -->
    <PmtInf>
      <PmtInfId><![CDATA[<NotATag>]]></PmtInfId>
      <CdtTrfTxInf>
        <Amt><InstdAmt Ccy="EUR" Note="a>b">10.00</InstdAmt></Amt>
        <Cdtr><Nm/></Cdtr>
      </CdtTrfTxInf>
      <CdtTrfTxInf>
        <Amt>
          <InstdAmt Ccy="USD">20.00</InstdAmt>
        </Amt>
      </CdtTrfTxInf>
    </PmtInf>
  </CstmrCdtTrfInitn>
</Document>`;

const validReport: ValidationReport = {
  valid: true,
  message_version: "pain.001.001.03",
  encoding: "UTF-8",
  transaction_count: 2,
  file: { name: "batch.xml", size_bytes: message.length, sha256: "0".repeat(64) },
  problems: [],
  truncated: false,
};

const problem: ValidationReport["problems"][number] = {
  line: 11,
  column: 15,
  tag: "Nm",
  path: `${ROOT}/PmtInf/CdtTrfTxInf[1]/Cdtr/Nm`,
  code: "pattern_mismatch",
  cause: null,
  message: "Nm is empty",
};

function answerWith(report: ValidationReport) {
  server.use(http.post("/api/v1/validations", () => HttpResponse.json(report)));
}

async function upload(text = message, report = validReport) {
  answerWith(report);
  const user = userEvent.setup();
  renderWithQueries(<Workbench />);
  await user.upload(screen.getByLabelText(/Drop a pain.001 file/), new File([text], "batch.xml"));
  await screen.findByRole("list", { name: "Source" });
  return user;
}

function box() {
  return screen.getByRole("combobox", { name: "XPath Query" });
}

function status() {
  return screen.getByRole("status");
}

async function statusIs(text: string) {
  await waitFor(() => expect(status().textContent).toBe(text));
}

/** The source line numbered `line`, found by its line number. */
function sourceLine(line: number) {
  const item = within(screen.getByRole("list", { name: "Source" }))
    .getAllByRole("listitem")
    .find((candidate) => candidate.querySelector("span")?.textContent === String(line));
  if (item === undefined) {
    throw new Error(`line ${line} is not rendered`);
  }
  return item;
}

function tinted() {
  return within(screen.getByRole("list", { name: "Source" }))
    .getAllByRole("listitem")
    .filter((item) => item.classList.contains("bg-primary-soft"))
    .map((item) => Number(item.querySelector("span")?.textContent));
}

function current() {
  return within(screen.getByRole("list", { name: "Source" }))
    .getAllByRole("listitem")
    .filter((item) => item.getAttribute("aria-current") === "step")
    .map((item) => Number(item.querySelector("span")?.textContent));
}

describe("XPath Query", () => {
  it("labels the box visibly as XPath Query", async () => {
    await upload();
    expect(screen.getByLabelText("XPath Query")).toBe(box());
    expect(screen.getByText("XPath Query", { selector: "label" })).toBeVisible();
  });

  it("shows the XPath cheat sheet on hovering the info button", async () => {
    const user = await upload();
    await user.hover(screen.getByRole("button", { name: "About XPath queries" }));
    expect(await screen.findByRole("tooltip")).toHaveTextContent("without namespace prefixes");
  });

  it("shows an XPath cheat sheet when the info button gets keyboard focus, and hides it on Esc", async () => {
    const user = await upload();
    const info = screen.getByRole("button", { name: "About XPath queries" });

    while (document.activeElement !== info) {
      await user.tab();
    }
    const tip = await screen.findByRole("tooltip");
    expect(tip).toHaveTextContent("XPath 1.0, written without namespace prefixes.");
    for (const example of [
      "/Document/CstmrCdtTrfInitn",
      "//InstdAmt",
      "//CdtTrfTxInf[2]",
      "//InstdAmt/@Ccy",
      "//Cdtr[Nm='ACME Ltd']",
      "count(//CdtTrfTxInf)",
    ]) {
      expect(within(tip).getByText(example)).toBeInTheDocument();
    }
    expect(tip).toHaveTextContent("a number, not matches");

    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("tooltip")).not.toBeInTheDocument());
  });

  it("runs a namespace-free query after a pause, jumping to the first match and tinting every match line", async () => {
    const user = await upload();
    expect(box()).toHaveAttribute("placeholder", ROOT);
    expect(status()).toHaveAttribute("aria-live", "polite");

    await user.type(box(), "//InstdAmt");
    expect(status().textContent).toBe("");
    expect(tinted()).toEqual([]);

    await statusIs(`2 matches · 1 of 2 · ${ROOT}/PmtInf/CdtTrfTxInf[1]/Amt/InstdAmt = 10.00`);
    expect(tinted()).toEqual([10, 15]);
    expect(current()).toEqual([10]);
  });

  /** Replaces the box's text with `query` and waits for the status line to read `expected`. */
  async function ask(user: ReturnType<typeof userEvent.setup>, query: string, expected: string) {
    await user.clear(box());
    // user-event reads `[` and `{` as key descriptors; doubling them types them.
    await user.type(box(), query.replaceAll("[", "[[").replaceAll("{", "{{"));
    await statusIs(expected);
  }

  it("reports each match's lxml path and the CLI's value states, on the line of its start tag", async () => {
    const user = await upload();

    await ask(user, "//NbOfTxs", `1 match · 1 of 1 · ${ROOT}/GrpHdr/NbOfTxs = 2`);
    expect(current()).toEqual([4]);
    await ask(user, "//Cdtr", `1 match · 1 of 1 · ${ROOT}/PmtInf/CdtTrfTxInf[1]/Cdtr (no value)`);
    expect(current()).toEqual([11]);
    await ask(user, "//Cdtr/Nm", `1 match · 1 of 1 · ${ROOT}/PmtInf/CdtTrfTxInf[1]/Cdtr/Nm (empty)`);
    await ask(user, "//PmtInf", `1 match · 1 of 1 · ${ROOT}/PmtInf (no value)`);
    expect(current()).toEqual([7]);
    await ask(user, "//PmtInfId", `1 match · 1 of 1 · ${ROOT}/PmtInf/PmtInfId = <NotATag>`);
    expect(current()).toEqual([8]);
    await ask(user, "//CdtTrfTxInf[2]/Amt", `1 match · 1 of 1 · ${ROOT}/PmtInf/CdtTrfTxInf[2]/Amt (no value)`);
    expect(current()).toEqual([14]);
    await ask(user, "//UltmtDbtr", "0 matches");
    expect(tinted()).toEqual([]);
    expect(current()).toEqual([]);
  });

  it("shows a number, boolean or string result in the status line and jumps nowhere", async () => {
    const user = await upload();
    await ask(user, "//InstdAmt", `2 matches · 1 of 2 · ${ROOT}/PmtInf/CdtTrfTxInf[1]/Amt/InstdAmt = 10.00`);

    await ask(user, "count(//CdtTrfTxInf)", "2");
    expect(tinted()).toEqual([]);
    expect(current()).toEqual([]);
    await ask(user, "boolean(//UltmtDbtr)", "false");
    await ask(user, "string(//MsgId)", "MSG-1");
    await ask(user, "local-name(/*)", "Document");
  });

  it("shows an XPath error and drops the last query's highlights", async () => {
    const user = await upload();
    await ask(user, "//InstdAmt", `2 matches · 1 of 2 · ${ROOT}/PmtInf/CdtTrfTxInf[1]/Amt/InstdAmt = 10.00`);

    await user.type(box(), "[[");
    await waitFor(() => expect(status().textContent).toMatch(/^XPath error: ./));
    expect(tinted()).toEqual([]);
    expect(current()).toEqual([]);
  });

  it("shows an empty string result visibly", async () => {
    const user = await upload();

    await ask(user, "string(//UltmtDbtr)", "(empty string)");
  });

  it("matches a top-level comment without jumping, with a CLI-like path", async () => {
    const user = await upload(message.replace("<Document", "<!-- prologue -->\n<Document"));

    await ask(user, "/comment()", "1 match · 1 of 1 · /comment() = prologue");
    expect(tinted()).toEqual([]);
    expect(current()).toEqual([]);
  });

  it("queries a message that has its own element named parsererror", async () => {
    const user = await upload(message.replace("<NbOfTxs>2</NbOfTxs>", "<NbOfTxs>2</NbOfTxs><parsererror/>"));

    expect(box()).toBeEnabled();
    await ask(user, "//parsererror", `1 match · 1 of 1 · ${ROOT}/GrpHdr/parsererror (empty)`);
  });

  it("runs the typed query before stepping when Enter comes within the pause", async () => {
    const user = await upload();
    await ask(user, "//MsgId", `1 match · 1 of 1 · ${ROOT}/GrpHdr/MsgId = MSG-1`);

    await user.clear(box());
    await user.type(box(), "//InstdAmt{Enter}");

    expect(status().textContent).toBe(`2 matches · 2 of 2 · ${ROOT}/PmtInf/CdtTrfTxInf[2]/Amt/InstdAmt = 20.00`);
    expect(current()).toEqual([15]);
    await new Promise((resolve) => setTimeout(resolve, 200));
    expect(status().textContent).toBe(`2 matches · 2 of 2 · ${ROOT}/PmtInf/CdtTrfTxInf[2]/Amt/InstdAmt = 20.00`);
  });

  // jsdom's XPath engine finds no attribute by name (`@Ccy`), so these use `@*`, which both engines support.
  it("lands attribute and text-node matches on their owning element's line", async () => {
    const user = await upload();

    await ask(user, "//InstdAmt/@*", `3 matches · 1 of 3 · ${ROOT}/PmtInf/CdtTrfTxInf[1]/Amt/InstdAmt/@Ccy = EUR`);
    expect(tinted()).toEqual([10, 15]);
    expect(current()).toEqual([10]);
    await ask(user, "//MsgId/text()", `1 match · 1 of 1 · ${ROOT}/GrpHdr/MsgId/text() = MSG-1`);
    expect(current()).toEqual([4]);
  });

  it("steps through matches with Previous and Next, and with Enter and Shift+Enter, wrapping at both ends", async () => {
    const user = await upload();
    const second = `2 matches · 2 of 2 · ${ROOT}/PmtInf/CdtTrfTxInf[2]/Amt/InstdAmt = 20.00`;
    const first = `2 matches · 1 of 2 · ${ROOT}/PmtInf/CdtTrfTxInf[1]/Amt/InstdAmt = 10.00`;
    await ask(user, "//InstdAmt", first);

    await user.click(screen.getByRole("button", { name: "Next match" }));
    expect(status().textContent).toBe(second);
    expect(current()).toEqual([15]);
    await user.click(screen.getByRole("button", { name: "Next match" }));
    expect(status().textContent).toBe(first);
    await user.click(screen.getByRole("button", { name: "Previous match" }));
    expect(status().textContent).toBe(second);

    await user.type(box(), "{Enter}");
    expect(status().textContent).toBe(first);
    expect(current()).toEqual([10]);
    await user.type(box(), "{Shift>}{Enter}{/Shift}");
    expect(status().textContent).toBe(second);
    expect(current()).toEqual([15]);
  });

  it("disables Previous and Next until there are matches", async () => {
    await upload();

    expect(screen.getByRole("button", { name: "Previous match" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Next match" })).toBeDisabled();
  });

  describe("typeahead", () => {
    function options() {
      return screen.queryAllByRole("option").map((option) => option.textContent);
    }

    it("accepts the placeholder with Tab in an empty box", async () => {
      const user = await upload();

      await user.click(box());
      await user.tab();

      expect(box()).toHaveValue(ROOT);
      expect(box()).toHaveFocus();
      await statusIs(`1 match · 1 of 1 · ${ROOT} (no value)`);
      expect(current()).toEqual([3]);
    });

    it("lists this message's element paths ranked by fuzzy match, and runs the chosen one at once", async () => {
      const user = await upload();

      await user.type(box(), "instamt");
      expect(box()).toHaveAttribute("aria-expanded", "true");
      expect(options()[0]).toBe(`${ROOT}/PmtInf/CdtTrfTxInf/Amt/InstdAmt`);
      expect(options()).toHaveLength(new Set(options()).size);

      await user.keyboard("{ArrowDown}");
      expect(screen.getAllByRole("option")[0]).toHaveAttribute("aria-selected", "true");
      expect(box()).toHaveAttribute("aria-activedescendant", screen.getAllByRole("option")[0]?.id);
      await user.keyboard("{Enter}");

      expect(box()).toHaveValue(`${ROOT}/PmtInf/CdtTrfTxInf/Amt/InstdAmt`);
      expect(box()).toHaveAttribute("aria-expanded", "false");
      expect(status().textContent).toBe(`2 matches · 1 of 2 · ${ROOT}/PmtInf/CdtTrfTxInf[1]/Amt/InstdAmt = 10.00`);
    });

    it("lists at most eight paths, wraps with the arrows, accepts with Tab and closes with Escape", async () => {
      const user = await upload();

      await user.type(box(), "d");
      expect(options()).toHaveLength(8);
      await user.keyboard("{ArrowUp}");
      expect(screen.getAllByRole("option")[7]).toHaveAttribute("aria-selected", "true");
      await user.keyboard("{ArrowDown}");
      expect(screen.getAllByRole("option")[0]).toHaveAttribute("aria-selected", "true");
      await user.keyboard("{Escape}");
      expect(box()).toHaveAttribute("aria-expanded", "false");
      expect(options()).toEqual([]);

      await user.type(box(), "msg");
      await user.keyboard("{ArrowDown}{Tab}");
      expect(box()).toHaveValue(`${ROOT}/GrpHdr/MsgId`);
      expect(status().textContent).toBe(`1 match · 1 of 1 · ${ROOT}/GrpHdr/MsgId = MSG-1`);
    });

    it("accepts a clicked path", async () => {
      const user = await upload();

      await user.type(box(), "nbof");
      await user.click(screen.getByRole("option", { name: `${ROOT}/GrpHdr/NbOfTxs` }));

      expect(box()).toHaveValue(`${ROOT}/GrpHdr/NbOfTxs`);
      expect(status().textContent).toBe(`1 match · 1 of 1 · ${ROOT}/GrpHdr/NbOfTxs = 2`);
    });

    it("runs an accepted path once, so stepping right after is not undone by the pause", async () => {
      const user = await upload();

      await user.type(box(), "instdamt");
      await user.keyboard("{ArrowDown}{Enter}");
      await user.click(screen.getByRole("button", { name: "Next match" }));
      await new Promise((resolve) => setTimeout(resolve, 200));

      expect(status().textContent).toBe(`2 matches · 2 of 2 · ${ROOT}/PmtInf/CdtTrfTxInf[2]/Amt/InstdAmt = 20.00`);
      expect(current()).toEqual([15]);
    });

    it("leaves the box with Shift+Tab without accepting, and reopens the list with the arrows", async () => {
      const user = await upload();

      await user.type(box(), "msg");
      await user.keyboard("{ArrowDown}{Shift>}{Tab}{/Shift}");
      expect(box()).toHaveValue("msg");
      expect(box()).not.toHaveFocus();

      await user.click(box());
      expect(box()).toHaveAttribute("aria-expanded", "false");
      await user.keyboard("{ArrowDown}");
      expect(box()).toHaveAttribute("aria-expanded", "true");
      expect(screen.getAllByRole("option")[0]).toHaveAttribute("aria-selected", "true");
      await user.keyboard("{Escape}{ArrowUp}");
      expect(box()).toHaveAttribute("aria-expanded", "true");
      expect(screen.getAllByRole("option").at(-1)).toHaveAttribute("aria-selected", "true");
    });

    it("hides once the query is more than a plain path, and Enter then steps through matches", async () => {
      const user = await upload();

      await user.type(box(), "//InstdAmt");
      expect(options()).not.toEqual([]);
      for (const extra of ["[[1]", "/@*", " | //MsgId", "count("]) {
        await user.clear(box());
        await user.type(box(), `//InstdAmt${extra}`);
        expect(options()).toEqual([]);
      }

      await user.clear(box());
      await user.type(box(), "//InstdAmt");
      await statusIs(`2 matches · 1 of 2 · ${ROOT}/PmtInf/CdtTrfTxInf[1]/Amt/InstdAmt = 10.00`);
      await user.keyboard("{Enter}");
      expect(options()).toEqual([]);
      expect(status().textContent).toBe(`2 matches · 2 of 2 · ${ROOT}/PmtInf/CdtTrfTxInf[2]/Amt/InstdAmt = 20.00`);
    });
  });

  it("keeps the query and runs it again on the next upload", async () => {
    const user = await upload();
    await ask(user, "//InstdAmt", `2 matches · 1 of 2 · ${ROOT}/PmtInf/CdtTrfTxInf[1]/Amt/InstdAmt = 10.00`);

    const one = message.replace(
      /\s*<CdtTrfTxInf>\s*<Amt>\s*<InstdAmt Ccy="USD">20.00<\/InstdAmt>[\s\S]*?<\/CdtTrfTxInf>/,
      "",
    );
    await user.upload(screen.getByLabelText(/Drop a pain.001 file/), new File([one], "one.xml"));

    await statusIs(`1 match · 1 of 1 · ${ROOT}/PmtInf/CdtTrfTxInf/Amt/InstdAmt = 10.00`);
    expect(box()).toHaveValue("//InstdAmt");
  });

  it("keeps problem jumps and query navigation apart", async () => {
    const user = await upload(message, { ...validReport, valid: false, problems: [problem] });
    await ask(user, "//InstdAmt", `2 matches · 1 of 2 · ${ROOT}/PmtInf/CdtTrfTxInf[1]/Amt/InstdAmt = 10.00`);

    await user.click(screen.getByRole("button", { name: /pattern_mismatch/ }));
    expect(sourceLine(11)).toHaveAttribute("aria-current", "location");
    expect(sourceLine(11)).toHaveClass("bg-destructive-soft");
    expect(tinted()).toEqual([10, 15]);
    expect(current()).toEqual([10]);

    await user.click(screen.getByRole("button", { name: "Next match" }));
    expect(current()).toEqual([15]);
    expect(sourceLine(11)).toHaveAttribute("aria-current", "location");
  });

  it.each([
    ["malformed_xml", "XPath Query is off: the Uploaded Message is not well-formed XML"],
    ["dtd_not_allowed", "XPath Query is off: the Uploaded Message carries a DTD"],
  ] as const)("is disabled, saying why, for a %s upload", async (code, reason) => {
    await upload(message, {
      ...validReport,
      valid: false,
      problems: [{ ...problem, line: 1, code, message: code }],
    });

    expect(box()).toBeDisabled();
    expect(status().textContent).toBe(reason);
  });
});
