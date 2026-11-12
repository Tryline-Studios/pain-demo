import "@testing-library/jest-dom/vitest";
import { Blob, File } from "node:buffer";
import { cleanup } from "@testing-library/react";
import { afterAll, afterEach } from "vitest";
import { server } from "@/test/server";

// jsdom's FormData, Blob and File reach Node's fetch through Vitest's shimmed Request, which drops the file name
// and yields a body MSW cannot read, so a multipart upload never arrives. Node's own classes, and Node's Request
// (the class Vitest's shim extends), carry it through fetch and MSW intact.
const NodeFormData = (await new Response(new URLSearchParams()).formData()).constructor;
const NodeRequest = Object.getPrototypeOf(globalThis.Request);
Object.assign(globalThis, { FormData: NodeFormData, Blob, File, Request: NodeRequest });

// Listen before any test module loads: the generated client captures the global fetch when it is created,
// so the mock server has to have patched it by then.
server.listen({ onUnhandledFrame: "error" });

afterEach(() => {
  cleanup();
  server.resetHandlers();
  window.localStorage.clear();
});
afterAll(() => server.close());
