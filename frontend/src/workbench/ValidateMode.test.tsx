import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { renderWithQueries } from "@/test/render";
import { Workbench } from "@/workbench/Workbench";

async function openValidate() {
  const user = userEvent.setup();
  renderWithQueries(<Workbench />);
  await user.click(screen.getByRole("button", { name: "Validate" }));
  return user;
}

function report() {
  return screen.getByRole("region", { name: "Validation Report" });
}

describe("Validate mode", () => {
  it("switches between Generate and Validate, keeping the resizable panes", async () => {
    const user = await openValidate();

    expect(screen.getByRole("button", { name: "Validate" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("complementary", { name: "Message" })).toHaveStyle({ width: "560px" });
    expect(screen.getByRole("separator", { name: "Resize settings pane" })).toBeInTheDocument();
    expect(within(report()).getByText("No message validated yet")).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Output" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Generate" }));
    expect(within(screen.getByRole("region", { name: "Output" })).getByText("No Sample File yet")).toBeInTheDocument();
  });
});
