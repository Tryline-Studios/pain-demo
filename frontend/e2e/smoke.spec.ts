import { expect, test } from "@playwright/test";

test("the Workbench loads through Caddy and the version tile shows the app version from the API", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("complementary", { name: "Settings" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Output" })).toContainText("No Sample File yet");
  const versionTile = page.getByRole("group", { name: "Version" });
  await expect(versionTile.getByText(/^\d+\.\d+\.\d+$/)).toBeVisible();
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
  await page.getByRole("button", { name: "Validate" }).click();

  await page.getByLabel(/Drop a pain.001 file/).setInputFiles({
    name: "small.xml",
    mimeType: "application/xml",
    buffer: Buffer.from(SMALL_MESSAGE),
  });

  const report = page.getByRole("region", { name: "Validation Report" });
  await expect(report.getByRole("group", { name: "Verdict" })).toHaveText(/^Verdict\s*Valid$/);
  await expect(report.getByText("small.xml")).toBeVisible();
  await expect(report.getByText("No problems found")).toBeVisible();
});
