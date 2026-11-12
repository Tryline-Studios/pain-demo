import { HttpResponse, http } from "msw";
import { setupServer } from "msw/node";
import type { components } from "@/api/schema";

export const generatorVersion: components["schemas"]["GeneratorVersion"] = {
  app_version: "1.2.3",
  git_sha: "0123456789abcdef0123456789abcdef01234567",
  pain001: "0.0.70",
  faker: "40.39.0",
  schwifty: "2026.7.3",
  iuliia: "0.13.0",
  rapidfuzz: "3.14.6",
  catalogue_snapshot: "2026-09-17",
};

export const messageVersions: components["schemas"]["MessageVersionOption"][] = [
  { message_version: "pain.001.001.03", default: true },
  { message_version: "pain.001.001.09", default: false },
  { message_version: "pain.001.001.13", default: false },
];

export const options: components["schemas"]["Options"] = {
  countries: [
    { country: "GB", currency: "GBP" },
    { country: "DE", currency: "EUR" },
    { country: "FR", currency: "EUR" },
    { country: "PL", currency: "PLN" },
    { country: "US", currency: "USD" },
  ],
  limits: { max_transactions: 100, max_seed_length: 64 },
  defaults: {
    message_version: "pain.001.001.03",
    transaction_count: 10,
    countries: ["GB", "DE"],
    amount_min: "10.00",
    amount_max: "50000.00",
  },
};

export const sampleXml = `<?xml version='1.0' encoding='UTF-8'?>
<!-- pain-demo 1.2.3 seed="echoed-seed" -->
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.09"/>
`;

export const generated: components["schemas"]["GeneratedSampleFile"] = {
  sample_file: {
    filename: "pain.001.001.09-echoed-seed.xml",
    content_type: "application/xml",
    xml: sampleXml,
  },
  answer_key: {
    answer_key_version: 1,
    seed: "echoed-seed",
    message_version: "pain.001.001.09",
    generator: generatorVersion,
    request: {
      message_version: "pain.001.001.09",
      seed: "echoed-seed",
      created_at: "2026-11-12T09:30:00Z",
      execution_date: "2026-11-13",
      message_id: "MSG-0123456789AB",
      transaction_count: 3,
      hit_count: 0,
      countries: ["DE", "US"],
      currencies: null,
      amount_min: "10.00",
      amount_max: "50000.00",
    },
    file: {
      message_id: "MSG-0123456789AB",
      created_at: "2026-11-12T09:30:00Z",
      execution_date: "2026-11-13",
      transaction_count: 3,
      hit_count: 0,
      sha256: "0".repeat(64),
    },
    summary: { by_placement: {}, by_name_variant: {}, by_entity_type: {}, by_list: {}, by_exposure_country: {} },
    hits: [],
    exposures: [],
    transactions: [
      { number: 1, end_to_end_id: "E2E-1", hit_ids: [] },
      { number: 2, end_to_end_id: "E2E-2", hit_ids: [] },
      { number: 3, end_to_end_id: "E2E-3", hit_ids: [] },
    ],
    warnings: [],
  },
};

/**
 * Two transactions with a file-level Debtor Hit (its name also sits in `InitgPty`, unmarked) and the same agent name
 * hit in both transactions' Creditor Agent, so highlighting must follow the XPath, not the text.
 */
export const xmlWithHits = `<?xml version='1.0' encoding='UTF-8'?>
<!-- pain-demo 1.2.3 seed="hits" -->
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.09">
  <CstmrCdtTrfInitn>
    <GrpHdr>
      <MsgId>MSG-1</MsgId>
      <InitgPty>
        <Nm>DAEDONG CREDIT BANK</Nm>
      </InitgPty>
    </GrpHdr>
    <PmtInf>
      <Dbtr>
        <Nm>DAEDONG CREDIT BANK</Nm>
      </Dbtr>
      <CdtTrfTxInf>
        <PmtId>
          <EndToEndId>E2E-1</EndToEndId>
        </PmtId>
        <CdtrAgt>
          <FinInstnId>
            <BICFI>TICSRUMM</BICFI>
            <Nm>T-BANK</Nm>
          </FinInstnId>
        </CdtrAgt>
        <Cdtr>
          <Nm>Jane Smith</Nm>
        </Cdtr>
      </CdtTrfTxInf>
      <CdtTrfTxInf>
        <PmtId>
          <EndToEndId>E2E-2</EndToEndId>
        </PmtId>
        <CdtrAgt>
          <FinInstnId>
            <BICFI>TICSRUMM</BICFI>
            <Nm>T-BANK</Nm>
          </FinInstnId>
        </CdtrAgt>
        <Cdtr>
          <Nm>John Doe</Nm>
        </Cdtr>
      </CdtTrfTxInf>
    </PmtInf>
  </CstmrCdtTrfInitn>
</Document>
`;

function tBankHit(id: string, transaction: number): components["schemas"]["Hit"] {
  return {
    id,
    scope: "transaction",
    transaction_number: transaction,
    end_to_end_id: `E2E-${transaction}`,
    xpath: `/Document/CstmrCdtTrfInitn/PmtInf/CdtTrfTxInf[${transaction}]/CdtrAgt/FinInstnId/Nm`,
    entity: { id: "t-bank", entity_type: "bank", listings: [{ list: "ofac_sdn", entry_id: "44259" }] },
    placement: "creditor_agent",
    rendering_mode: "name_and_bic",
    name: {
      variant: "exact",
      rendered: "T-BANK",
      source: { value: "T-BANK", type: "primary", script: "latin", listing: { list: "ofac_sdn", entry_id: "44259" } },
    },
    bic: { value: "TICSRUMM", source: "listing" },
    lei: null,
    address_from_listing: "44259",
    triggers: [
      { kind: "name", value: "T-BANK", listed_on: ["ofac_sdn"] },
      { kind: "bic", value: "TICSRUMM", listed_on: ["ofac_sdn"] },
    ],
    origin: "drawn",
    paired_with: null,
    displaced: null,
  };
}

/** A file-level Debtor Hit and a Creditor Agent Hit in each of two transactions. */
export const generatedWithHits: components["schemas"]["GeneratedSampleFile"] = {
  sample_file: { ...generated.sample_file, xml: xmlWithHits },
  answer_key: {
    ...generated.answer_key,
    request: { ...generated.answer_key.request, transaction_count: 2, hit_count: 3 },
    file: { ...generated.answer_key.file, transaction_count: 2, hit_count: 3 },
    hits: [
      {
        id: "h1",
        scope: "file",
        xpath: "/Document/CstmrCdtTrfInitn/PmtInf/Dbtr/Nm",
        entity: {
          id: "daedong-credit-bank",
          entity_type: "bank",
          listings: [
            { list: "ofac_sdn", entry_id: "16085" },
            { list: "uk", entry_id: "DPR0131" },
          ],
        },
        placement: "debtor",
        name: {
          variant: "exact",
          rendered: "DAEDONG CREDIT BANK",
          source: {
            value: "DAEDONG CREDIT BANK",
            type: "primary",
            script: "latin",
            listing: { list: "ofac_sdn", entry_id: "16085" },
          },
        },
        bic: null,
        lei: null,
        address_from_listing: "DPR0131",
        triggers: [{ kind: "name", value: "DAEDONG CREDIT BANK", listed_on: ["ofac_sdn"] }],
        origin: "drawn",
        paired_with: null,
        displaced: null,
      },
      tBankHit("h2", 1),
      tBankHit("h3", 2),
    ],
    transactions: [
      { number: 1, end_to_end_id: "E2E-1", hit_ids: ["h1", "h2"] },
      { number: 2, end_to_end_id: "E2E-2", hit_ids: ["h1", "h3"] },
    ],
  },
};

export const server = setupServer(
  http.get("/api/v1/version", () => HttpResponse.json(generatorVersion)),
  http.get("/api/v1/message-versions", () => HttpResponse.json(messageVersions)),
  http.get("/api/v1/options", () => HttpResponse.json(options)),
  http.post("/api/v1/sample-files", () => HttpResponse.json(generated)),
);
