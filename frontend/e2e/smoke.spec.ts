import { expect, test } from "@playwright/test";

test("the Workbench loads through Caddy and the version tile shows the app version from the API", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("complementary", { name: "Settings" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Output" })).toContainText("No Sample File yet");
  const versionTile = page.getByRole("group", { name: "Version" });
  await expect(versionTile.getByText(/^\d+\.\d+\.\d+$/)).toBeVisible();
});
