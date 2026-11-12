import { Blob, File } from "node:buffer";

// Import this before the module under test in a test file that sends a multipart upload. jsdom's FormData, Blob and
// File reach Node's fetch through Vitest's shimmed Request, which drops the file name and yields a body MSW cannot
// read. Node's own classes, and Node's Request (the class Vitest's shim extends), carry it through fetch and MSW
// intact. The generated client captures `Request` when it is created, so this has to run before it is imported;
// Vitest isolates each test file, so the swap stays in the files that opt in.
const NodeFormData = (await new Response(new URLSearchParams()).formData()).constructor;
const NodeRequest = Object.getPrototypeOf(globalThis.Request);
Object.assign(globalThis, { FormData: NodeFormData, Blob, File, Request: NodeRequest });
