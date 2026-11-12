import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, within } from "@testing-library/react";
import type { ReactElement } from "react";
import { Workbench } from "@/workbench/Workbench";

/** Renders under a fresh QueryClient with retries off, so a failing request fails the test fast. */
export function renderWithQueries(ui: ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

/** Renders the Workbench and leaves its default Validate mode for Generate. */
export function renderGenerateMode() {
  const result = renderWithQueries(<Workbench />);
  fireEvent.click(within(screen.getByRole("group", { name: "Mode" })).getByRole("button", { name: "Generate" }));
  return result;
}
