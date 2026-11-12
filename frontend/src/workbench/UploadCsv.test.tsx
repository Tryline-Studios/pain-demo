import "@/test/multipart";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { afterEach, describe, expect, it, vi } from "vitest";
import { renderWithQueries } from "@/test/render";
import { generated, server } from "@/test/server";
import { Workbench } from "@/workbench/Workbench";

const HEADER = "payment.debtor.name,creditor.name,intermediary_agents.0.bic,amount";

async function chooseUploadCsv() {
  const user = userEvent.setup();
  renderWithQueries(<Workbench />);
  await user.click(screen.getByRole("button", { name: "Data" }));
  await user.click(screen.getByRole("radio", { name: /Upload CSV/ }));
  return user;
}

function generateButton() {
  return within(screen.getByRole("complementary", { name: "Settings" })).getByRole("button", { name: "Generate" });
}

describe("Generate mode: Supplied Data as CSV", () => {
  afterEach(() => vi.restoreAllMocks());

  it("shows the expected header and posts the file beside the settings as JSON", async () => {
    const seen: { request: unknown; csv: string }[] = [];
    server.use(
      http.post("/api/v1/sample-files/csv", async ({ request }) => {
        const form = await request.formData();
        const file = form.get("supplied_data");
        seen.push({
          request: JSON.parse(String(form.get("request"))),
          csv: file instanceof File ? await file.text() : "",
        });
        return HttpResponse.json(generated);
      }),
    );
    const user = await chooseUploadCsv();

    expect(await screen.findByText(HEADER)).toBeInTheDocument();
    expect(generateButton()).toBeDisabled();
    const csv = `${HEADER}\nOur Debtor Ltd,Acme,,12.50\n`;
    await user.upload(screen.getByLabelText("Supplied Data CSV"), new File([csv], "data.csv", { type: "text/csv" }));
    await waitFor(() => expect(generateButton()).toBeEnabled());
    await user.click(generateButton());

    await within(screen.getByRole("region", { name: "Output" })).findByRole("tab", { name: "Answer Key" });
    expect(seen).toEqual([{ request: {}, csv }]);
  });

  it("downloads the header template", async () => {
    const saved: Blob[] = [];
    URL.createObjectURL = (blob: Blob) => {
      saved.push(blob);
      return "blob:template";
    };
    URL.revokeObjectURL = () => undefined;
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    const user = await chooseUploadCsv();

    await user.click(await screen.findByRole("button", { name: "Download header template" }));

    expect((click.mock.contexts[0] as HTMLAnchorElement).download).toBe("supplied-data-template.csv");
    expect(await saved[0]?.text()).toBe(`${HEADER}\n`);
  });

  it("shows a 422 against the row and column", async () => {
    server.use(
      http.post("/api/v1/sample-files/csv", () =>
        HttpResponse.json(
          {
            type: "validation_error",
            title: "Validation error",
            status: 422,
            detail: "1 field failed validation",
            instance: "req-1",
            errors: [{ field: "supplied_data.creditor.nickname", message: "unknown column", code: "value_error" }],
          },
          { status: 422, headers: { "Content-Type": "application/problem+json" } },
        ),
      ),
    );
    const user = await chooseUploadCsv();
    await user.upload(screen.getByLabelText("Supplied Data CSV"), new File(["creditor.nickname\nAce\n"], "d.csv"));
    await waitFor(() => expect(generateButton()).toBeEnabled());
    await user.click(generateButton());

    expect(await screen.findByRole("alert")).toHaveTextContent("supplied_data.creditor.nickname: unknown column");
  });
});
