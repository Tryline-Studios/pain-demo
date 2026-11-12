import { useState } from "react";
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
 * problem details body. `source` is the text that was sent, for the source view.
 */
export function useValidation() {
  const mutation = api.useMutation("post", "/api/v1/validations");
  const [source, setSource] = useState("");

  const validateXml = (xml: string) => {
    setSource(xml);
    mutation.mutate({
      body: xml,
      headers: { "Content-Type": "application/xml" },
      bodySerializer: (body) => body,
    });
  };

  // shortcut: the file is shown decoded as UTF-8 whatever its prolog declares, so a Latin-1 file shows U+FFFD for
  // its non-ASCII characters (line numbers still match); decode with the report's `encoding` if that matters.
  const validateFile = (file: File) =>
    file.text().then((text) => {
      setSource(text);
      const form = new FormData();
      form.append("file", file);
      // The generated type says `file: string` (OpenAPI's binary); FormData lets the browser set the boundary.
      mutation.mutate({ body: form as never, bodySerializer: (body) => body });
    });

  return { ...mutation, source, validateXml, validateFile };
}

export type Validation = ReturnType<typeof useValidation>;
