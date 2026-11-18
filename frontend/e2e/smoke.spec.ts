import { expect, test } from "@playwright/test";

test("the Workbench loads through Caddy and the header shows the app version from the API", async ({
  page,
  baseURL,
}) => {
  const origin = new URL("/", baseURL).href;
  const elsewhere: string[] = [];
  page.on("request", (request) => {
    if (!request.url().startsWith(origin)) {
      elsewhere.push(request.url());
    }
  });
  await page.goto("/");

  // The Workbench opens in Validate mode.
  await expect(page.getByRole("group", { name: "Mode" }).getByRole("button", { name: "Validate" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await expect(page.getByRole("region", { name: "Validation Report" })).toContainText("No message validated yet");
  await expect(page.getByRole("banner").getByText(/^\d+\.\d+\.\d+$/)).toBeVisible();
  // Fonts are self-hosted: nothing leaves for a font CDN.
  expect(elsewhere).toEqual([]);
});

test("the Dark theme applies and is remembered across a reload", async ({ page }) => {
  await page.emulateMedia({ colorScheme: "light" });
  await page.goto("/");
  const html = page.locator("html");
  await expect(html).not.toHaveClass(/dark/);

  await page.getByRole("group", { name: "Colour theme" }).getByRole("button", { name: "Dark theme" }).click();
  await expect(html).toHaveClass(/dark/);
  await page.reload();
  await expect(html).toHaveClass(/dark/);
  await expect(page.getByRole("button", { name: "Dark theme" })).toHaveAttribute("aria-pressed", "true");
});

test("Generate mode generates a clean Sample File through Caddy, downloads it and validates it", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("group", { name: "Mode" }).getByRole("button", { name: "Generate" }).click();
  const settings = page.getByRole("complementary", { name: "Settings" });
  await settings.getByRole("button", { name: "File" }).click();
  await settings.getByRole("combobox", { name: "Message Version" }).selectOption("pain.001.001.09");
  await settings.getByRole("spinbutton", { name: "Transactions" }).fill("3");
  await settings.getByRole("textbox", { name: "Seed" }).fill("smoke");
  await settings.getByRole("button", { name: "Generate" }).click();

  const output = page.getByRole("region", { name: "Output" });
  await expect(output.getByRole("group", { name: "Seed" })).toHaveText(/smoke/);
  await expect(output.getByRole("group", { name: "Transactions" })).toHaveText(/3/);
  await expect(output.getByRole("group", { name: "Message Version" })).toHaveText(/pain\.001\.001\.09/);
  await expect(output.getByRole("tabpanel")).toContainText("No Hits");
  await output.getByRole("tab", { name: "XML" }).click();
  await expect(output.getByRole("tabpanel")).toContainText("urn:iso:std:iso:20022:tech:xsd:pain.001.001.09");

  for (const [button, name] of [
    ["Zip", "pain.001.001.09-smoke.zip"],
    ["XML", "pain.001.001.09-smoke.xml"],
    ["Answer Key JSON", "pain.001.001.09-smoke.answer-key.json"],
  ] as const) {
    const download = page.waitForEvent("download");
    await output.getByRole("button", { name: button, exact: true }).click();
    expect((await download).suggestedFilename()).toBe(name);
  }

  await output.getByRole("button", { name: "Validate this Sample File" }).click();
  const report = page.getByRole("region", { name: "Validation Report" });
  await expect(report.getByRole("group", { name: "Verdict" })).toHaveText(/^Verdict\s*Valid$/);
  await expect(report.getByRole("group", { name: "Message Version" })).toHaveText(/pain\.001\.001\.09/);
  await expect(report.getByText("pain.001.001.09-smoke.xml")).toBeVisible();
});

test("Generate mode draws Hits and lists them in the Answer Key table and the XML", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("group", { name: "Mode" }).getByRole("button", { name: "Generate" }).click();
  const settings = page.getByRole("complementary", { name: "Settings" });
  await settings.getByRole("button", { name: "Hits" }).click();
  await settings.getByRole("spinbutton", { name: "Hit Count" }).fill("2");
  await settings.getByRole("button", { name: "Generate" }).click();

  const output = page.getByRole("region", { name: "Output" });
  await expect(output.getByRole("group", { name: "Hits" })).toHaveText(/2/);
  // A header row and one row per Hit.
  await expect(output.getByRole("tabpanel").getByRole("row")).toHaveCount(3);
  await output.getByRole("tab", { name: "XML" }).click();
  await expect(output.getByRole("tabpanel").locator("mark")).toHaveCount(2);
});

// The minimal XSD-valid .03 message the backend's validation tests use.
const SMALL_MESSAGE = `<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.03">
  <CstmrCdtTrfInitn>
    <GrpHdr><MsgId>M1</MsgId><CreDtTm>2026-01-01T09:00:00</CreDtTm><NbOfTxs>1</NbOfTxs><InitgPty/></GrpHdr>
    <PmtInf>
      <PmtInfId>P1</PmtInfId><PmtMtd>TRF</PmtMtd><ReqdExctnDt>2026-01-02</ReqdExctnDt><Dbtr/>
      <DbtrAcct><Id><IBAN>DE89370400440532013000</IBAN></Id></DbtrAcct><DbtrAgt><FinInstnId/></DbtrAgt>
      <CdtTrfTxInf>
        <PmtId><EndToEndId>E1</EndToEndId></PmtId><Amt><InstdAmt Ccy="EUR">1.00</InstdAmt></Amt><Cdtr/>
      </CdtTrfTxInf>
    </PmtInf>
  </CstmrCdtTrfInitn>
</Document>
`;

test("Validate mode sends a file through Caddy and shows its verdict", async ({ page }) => {
  await page.goto("/");

  await page.getByLabel(/Drop a pain.001 file/).setInputFiles({
    name: "small.xml",
    mimeType: "application/xml",
    buffer: Buffer.from(SMALL_MESSAGE),
  });

  const report = page.getByRole("region", { name: "Validation Report" });
  await expect(report.getByRole("group", { name: "Verdict" })).toHaveText(/^Verdict\s*Valid$/);
  await expect(report.getByText("small.xml")).toBeVisible();
  await expect(report.getByRole("group", { name: "Problems" })).toHaveText(/^Problems\s*0$/);
  await expect(report.getByText("No problems found")).toHaveCount(0);
});
