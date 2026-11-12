import { api } from "@/api/client";
import type { components } from "@/api/schema";

export type GenerationRequest = components["schemas"]["GenerationRequest"];
export type GeneratedSampleFile = components["schemas"]["GeneratedSampleFile"];

/** Hands the browser a file to save. */
export function saveFile(blob: Blob, name: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  URL.revokeObjectURL(url);
}

/**
 * `POST /api/v1/sample-files` through the generated client (spec 13.4). A 422 lands in `error` as the problem details
 * body. The zip replays the Answer Key's Effective Request with `?format=zip`, which reproduces the same file byte
 * for byte, so nothing generated has to be kept server-side.
 */
export function useGeneration() {
  const mutation = api.useMutation("post", "/api/v1/sample-files");
  const zip = api.useMutation("post", "/api/v1/sample-files");

  const generate = (body: Partial<GenerationRequest>) => {
    zip.reset();
    // Every field is optional on the wire; the generated type marks the ones with defaults as required.
    mutation.mutate({ body: body as GenerationRequest });
  };

  const downloadZip = (generated: GeneratedSampleFile) =>
    zip.mutate(
      { params: { query: { format: "zip" } }, body: generated.answer_key.request, parseAs: "blob" },
      // openapi-fetch types the body by media type, not by `parseAs`; with "blob" it is a Blob.
      {
        onSuccess: (blob) =>
          saveFile(blob as unknown as Blob, generated.sample_file.filename.replace(/\.xml$/, ".zip")),
      },
    );

  // Without `format=zip` the 200 is always the JSON envelope; the union with the zip's binary is the OpenAPI's.
  const data = mutation.data as GeneratedSampleFile | undefined;
  return { ...mutation, data, generate, downloadZip, zipError: zip.error };
}

export type Generation = ReturnType<typeof useGeneration>;
