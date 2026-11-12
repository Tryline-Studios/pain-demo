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

const invalidReport: ValidationReport = {
  ...validReport,
  valid: false,
  problems: [
    {
      line: 9,
      column: 18,
      tag: "Cd",
      path: "/Document/CstmrCdtTrfInitn/PmtInf[1]/DbtrAcct/Tp/Cd",
      code: "invalid_value",
      cause: "Element 'Cd': [facet 'enumeration'] The value 'SAVING' is not an element of the set.",
      message: "Cd 'SAVING' on line 9 is not one of the allowed values",
    },
    {
      line: 12,
      column: 30,
      tag: "BIC",
      path: "/Document/CstmrCdtTrfInitn/PmtInf[1]/CdtTrfTxInf[1]/CdtrAgt/FinInstnId/BIC",
      code: "pattern_mismatch",
      cause: "Element 'BIC': [facet 'pattern'] The value 'COBA12' is not accepted by the pattern.",
      message: "BIC 'COBA12' on line 12 doesn't match the pattern",
    },
    {
      line: null,
      column: null,
      tag: null,
      path: null,
      code: "dtd_not_allowed",
      cause: null,
      message: "The message carries a DTD, which is not allowed",
    },
  ],
};

/** Answers every validation with `body`, recording what the request carried. */
function answerWith(body: object, status = 200) {
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
      return HttpResponse.json(body, {
        status,
        headers: status === 200 ? {} : { "Content-Type": "application/problem+json" },
      });
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

  it("lists every Validation Problem in report order with its code, line, message, path and cause", async () => {
    answerWith(invalidReport);
    const user = await openValidate();

    await user.type(screen.getByRole("textbox", { name: "Paste XML" }), "<Document/>");
    await user.click(screen.getByRole("button", { name: "Validate pasted XML" }));

    const rail = await within(report()).findByRole("list", { name: "Validation Problems" });
    const items = within(rail).getAllByRole("listitem");
    expect(items).toHaveLength(3);
    const [first, second, last] = items as [HTMLElement, HTMLElement, HTMLElement];
    expect(first).toHaveTextContent("invalid_value");
    expect(second).toHaveTextContent("pattern_mismatch");
    expect(second).toHaveTextContent("Line 12");
    expect(last).toHaveTextContent("dtd_not_allowed");
    expect(first).toHaveTextContent("Line 9");
    expect(first).toHaveTextContent("Cd 'SAVING' on line 9 is not one of the allowed values");
    expect(first).toHaveTextContent("/Document/CstmrCdtTrfInitn/PmtInf[1]/DbtrAcct/Tp/Cd");
    expect(first).toHaveTextContent(
      "Element 'Cd': [facet 'enumeration'] The value 'SAVING' is not an element of the set.",
    );
    expect(last).toHaveTextContent("No line");
    expect(tile("Verdict")).toHaveTextContent("Invalid");
    expect(tile("Problems")).toHaveTextContent("3");
    expect(within(report()).queryByText("No problems found")).not.toBeInTheDocument();
  });

  it("shows 100+ problems and says only the first 100 are listed when the report is truncated", async () => {
    answerWith({ ...invalidReport, truncated: true });
    const user = await openValidate();

    await user.type(screen.getByRole("textbox", { name: "Paste XML" }), "<Document/>");
    await user.click(screen.getByRole("button", { name: "Validate pasted XML" }));

    expect(await within(report()).findByText("Only the first 100 problems are shown.")).toBeInTheDocument();
    expect(tile("Problems")).toHaveTextContent("100+");
  });

  it("shows a refused request as a problem block in the report area", async () => {
    answerWith(
      {
        type: "about:blank",
        title: "Content Too Large",
        status: 413,
        detail: "The Uploaded Message is larger than 10 MB",
        instance: "req-1",
      },
      413,
    );
    const user = await openValidate();

    await user.upload(screen.getByLabelText(/Drop a pain.001 file/), new File(["<Document/>"], "huge.xml"));

    const problem = await within(report()).findByRole("alert");
    expect(problem).toHaveTextContent("Content Too Large");
    expect(problem).toHaveTextContent("The Uploaded Message is larger than 10 MB");
    expect(problem).toHaveTextContent("413");
    expect(within(report()).queryByText("No message validated yet")).not.toBeInTheDocument();
  });

  it("lists the field errors of a 422", async () => {
    answerWith(
      {
        type: "validation_error",
        title: "Validation error",
        status: 422,
        detail: "1 field failed validation",
        instance: "req-2",
        errors: [{ field: "file", message: "Field required", code: "missing" }],
      },
      422,
    );
    const user = await openValidate();

    await user.type(screen.getByRole("textbox", { name: "Paste XML" }), "<Document/>");
    await user.click(screen.getByRole("button", { name: "Validate pasted XML" }));

    const problem = await within(report()).findByRole("alert");
    expect(problem).toHaveTextContent("1 field failed validation");
    expect(problem).toHaveTextContent("file: Field required");
  });
});
