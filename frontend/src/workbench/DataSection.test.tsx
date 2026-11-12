import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { describe, expect, it } from "vitest";
import { renderWithQueries } from "@/test/render";
import { generated, server } from "@/test/server";
import { Workbench } from "@/workbench/Workbench";

function settings() {
  return screen.getByRole("complementary", { name: "Settings" });
}

async function openDataSection() {
  const user = userEvent.setup();
  renderWithQueries(<Workbench />);
  await user.click(screen.getByRole("button", { name: "Data" }));
  return user;
}

function recordGenerateRequests() {
  const bodies: Record<string, unknown>[] = [];
  server.use(
    http.post("/api/v1/sample-files", async ({ request }) => {
      bodies.push((await request.json()) as Record<string, unknown>);
      return HttpResponse.json(generated);
    }),
  );
  return bodies;
}

/** Generate, once the options have loaded and the button is enabled. */
async function generate(user: ReturnType<typeof userEvent.setup>) {
  const button = within(settings()).getByRole("button", { name: "Generate" });
  await waitFor(() => expect(button).toBeEnabled());
  await user.click(button);
}

async function answerKeyTab() {
  await within(screen.getByRole("region", { name: "Output" })).findByRole("tab", { name: "Answer Key" });
}

describe("Generate mode: the Data section", () => {
  it("generates everything by default and sends no Supplied Data", async () => {
    const bodies = recordGenerateRequests();
    const user = await openDataSection();

    expect(screen.getByRole("radio", { name: /Generated only/ })).toBeChecked();
    await generate(user);

    await answerKeyTab();
    expect(bodies).toHaveLength(1);
    expect(bodies[0]).not.toHaveProperty("payment");
    expect(bodies[0]).not.toHaveProperty("transactions");
  });

  it("sends supplied fields, absent where left empty and null where left out", async () => {
    const bodies = recordGenerateRequests();
    const user = await openDataSection();

    await user.click(screen.getByRole("radio", { name: /Supply some fields/ }));
    await user.type(screen.getByRole("textbox", { name: "Debtor name" }), "Our Debtor Ltd");
    await user.click(screen.getByRole("button", { name: "Add transaction" }));
    const row = screen.getByRole("group", { name: "Transaction 1" });
    await user.type(within(row).getByRole("textbox", { name: "Creditor name" }), "Acme");
    await user.type(within(row).getByRole("textbox", { name: "Amount" }), "12.50");
    const ultimateDebtor = within(row).getByRole("radiogroup", { name: "Ultimate Debtor" });
    await user.click(within(ultimateDebtor).getByRole("radio", { name: "Leave out" }));
    const ultimateCreditor = within(row).getByRole("radiogroup", { name: "Ultimate Creditor" });
    expect(within(ultimateCreditor).getByRole("radio", { name: "Generate" })).toBeChecked();
    await user.click(within(ultimateCreditor).getByRole("radio", { name: "Supply" }));
    await user.type(within(row).getByRole("textbox", { name: "Ultimate Creditor name" }), "Parent plc");
    await user.click(screen.getByRole("button", { name: "Add transaction" }));
    await generate(user);

    await answerKeyTab();
    expect(bodies[0]).toMatchObject({
      transaction_count: 10,
      payment: { debtor: { name: "Our Debtor Ltd" } },
      transactions: [
        {
          creditor: { name: "Acme" },
          amount: "12.50",
          ultimate_debtor: null,
          ultimate_creditor: { name: "Parent plc" },
        },
        {},
      ],
    });
  });

  it("shows a 422 on the supplied field its dotted path names", async () => {
    server.use(
      http.post("/api/v1/sample-files", () =>
        HttpResponse.json(
          {
            type: "validation_error",
            title: "Validation error",
            status: 422,
            detail: "1 field failed validation",
            instance: "req-1",
            errors: [{ field: "transactions[0].creditor.name", message: "names a catalogue Entity", code: "x" }],
          },
          { status: 422, headers: { "Content-Type": "application/problem+json" } },
        ),
      ),
    );
    const user = await openDataSection();
    await user.click(screen.getByRole("radio", { name: /Supply some fields/ }));
    await user.click(screen.getByRole("button", { name: "Add transaction" }));
    const row = screen.getByRole("group", { name: "Transaction 1" });
    await user.type(within(row).getByRole("textbox", { name: "Creditor name" }), "Rosneft");
    await generate(user);

    await screen.findByRole("alert");
    const name = within(row).getByRole("textbox", { name: "Creditor name" });
    expect(name).toHaveAttribute("aria-invalid", "true");
    expect(name).toHaveAccessibleDescription("names a catalogue Entity");
  });
});
