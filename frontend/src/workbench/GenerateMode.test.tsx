import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithQueries } from "@/test/render";
import { generated, generatedWithHits, sampleXml, server } from "@/test/server";
import { Workbench } from "@/workbench/Workbench";

async function openFileSection() {
  const user = userEvent.setup();
  renderWithQueries(<Workbench />);
  await user.click(screen.getByRole("button", { name: "File" }));
  await screen.findByRole("option", { name: "pain.001.001.13" });
  return user;
}

function settings() {
  return screen.getByRole("complementary", { name: "Settings" });
}

/** The settings pane's Generate, not the mode toggle of the same name. */
function generateButton() {
  return within(settings()).getByRole("button", { name: "Generate" });
}

function output() {
  return screen.getByRole("region", { name: "Output" });
}

function chip(group: string, name: string) {
  return within(screen.getByRole("group", { name: group })).getByRole("button", { name });
}

/** Records every body posted to the generate endpoint, answering with `generated`. */
function recordGenerateRequests() {
  const bodies: unknown[] = [];
  server.use(
    http.post("/api/v1/sample-files", async ({ request }) => {
      bodies.push(await request.json());
      return HttpResponse.json(generated);
    }),
  );
  return bodies;
}

describe("Generate mode: the File section", () => {
  it("is populated from the options and Message Versions the API publishes", async () => {
    await openFileSection();

    const version = screen.getByRole("combobox", { name: "Message Version" });
    expect(version).toHaveValue("pain.001.001.03");
    expect(
      within(version)
        .getAllByRole("option")
        .map((o) => o.textContent),
    ).toEqual(["pain.001.001.03", "pain.001.001.09", "pain.001.001.13"]);
    const count = screen.getByRole("spinbutton", { name: "Transactions" });
    expect(count).toHaveValue(10);
    expect(count).toHaveAttribute("max", "100");
    expect(screen.getByRole("textbox", { name: "Seed" })).toHaveAttribute("maxlength", "64");
    expect(screen.getByRole("textbox", { name: "Minimum amount" })).toHaveValue("10.00");
    expect(screen.getByRole("textbox", { name: "Maximum amount" })).toHaveValue("50000.00");
    for (const [code, pressed] of [
      ["GB", true],
      ["DE", true],
      ["FR", false],
      ["PL", false],
      ["US", false],
    ] as const) {
      expect(chip("Countries", code)).toHaveAttribute("aria-pressed", String(pressed));
    }
    expect(screen.getByText("Debtor country: GB")).toBeInTheDocument();
    for (const code of ["GBP", "EUR", "PLN", "USD"]) {
      expect(chip("Currencies", code)).toHaveAttribute("aria-pressed", "false");
    }
  });

  it("makes the first chosen country the Debtor's", async () => {
    const user = await openFileSection();

    await user.click(chip("Countries", "GB"));
    await user.click(chip("Countries", "US"));

    expect(chip("Countries", "GB")).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByText("Debtor country: DE")).toBeInTheDocument();
  });
});

describe("Generate mode: generating", () => {
  it("posts nothing the user left alone, so the API's defaults apply", async () => {
    const bodies = recordGenerateRequests();
    const user = await openFileSection();

    await user.click(generateButton());

    await within(output()).findByRole("tab", { name: "Answer Key" });
    expect(bodies).toEqual([{}]);
  });

  it("posts only the field the user changed", async () => {
    const bodies = recordGenerateRequests();
    const user = await openFileSection();

    await user.clear(screen.getByRole("spinbutton", { name: "Transactions" }));
    await user.type(screen.getByRole("spinbutton", { name: "Transactions" }), "3");
    await user.click(generateButton());

    await within(output()).findByRole("tab", { name: "Answer Key" });
    expect(bodies).toEqual([{ transaction_count: 3 }]);
  });

  it("leaves a cleared Seed and deselected currencies for the API to pick", async () => {
    const bodies = recordGenerateRequests();
    const user = await openFileSection();

    await user.type(screen.getByRole("textbox", { name: "Seed" }), "abc");
    await user.clear(screen.getByRole("textbox", { name: "Seed" }));
    await user.click(chip("Currencies", "EUR"));
    await user.click(chip("Currencies", "EUR"));
    await user.click(generateButton());

    await within(output()).findByRole("tab", { name: "Answer Key" });
    expect(bodies).toEqual([{}]);
  });

  it("posts a country made the Debtor's first, keeping the others chosen", async () => {
    const bodies = recordGenerateRequests();
    const user = await openFileSection();

    await user.click(chip("Countries", "US"));
    await user.click(screen.getByRole("button", { name: "Make US Debtor" }));
    await user.click(generateButton());

    await within(output()).findByRole("tab", { name: "Answer Key" });
    expect(screen.getByText("Debtor country: US")).toBeInTheDocument();
    for (const code of ["GB", "DE", "US"]) {
      expect(chip("Countries", code)).toHaveAttribute("aria-pressed", "true");
    }
    expect(bodies).toEqual([{ countries: ["US", "GB", "DE"] }]);
  });

  it("posts what the File section says", async () => {
    const bodies = recordGenerateRequests();
    const user = await openFileSection();

    await user.selectOptions(screen.getByRole("combobox", { name: "Message Version" }), "pain.001.001.09");
    await user.clear(screen.getByRole("spinbutton", { name: "Transactions" }));
    await user.type(screen.getByRole("spinbutton", { name: "Transactions" }), "3");
    await user.type(screen.getByRole("textbox", { name: "Seed" }), "regression-run-42");
    await user.click(chip("Countries", "GB"));
    await user.click(chip("Countries", "US"));
    await user.click(chip("Currencies", "EUR"));
    await user.click(chip("Currencies", "USD"));
    await user.clear(screen.getByRole("textbox", { name: "Minimum amount" }));
    await user.type(screen.getByRole("textbox", { name: "Minimum amount" }), "5.50");
    await user.clear(screen.getByRole("textbox", { name: "Maximum amount" }));
    await user.type(screen.getByRole("textbox", { name: "Maximum amount" }), "900");
    await user.click(generateButton());

    await within(output()).findByRole("group", { name: "Seed" });
    expect(bodies).toEqual([
      {
        message_version: "pain.001.001.09",
        transaction_count: 3,
        seed: "regression-run-42",
        countries: ["DE", "US"],
        currencies: ["EUR", "USD"],
        amount_min: "5.50",
        amount_max: "900",
      },
    ]);
  });

  it("shows the summary tiles, the XML and the warnings of the Sample File", async () => {
    server.use(
      http.post("/api/v1/sample-files", () =>
        HttpResponse.json({
          ...generated,
          answer_key: { ...generated.answer_key, warnings: ["/Document/.../LEI dropped: not in pain.001.001.03"] },
        }),
      ),
    );
    const user = await openFileSection();

    await user.click(generateButton());

    const seedTile = await within(output()).findByRole("group", { name: "Seed" });
    expect(seedTile).toHaveTextContent("echoed-seed");
    expect(within(output()).getByRole("group", { name: "Transactions" })).toHaveTextContent("3");
    expect(within(output()).getByRole("group", { name: "Hits" })).toHaveTextContent("0");
    expect(within(output()).getByRole("group", { name: "Message Version" })).toHaveTextContent("pain.001.001.09");
    expect(within(output()).getByRole("group", { name: "XSD" })).toHaveTextContent("Valid");
    expect(within(output()).getByRole("heading", { name: "Sample File", level: 2 })).toBeInTheDocument();
    expect(within(output()).getByText(generated.sample_file.filename)).toBeInTheDocument();
    expect(within(output()).queryByText("No Sample File yet")).not.toBeInTheDocument();
    await user.click(within(output()).getByRole("tab", { name: "XML" }));
    expect(within(output()).getByRole("tabpanel")).toHaveTextContent('seed="echoed-seed"');

    await user.click(within(output()).getByRole("tab", { name: "Warnings (1)" }));
    expect(within(output()).getByRole("tabpanel")).toHaveTextContent("LEI dropped: not in pain.001.001.03");
  });

  it("says so when the build left no warnings", async () => {
    const user = await openFileSection();
    await user.click(generateButton());

    await user.click(await within(output()).findByRole("tab", { name: "Warnings (0)" }));

    expect(within(output()).getByRole("tabpanel")).toHaveTextContent("No warnings");
  });

  it("shows no Message Version in the version tile before the first generate", async () => {
    await openFileSection();

    expect(within(output()).getByRole("group", { name: "Message Version" })).toHaveTextContent("–");
  });

  it("clears the previous Sample File while the next one is generating", async () => {
    const user = await openFileSection();
    await user.click(generateButton());
    await within(output()).findByRole("tabpanel");
    let answer: (response: Response) => void = () => undefined;
    server.use(http.post("/api/v1/sample-files", () => new Promise<Response>((resolve) => (answer = resolve))));

    await user.click(generateButton());

    expect(await within(output()).findByText("Generating…")).toBeInTheDocument();
    expect(within(output()).queryByRole("tabpanel")).not.toBeInTheDocument();
    expect(within(output()).getByRole("group", { name: "Seed" })).toHaveTextContent("–");
    answer(HttpResponse.json(generated));
    await within(output()).findByRole("tabpanel");
  });

  it("disables Generate while the request is in flight", async () => {
    let answer: (response: Response) => void = () => undefined;
    server.use(http.post("/api/v1/sample-files", () => new Promise<Response>((resolve) => (answer = resolve))));
    const user = await openFileSection();

    await user.click(generateButton());

    expect(await screen.findByRole("button", { name: "Generating…" })).toBeDisabled();
    answer(HttpResponse.json(generated));
    expect(await within(settings()).findByRole("button", { name: "Generate" })).toBeEnabled();
  });

  it("shows a 422 as a problem block listing each field and message", async () => {
    server.use(
      http.post("/api/v1/sample-files", () =>
        HttpResponse.json(
          {
            type: "validation_error",
            title: "Request validation failed",
            status: 422,
            detail: "2 fields are invalid",
            instance: "req-1",
            errors: [
              {
                field: "transaction_count",
                message: "Input should be less than or equal to 100",
                code: "less_than_equal",
              },
              { field: "amount_max", message: "amount_max is below amount_min", code: "value_error" },
            ],
          },
          { status: 422, headers: { "Content-Type": "application/problem+json" } },
        ),
      ),
    );
    const user = await openFileSection();

    await user.click(generateButton());

    const problem = await within(output()).findByRole("alert");
    expect(problem).toHaveTextContent("Request validation failed");
    expect(problem).toHaveTextContent("transaction_count: Input should be less than or equal to 100");
    expect(problem).toHaveTextContent("amount_max: amount_max is below amount_min");
  });
});

describe("Generate mode: downloads", () => {
  const saved: { name: string; blob: Blob }[] = [];

  beforeEach(() => {
    saved.length = 0;
    const blobs = new Map<string, Blob>();
    // jsdom has no object URLs; these stand in for the browser's.
    URL.createObjectURL = (blob: Blob) => {
      const url = `blob:${blobs.size}`;
      blobs.set(url, blob);
      return url;
    };
    URL.revokeObjectURL = () => undefined;
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
      saved.push({ name: this.download, blob: blobs.get(this.getAttribute("href") ?? "") as Blob });
    });
  });

  afterEach(() => vi.restoreAllMocks());

  async function generateOnce() {
    const user = await openFileSection();
    await user.click(generateButton());
    await within(output()).findByRole("group", { name: "Seed" });
    return user;
  }

  it("saves the XML as it came back", async () => {
    const user = await generateOnce();

    await user.click(within(output()).getByRole("button", { name: "XML" }));

    expect(saved.map((s) => s.name)).toEqual(["pain.001.001.09-echoed-seed.xml"]);
    expect(await saved[0]?.blob.text()).toBe(sampleXml);
  });

  it("saves the Answer Key JSON", async () => {
    const user = await generateOnce();

    await user.click(within(output()).getByRole("button", { name: "Answer Key JSON" }));

    expect(saved.map((s) => s.name)).toEqual(["pain.001.001.09-echoed-seed.answer-key.json"]);
    expect(JSON.parse(await (saved[0]?.blob.text() ?? Promise.resolve("")))).toEqual(generated.answer_key);
  });

  it("fetches the zip by replaying the Effective Request, so it holds the same file", async () => {
    const zipRequests: { format: string | null; body: unknown }[] = [];
    server.use(
      http.post("/api/v1/sample-files", async ({ request }) => {
        const format = new URL(request.url).searchParams.get("format");
        if (format !== "zip") {
          return HttpResponse.json(generated);
        }
        zipRequests.push({ format, body: await request.json() });
        return new HttpResponse(new Uint8Array([80, 75, 3, 4]), { headers: { "Content-Type": "application/zip" } });
      }),
    );
    const user = await generateOnce();

    await user.click(within(output()).getByRole("button", { name: "Zip" }));

    await vi.waitFor(() => expect(saved.map((s) => s.name)).toEqual(["pain.001.001.09-echoed-seed.zip"]));
    expect(zipRequests).toEqual([{ format: "zip", body: generated.answer_key.request }]);
    expect(new Uint8Array(await (saved[0]?.blob.arrayBuffer() ?? Promise.resolve(new ArrayBuffer(0))))).toEqual(
      new Uint8Array([80, 75, 3, 4]),
    );
  });
});

describe("Generate mode: Exposures", () => {
  it("offers every exposure country, all chosen, and no Exposures until asked", async () => {
    await openFileSection();

    for (const code of ["RU", "BY", "IR", "KP", "SY", "VE"]) {
      expect(chip("Exposure countries", code)).toHaveAttribute("aria-pressed", "true");
    }
    expect(screen.getByRole("spinbutton", { name: "Exposures" })).toHaveValue(0);
  });

  it("posts the Exposure count and the exposure countries the user chose", async () => {
    const bodies = recordGenerateRequests();
    const user = await openFileSection();

    await user.click(chip("Exposure countries", "KP"));
    await user.click(chip("Exposure countries", "SY"));
    await user.clear(screen.getByRole("spinbutton", { name: "Exposures" }));
    await user.type(screen.getByRole("spinbutton", { name: "Exposures" }), "4");
    await user.click(generateButton());

    await within(output()).findByRole("group", { name: "Seed" });
    expect(bodies).toEqual([{ exposure_countries: ["RU", "BY", "IR", "VE"], exposure_count: 4 }]);
  });

  it("lists the Exposures apart from the Hits in the Answer Key", async () => {
    server.use(
      http.post("/api/v1/sample-files", () =>
        HttpResponse.json({
          ...generated,
          answer_key: {
            ...generated.answer_key,
            summary: { ...generated.answer_key.summary, by_exposure_country: { IR: 1 } },
            exposures: [
              {
                transaction_number: 2,
                end_to_end_id: "E2E-2",
                country: "IR",
                currency: "IRR",
                elements: ["creditor_address", "agent_bic", "account"],
              },
            ],
          },
        }),
      ),
    );
    const user = await openFileSection();
    await user.click(generateButton());

    const exposures = await within(output()).findByRole("table", { name: "Exposures" });
    expect(
      within(exposures)
        .getAllByRole("row")
        .map((row) => [...row.children].map((cell) => cell.textContent)),
    ).toEqual([
      ["Transaction", "End-to-end id", "Country", "Currency", "Elements"],
      ["2", "E2E-2", "IR", "IRR", "creditor_address, agent_bic, account"],
    ]);
    expect(within(output()).getByRole("group", { name: "Exposures" })).toHaveTextContent(/^Exposures1$/);
  });
});

describe("Generate mode: Hits", () => {
  async function generateWithHits() {
    server.use(http.post("/api/v1/sample-files", () => HttpResponse.json(generatedWithHits)));
    const user = await openFileSection();
    await user.click(generateButton());
    await within(output()).findByRole("group", { name: "Seed" });
    return user;
  }

  it("opens on the Answer Key table, one row per Hit", async () => {
    await generateWithHits();

    expect(within(output()).getByRole("tab", { name: "Answer Key", selected: true })).toBeInTheDocument();
    const rows = within(within(output()).getByRole("tabpanel")).getAllByRole("row");
    expect(rows.map((row) => [...row.children].map((cell) => cell.textContent))).toEqual([
      [
        "Hit",
        "Scope",
        "Transaction",
        "End-to-end id",
        "XPath",
        "Placement",
        "Element",
        "Rendering mode",
        "Entity",
        "Name Variant",
        "Rendered name",
        "Scheme",
        "Operations",
        "BIC",
        "LEI",
        "Triggers",
        "Lists",
      ],
      [
        "h1",
        "file",
        "",
        "",
        "/Document/CstmrCdtTrfInitn/PmtInf/Dbtr/Nm",
        "debtor",
        "",
        "",
        "daedong-credit-bank",
        "exact",
        "DAEDONG CREDIT BANK",
        "",
        "",
        "",
        "",
        "name",
        "ofac_sdn, uk",
      ],
      [
        "h2",
        "transaction",
        "1",
        "E2E-1",
        "/Document/CstmrCdtTrfInitn/PmtInf/CdtTrfTxInf[1]/CdtrAgt/FinInstnId/Nm",
        "creditor_agent",
        "",
        "name_and_bic",
        "t-bank",
        "exact",
        "T-BANK",
        "",
        "",
        "TICSRUMM",
        "",
        "name, bic",
        "ofac_sdn",
      ],
      [
        "h3",
        "transaction",
        "2",
        "E2E-2",
        "/Document/CstmrCdtTrfInitn/PmtInf/CdtTrfTxInf[2]/RmtInf/Ustrd",
        "remittance",
        "ustrd",
        "",
        "t-bank",
        "fuzzed",
        "T BANK",
        "",
        "punctuation",
        "",
        "",
        "name",
        "ofac_sdn",
      ],
    ]);
    // As on the canvas: ids and the Entity in mono, the Placement as a tag.
    const firstRow = within(rows[1] as HTMLElement).getAllByRole("cell");
    for (const column of [0, 2, 6, 8]) {
      expect(firstRow[column]).toHaveClass("font-mono");
    }
    expect(within(firstRow[5] as HTMLElement).getByText("debtor").tagName).toBe("SPAN");
    // The XPath column is cut to fit; the full path is its tooltip.
    expect(within(output()).getByRole("cell", { name: "/Document/CstmrCdtTrfInitn/PmtInf/Dbtr/Nm" })).toHaveAttribute(
      "title",
      "/Document/CstmrCdtTrfInitn/PmtInf/Dbtr/Nm",
    );
  });

  it("says so when the Sample File has no Hits", async () => {
    const user = await openFileSection();
    await user.click(generateButton());

    await within(output()).findByRole("tab", { name: "Answer Key", selected: true });
    expect(within(output()).getByRole("tabpanel")).toHaveTextContent("No Hits");
  });

  it("shows the Hit Count in the Hits tile, split into party and remittance Hits", async () => {
    await generateWithHits();

    expect(within(output()).getByRole("group", { name: "Hits" })).toHaveTextContent(/^Hits3\s*2 party · 1 remittance$/);
  });

  it("posts the Hit Count the user set, limited to two more than the transactions", async () => {
    const bodies = recordGenerateRequests();
    const user = await openFileSection();
    await user.click(screen.getByRole("button", { name: "Hits" }));

    const hitCount = screen.getByRole("spinbutton", { name: "Hit Count" });
    expect(hitCount).toHaveValue(0);
    expect(hitCount).toHaveAttribute("max", "12");
    await user.clear(hitCount);
    await user.type(hitCount, "3");
    await user.click(generateButton());

    await within(output()).findByRole("tab", { name: "Answer Key" });
    expect(bodies).toEqual([{ hit_count: 3 }]);
  });

  it("holds Generate back while the Hit Count is above the limit", async () => {
    const bodies = recordGenerateRequests();
    const user = await openFileSection();
    await user.click(screen.getByRole("button", { name: "Hits" }));

    await user.clear(screen.getByRole("spinbutton", { name: "Transactions" }));
    await user.type(screen.getByRole("spinbutton", { name: "Transactions" }), "3");
    await user.clear(screen.getByRole("spinbutton", { name: "Hit Count" }));
    await user.type(screen.getByRole("spinbutton", { name: "Hit Count" }), "6");

    expect(screen.getByText("At most 5 Hits for 3 transactions.")).toBeInTheDocument();
    expect(generateButton()).toBeDisabled();

    await user.clear(screen.getByRole("spinbutton", { name: "Hit Count" }));
    await user.type(screen.getByRole("spinbutton", { name: "Hit Count" }), "5");
    await user.click(generateButton());

    await within(output()).findByRole("tab", { name: "Answer Key" });
    expect(bodies).toEqual([{ transaction_count: 3, hit_count: 5 }]);
  });

  it("highlights each Hit's name where its XPath points, not every copy of the text", async () => {
    const user = await generateWithHits();

    await user.click(within(output()).getByRole("tab", { name: "XML" }));

    // The XML as shown, each highlight written as [id: text].
    const shown = within(output()).getByRole("tabpanel").cloneNode(true) as HTMLElement;
    for (const mark of shown.querySelectorAll("mark")) {
      mark.replaceWith(`[${mark.title}: ${mark.textContent}]`);
    }
    const [header, first, second] = (shown.textContent ?? "").split("<CdtTrfTxInf>");
    expect(header).toContain("<InitgPty>\n        <Nm>DAEDONG CREDIT BANK</Nm>");
    expect(header).toContain("<Dbtr>\n        <Nm>[h1: DAEDONG CREDIT BANK]</Nm>");
    expect(first).toContain("<Nm>[h2: T-BANK]</Nm>");
    expect(first).toContain("<Nm>Jane Smith</Nm>");
    expect(second).toContain("<Nm>T-BANK</Nm>");
    expect(second).toContain("<Ustrd>[h3: Invoice 447102 payment to T BANK]</Ustrd>");
    expect(shown.querySelectorAll("mark")).toHaveLength(0);
    expect(shown.textContent?.match(/\[h\d/g)).toHaveLength(3);
  });

  it("colours the XML's syntax around a highlighted Hit", async () => {
    const user = await generateWithHits();

    await user.click(within(output()).getByRole("tab", { name: "XML" }));

    const panel = within(output()).getByRole("tabpanel");
    const mark = within(panel).getByTitle("h1");
    const line = mark.parentElement as HTMLElement;
    expect(line).toHaveTextContent(/^\s*<Nm>DAEDONG CREDIT BANK<\/Nm>$/);
    expect(
      within(line)
        .getAllByText("Nm")
        .map((name) => name.className),
    ).toEqual(["text-tk-tag", "text-tk-tag"]);
    expect(within(line).getAllByText("<")[0]).toHaveClass("text-tk-punct");
    expect(mark).toHaveClass("bg-hit");
    expect(within(panel).getAllByText("xml")[0]).toHaveClass("text-tk-decl");
  });
});
