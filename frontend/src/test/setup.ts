import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterAll, afterEach, beforeEach, vi } from "vitest";
import { server } from "@/test/server";

// Listen before any test module loads: the generated client captures the global fetch when it is created,
// so the mock server has to have patched it by then.
server.listen({ onUnhandledFrame: "error" });

beforeEach(() => {
  // jsdom has no matchMedia; a light system scheme unless a test says otherwise.
  window.matchMedia = vi.fn(
    () => ({ matches: false, addEventListener() {}, removeEventListener() {} }) as unknown as MediaQueryList,
  );
});

afterEach(() => {
  cleanup();
  server.resetHandlers();
  vi.restoreAllMocks();
  window.localStorage.clear();
  document.documentElement.className = "";
});
afterAll(() => server.close());
