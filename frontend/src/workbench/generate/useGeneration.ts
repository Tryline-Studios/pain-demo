import { api } from "@/api/client";
import type { components } from "@/api/schema";
import { saveFile } from "@/lib/saveFile";

export type GenerationRequest = components["schemas"]["GenerationRequest"];
export type GeneratedSampleFile = components["schemas"]["GeneratedSampleFile"];

/** The zip or Answer Key name beside the Sample File's `<name>.xml`, as the API names them (spec 12.2). */
export function siblingFilename(sampleFilename: string, suffix: ".zip" | ".answer-key.json" | ".answer-key.csv") {
  return sampleFilename.replace(/\.xml$/, suffix);
}

/**
 * `POST /api/v1/sample-files`, or `/csv` with a CSV of Supplied Data, through the generated client (spec 13.4). A 422 lands in `error` as the problem details
 * body. The zip replays the Answer Key's Effective Request with `?format=zip`, which reproduces the same file byte
 * for byte, so nothing generated has to be kept server-side.
 */
export function useGeneration() {
  const fromJson = api.useMutation("post", "/api/v1/sample-files");
  const fromCsv = api.useMutation("post", "/api/v1/sample-files/csv");
  // Whichever endpoint the last Generate used; the other is reset.
  const mutation = fromCsv.isIdle ? fromJson : fromCsv;
  const zip = api.useMutation("post", "/api/v1/sample-files");
  const answerKeyCsv = api.useMutation("post", "/api/v1/answer-keys/csv");

  const generate = (body: Partial<GenerationRequest>) => {
    zip.reset();
    answerKeyCsv.reset();
    fromCsv.reset();
    // Every field is optional on the wire; the generated type marks the ones with defaults as required.
    fromJson.mutate({ body: body as GenerationRequest });
  };

  /** `POST /api/v1/sample-files/csv`: the settings and Hits as the `request` part, the file as `supplied_data`. */
  const generateFromCsv = (body: Partial<GenerationRequest>, csv: File) => {
    zip.reset();
    answerKeyCsv.reset();
    fromJson.reset();
    const form = new FormData();
    form.append("request", JSON.stringify(body));
    form.append("supplied_data", csv);
    // The generated type says `supplied_data: string` (OpenAPI's binary); FormData lets the browser set the boundary.
    fromCsv.mutate({ body: form as never, bodySerializer: (body) => body });
  };

  const downloadZip = (generated: GeneratedSampleFile) =>
    zip.mutate(
      { params: { query: { format: "zip" } }, body: generated.answer_key.request, parseAs: "blob" },
      // openapi-fetch types the body by media type, not by `parseAs`; with "blob" it is a Blob.
      {
        onSuccess: (blob) => saveFile(blob as unknown as Blob, siblingFilename(generated.sample_file.filename, ".zip")),
      },
    );

  // The CSV projection lives in the API alone (spec 11.1), so the Workbench posts the Answer Key back for it.
  const downloadAnswerKeyCsv = (generated: GeneratedSampleFile) =>
    answerKeyCsv.mutate(
      // The Answer Key goes back as it came. openapi-fetch's `Writable` reads a null-only property (`displaced`) as
      // read-only (`NonNullable<null>` is `never`) and forbids it, so no Answer Key type fits its body type.
      { body: generated.answer_key as never, parseAs: "blob" },
      {
        onSuccess: (blob) =>
          saveFile(blob as unknown as Blob, siblingFilename(generated.sample_file.filename, ".answer-key.csv")),
      },
    );

  // Without `format=zip` the 200 is always the JSON envelope; the union with the zip's binary is the OpenAPI's.
  const data = mutation.data as GeneratedSampleFile | undefined;
  return {
    ...mutation,
    data,
    generate,
    generateFromCsv,
    downloadZip,
    downloadAnswerKeyCsv,
    downloadError: zip.error ?? answerKeyCsv.error,
  };
}

export type Generation = ReturnType<typeof useGeneration>;
