import { api } from "@/api/client";

/**
 * `POST /api/v1/validations` through the generated client (spec 17.9). A file goes as multipart so the report
 * carries its name; pasted XML goes as a raw `application/xml` body. A 413, 415 or 422 lands in `error` as the
 * problem details body.
 */
export function useValidation() {
  const mutation = api.useMutation("post", "/api/v1/validations");

  const validateXml = (xml: string) =>
    mutation.mutate({
      body: xml,
      headers: { "Content-Type": "application/xml" },
      bodySerializer: (body) => body,
    });

  const validateFile = (file: File) => {
    const form = new FormData();
    form.append("file", file);
    // The generated type says `file: string` (OpenAPI's binary); FormData lets the browser set the boundary.
    mutation.mutate({ body: form as never, bodySerializer: (body) => body });
  };

  return { ...mutation, validateXml, validateFile };
}

export type Validation = ReturnType<typeof useValidation>;
