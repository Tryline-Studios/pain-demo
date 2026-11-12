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

export const server = setupServer(
  http.get("/api/v1/version", () => HttpResponse.json(generatorVersion)),
  http.get("/api/v1/message-versions", () => HttpResponse.json(messageVersions)),
  http.get("/api/v1/options", () => HttpResponse.json(options)),
  http.post("/api/v1/sample-files", () => HttpResponse.json(generated)),
);
