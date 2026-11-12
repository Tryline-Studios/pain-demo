import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { describe, expect, it } from "vitest";
import { renderWithQueries } from "@/test/render";
import { generated, server } from "@/test/server";
import { Workbench } from "@/workbench/Workbench";

async function openHitsSection() {
  const user = userEvent.setup();
  renderWithQueries(<Workbench />);
  await user.click(screen.getByRole("button", { name: "Hits" }));
  await screen.findByRole("button", { name: "Add named Hit" });
  return user;
}

function settings() {
  return screen.getByRole("complementary", { name: "Settings" });
}

function generateButton() {
  return within(settings()).getByRole("button", { name: "Generate" });
}

function row(n: number) {
  return screen.getByRole("group", { name: `Named Hit ${n}` });
}

function option(select: HTMLElement, name: string | RegExp) {
  return within(select).getByRole("option", { name });
}

/** Adds a row and picks its Entity once the catalogue has loaded. */
async function addHit(user: ReturnType<typeof userEvent.setup>, n: number, entity: string) {
  await user.click(screen.getByRole("button", { name: "Add named Hit" }));
  const select = within(row(n)).getByRole("combobox", { name: "Entity" });
  await within(select).findByRole("option", { name: entity });
  await user.selectOptions(select, entity);
  return row(n);
}

function recordGenerateRequests() {
  const bodies: unknown[] = [];
  server.use(
    http.post("/api/v1/sample-files", async ({ request }) => {
      bodies.push(await request.json());
      return HttpResponse.json(generated);
    }),
  );
  return bodies;
}

async function setHitCount(user: ReturnType<typeof userEvent.setup>, count: string) {
  const hitCount = screen.getByRole("spinbutton", { name: "Hit Count" });
  await user.clear(hitCount);
  await user.type(hitCount, count);
}

describe("Generate mode: named Hits", () => {
  it("groups the Entities by type", async () => {
    const user = await openHitsSection();
    await user.click(screen.getByRole("button", { name: "Add named Hit" }));

    const select = within(row(1)).getByRole("combobox", { name: "Entity" });
    const banks = await within(select).findByRole("group", { name: "Banks" });
    expect(
      within(banks)
        .getAllByRole("option")
        .map((o) => o.textContent),
    ).toEqual(["PLAIN BANK", "PJSC SBERBANK"]);
    expect(within(select).getByRole("group", { name: "Individuals" })).toHaveTextContent(
      "Simon Alejandro ZERPA DELGADO",
    );
  });

  it("posts only what a row pins, with the allowlist chips", async () => {
    const bodies = recordGenerateRequests();
    const user = await openHitsSection();
    await setHitCount(user, "3");

    const hit = await addHit(user, 1, "PJSC SBERBANK");
    await user.selectOptions(within(hit).getByRole("combobox", { name: "Placement" }), "creditor_agent");
    await user.type(within(hit).getByRole("spinbutton", { name: "Transaction" }), "2");
    await user.selectOptions(within(hit).getByRole("combobox", { name: "Rendering mode" }), "bic_only");
    await user.click(
      within(screen.getByRole("group", { name: "Drawn Placements" })).getByRole("button", { name: "creditor" }),
    );
    await user.click(
      within(screen.getByRole("group", { name: "Drawn Name Variants" })).getByRole("button", { name: "alias" }),
    );
    await user.click(generateButton());

    await screen.findByRole("tab", { name: "Answer Key" });
    expect(bodies).toEqual([
      {
        hit_count: 3,
        hits: [{ entity: "sberbank", placement: "creditor_agent", transaction: 2, rendering_mode: "bic_only" }],
        placements: ["creditor"],
        name_variants: ["alias"],
      },
    ]);
  });

  it("disables the Placements and Name Variants an Entity cannot take, and marks file-level ones", async () => {
    const user = await openHitsSection();
    const hit = await addHit(user, 1, "Simon Alejandro ZERPA DELGADO");

    const placement = within(hit).getByRole("combobox", { name: "Placement" });
    expect(option(placement, "Creditor Agent")).toBeDisabled();
    expect(option(placement, "Creditor")).toBeEnabled();
    expect(option(placement, "Debtor (file-level)")).toBeEnabled();
    const variant = within(hit).getByRole("combobox", { name: "Name Variant" });
    expect(option(variant, "alias")).toBeDisabled();
    expect(option(variant, "fuzzed")).toBeEnabled();
    expect(within(hit).queryByRole("combobox", { name: "Rendering mode" })).toBeNull();
  });

  it("disables the transaction for a file-level Placement", async () => {
    const user = await openHitsSection();
    const hit = await addHit(user, 1, "PJSC SBERBANK");

    await user.selectOptions(within(hit).getByRole("combobox", { name: "Placement" }), "debtor_agent");

    expect(within(hit).getByRole("spinbutton", { name: "Transaction" })).toBeDisabled();
  });

  it("offers bic_only only to a Bank with a BIC", async () => {
    const user = await openHitsSection();
    const hit = await addHit(user, 1, "PLAIN BANK");

    expect(option(within(hit).getByRole("combobox", { name: "Rendering mode" }), "bic_only")).toBeDisabled();
  });

  it("offers the controller only to a controlled Entity, and posts it", async () => {
    const bodies = recordGenerateRequests();
    const user = await openHitsSection();
    await setHitCount(user, "2");

    const plain = await addHit(user, 1, "PLAIN BANK");
    expect(within(plain).queryByRole("checkbox")).toBeNull();
    await user.click(within(plain).getByRole("button", { name: "Remove" }));
    const hit = await addHit(user, 1, "PJSC SBERBANK");
    await user.click(within(hit).getByRole("checkbox", { name: "Add controller as Ultimate party" }));
    await user.click(generateButton());

    await screen.findByRole("tab", { name: "Answer Key" });
    expect(bodies).toEqual([{ hit_count: 2, hits: [{ entity: "sberbank", with_controller: true }] }]);
  });

  it("renders 422 errors inline on the rows the dotted paths point at", async () => {
    server.use(
      http.post("/api/v1/sample-files", () =>
        HttpResponse.json(
          {
            type: "validation_error",
            title: "Request validation failed",
            status: 422,
            detail: "1 field failed validation",
            instance: "req-1",
            errors: [
              {
                field: "hits[1].name_variant",
                message: "simon-zerpa: does not support the alias Name Variant",
                code: "value_error",
              },
            ],
          },
          { status: 422, headers: { "Content-Type": "application/problem+json" } },
        ),
      ),
    );
    const user = await openHitsSection();
    await setHitCount(user, "2");
    await addHit(user, 1, "PJSC SBERBANK");
    await addHit(user, 2, "Simon Alejandro ZERPA DELGADO");
    await user.click(generateButton());

    expect(await within(row(2)).findByText(/does not support the alias Name Variant/)).toBeInTheDocument();
    expect(within(row(2)).getByRole("combobox", { name: "Name Variant" })).toHaveAttribute("aria-invalid", "true");
    expect(within(row(1)).queryByText(/does not support/)).toBeNull();
  });
});
