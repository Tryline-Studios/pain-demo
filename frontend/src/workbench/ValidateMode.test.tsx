import { fireEvent, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { describe, expect, it } from "vitest";
import type { components } from "@/api/schema";
import { renderWithQueries } from "@/test/render";
import { server } from "@/test/server";
import { Workbench } from "@/workbench/Workbench";

async function openValidate() {
  const user = userEvent.setup();
  renderWithQueries(<Workbench />);
  await user.click(screen.getByRole("button", { name: "Validate" }));
  return user;
}

type ValidationReport = components["schemas"]["ValidationReport"];

const SHA256 = "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08";

const validReport: ValidationReport = {
  valid: true,
  message_version: "pain.001.001.03",
  encoding: "UTF-8",
  transaction_count: 2,
  file: { name: null, size_bytes: 1234, sha256: SHA256 },
  problems: [],
  truncated: false,
};

/** Answers every validation with `body`, recording what the request carried. */
function answerWith(body: ValidationReport, status = 200) {
  const seen: { contentType: string | null; text: string; fileName: string | null }[] = [];
  server.use(
    http.post("/api/v1/validations", async ({ request }) => {
      const contentType = request.headers.get("Content-Type");
      if (contentType?.startsWith("multipart/form-data")) {
        const file = (await request.formData()).get("file");
        const isFile = file instanceof File;
        seen.push({ contentType, text: isFile ? await file.text() : "", fileName: isFile ? file.name : null });
      } else {
        seen.push({ contentType, text: await request.text(), fileName: null });
      }
      return HttpResponse.json(body, { status });
    }),
  );
  return seen;
}

function tile(name: string) {
  return within(report()).getByRole("group", { name });
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

  it("validates pasted XML as a raw application/xml body and shows a valid report", async () => {
    const seen = answerWith(validReport);
    const user = await openValidate();

    await user.type(screen.getByRole("textbox", { name: "Paste XML" }), "<Document/>");
    await user.click(screen.getByRole("button", { name: "Validate pasted XML" }));

    expect(await within(report()).findByText("No problems found")).toBeInTheDocument();
    expect(seen).toEqual([{ contentType: "application/xml", text: "<Document/>", fileName: null }]);
    expect(tile("Verdict")).toHaveTextContent("Valid");
    expect(tile("Message Version")).toHaveTextContent("pain.001.001.03");
    expect(tile("Transactions")).toHaveTextContent("2");
    expect(tile("Problems")).toHaveTextContent("0");
    expect(tile("Encoding")).toHaveTextContent("UTF-8");
    expect(within(report()).getByText("Pasted XML")).toBeInTheDocument();
    expect(within(report()).getByText("1,234 bytes")).toBeInTheDocument();
    expect(within(report()).getByText("sha256 9f86d081884c")).toBeInTheDocument();
  });

  it("sends a picked file as multipart so the report carries its name", async () => {
    const seen = answerWith({ ...validReport, file: { name: "batch.xml", size_bytes: 11, sha256: SHA256 } });
    const user = await openValidate();

    await user.upload(screen.getByLabelText(/Drop a pain.001 file/), new File(["<Document/>"], "batch.xml"));

    expect(await within(report()).findByText("batch.xml")).toBeInTheDocument();
    expect(seen).toEqual([
      {
        contentType: expect.stringMatching(/^multipart\/form-data; boundary=/),
        text: "<Document/>",
        fileName: "batch.xml",
      },
    ]);
  });

  it("validates a dropped file", async () => {
    const seen = answerWith({ ...validReport, file: { name: "dropped.xml", size_bytes: 11, sha256: SHA256 } });
    await openValidate();

    const file = new File(["<Document/>"], "dropped.xml");
    fireEvent.drop(screen.getByText(/Drop a pain.001 file/), { dataTransfer: { files: [file] } });

    expect(await within(report()).findByText("dropped.xml")).toBeInTheDocument();
    expect(seen.map((request) => request.fileName)).toEqual(["dropped.xml"]);
  });
});
