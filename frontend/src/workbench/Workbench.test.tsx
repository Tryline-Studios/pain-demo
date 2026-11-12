import { fireEvent, screen, within } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { describe, expect, it } from "vitest";
import { renderWithQueries } from "@/test/render";
import { server } from "@/test/server";
import { SETTINGS_WIDTH_KEY } from "@/workbench/useSettingsPaneWidth";
import { Workbench } from "@/workbench/Workbench";

function settingsPane() {
  return screen.getByRole("complementary", { name: "Settings" });
}

function resizeHandle() {
  return screen.getByRole("separator", { name: "Resize settings pane" });
}

describe("Workbench", () => {
  it("shows the app version from the API in the header", async () => {
    renderWithQueries(<Workbench />);

    expect(await within(screen.getByRole("banner")).findByText("1.2.3")).toBeInTheDocument();
  });

  it("says so when the version cannot be loaded", async () => {
    server.use(http.get("/api/v1/version", () => HttpResponse.error()));
    renderWithQueries(<Workbench />);

    expect(await within(screen.getByRole("banner")).findByText("unavailable")).toBeInTheDocument();
  });

  it("names the page in a level-one heading before the first generate", () => {
    renderWithQueries(<Workbench />);

    expect(screen.getAllByRole("heading", { level: 1 }).map((heading) => heading.textContent)).toEqual(["pain-demo"]);
  });

  it("shows the empty state in the output pane before the first generate", () => {
    renderWithQueries(<Workbench />);

    const output = screen.getByRole("region", { name: "Output" });
    expect(within(output).getByText("No Sample File yet")).toBeInTheDocument();
  });

  it("opens the File, Data and Hits sections collapsed", () => {
    renderWithQueries(<Workbench />);

    for (const name of ["File", "Data", "Hits"]) {
      expect(within(settingsPane()).getByRole("button", { name })).toHaveAttribute("aria-expanded", "false");
    }
  });

  it("opens the settings pane at 560px", () => {
    renderWithQueries(<Workbench />);

    expect(settingsPane()).toHaveStyle({ width: "560px" });
    expect(resizeHandle()).toHaveAttribute("aria-valuenow", "560");
  });

  it("resizes with the drag handle, clamped between 380px and 900px, and remembers the width", () => {
    renderWithQueries(<Workbench />);

    fireEvent.mouseDown(resizeHandle(), { clientX: 560 });
    fireEvent.mouseMove(window, { clientX: 700 });
    expect(settingsPane()).toHaveStyle({ width: "700px" });

    fireEvent.mouseMove(window, { clientX: 1500 });
    expect(settingsPane()).toHaveStyle({ width: "900px" });

    fireEvent.mouseMove(window, { clientX: 100 });
    expect(settingsPane()).toHaveStyle({ width: "380px" });

    fireEvent.mouseMove(window, { clientX: 640 });
    fireEvent.mouseUp(window);
    expect(settingsPane()).toHaveStyle({ width: "640px" });
    expect(window.localStorage.getItem(SETTINGS_WIDTH_KEY)).toBe("640");
  });

  it("resizes from the keyboard with the arrow, Home and End keys", () => {
    renderWithQueries(<Workbench />);

    fireEvent.keyDown(resizeHandle(), { key: "ArrowRight" });
    expect(settingsPane()).toHaveStyle({ width: "576px" });
    fireEvent.keyDown(resizeHandle(), { key: "ArrowLeft" });
    fireEvent.keyDown(resizeHandle(), { key: "ArrowLeft" });
    expect(settingsPane()).toHaveStyle({ width: "544px" });
    fireEvent.keyDown(resizeHandle(), { key: "End" });
    expect(settingsPane()).toHaveStyle({ width: "900px" });
    fireEvent.keyDown(resizeHandle(), { key: "Home" });
    expect(settingsPane()).toHaveStyle({ width: "380px" });
    expect(window.localStorage.getItem(SETTINGS_WIDTH_KEY)).toBe("380");
  });

  it("restores the remembered width", () => {
    window.localStorage.setItem(SETTINGS_WIDTH_KEY, "720");
    renderWithQueries(<Workbench />);

    expect(settingsPane()).toHaveStyle({ width: "720px" });
  });

  it("ignores a remembered width outside the allowed range", () => {
    window.localStorage.setItem(SETTINGS_WIDTH_KEY, "5000");
    renderWithQueries(<Workbench />);

    expect(settingsPane()).toHaveStyle({ width: "560px" });
  });
});
