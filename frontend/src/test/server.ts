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

export const server = setupServer(http.get("/api/v1/version", () => HttpResponse.json(generatorVersion)));
