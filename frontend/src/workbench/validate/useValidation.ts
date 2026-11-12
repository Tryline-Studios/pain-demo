import { useMemo, useState } from "react";
import { api } from "@/api/client";
import type { components } from "@/api/schema";

export type ValidationProblem = components["schemas"]["ValidationProblem"];

/** A React key for a problem: problems carry no id, and this tuple is unique within one report. */
export function problemKey(problem: ValidationProblem) {
  return `${problem.line}:${problem.column}:${problem.code}:${problem.path}:${problem.message}`;
}

/**
 * `POST /api/v1/validations` through the generated client (spec 17.9). A file goes as multipart so the report
 * carries its name; pasted XML goes as a raw `application/xml` body. A 413, 415 or 422 lands in `error` as the
 * problem details body. `source` is the text that was sent, for the source view: a file's bytes are decoded with the
 * encoding the report names, so the source view shows what the server validated.
 */
export function useValidation() {
  const mutation = api.useMutation("post", "/api/v1/validations");
  const [sent, setSent] = useState<string | ArrayBuffer>("");
  const encoding = mutation.data?.encoding ?? null;
  const source = useMemo(() => (typeof sent === "string" ? sent : decode(sent, encoding)), [sent, encoding]);

  const validateXml = (xml: string) => {
    setSent(xml);
    mutation.mutate({
      body: xml,
      headers: { "Content-Type": "application/xml" },
      bodySerializer: (body) => body,
    });
  };

  const validateFile = (file: File) =>
    file.arrayBuffer().then((bytes) => {
      setSent(bytes);
      const form = new FormData();
      form.append("file", file);
      // The generated type says `file: string` (OpenAPI's binary); FormData lets the browser set the boundary.
      mutation.mutate({ body: form as never, bodySerializer: (body) => body });
    });

  return { ...mutation, source, validateXml, validateFile };
}

/** Decodes with the encoding the report names; UTF-8 when it names none (a malformed file) or one the browser lacks. */
function decode(bytes: ArrayBuffer, encoding: string | null) {
  try {
    return new TextDecoder(encoding ?? "utf-8").decode(bytes);
  } catch {
    return new TextDecoder().decode(bytes);
  }
}

export type Validation = ReturnType<typeof useValidation>;
