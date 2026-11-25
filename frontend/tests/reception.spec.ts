import path from "node:path";
import { test, expect } from "@playwright/test";

test("schedule filters, date controls, keyboard navigation and mobile width", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page.getByText("Dr Asha Menon")).toBeVisible();
  await page.getByLabel("Filter by specialty").selectOption("Cardiology");
  await expect(page.getByText("Dr Arjun Rao")).toBeVisible();
  await expect(page.getByText("Dr Asha Menon")).toHaveCount(0);
  const before = await page.locator(".daybar strong").innerText();
  await page.route("**/api/dashboard?day=*", (route) =>
    route.fulfill({ status: 503, body: "Unavailable" }),
  );
  await page.getByRole("button", { name: "Next date" }).click();
  await expect(page.getByRole("alert")).toContainText("could not be loaded");
  await expect(page.getByText("Dr Arjun Rao")).toHaveCount(0);
  await page.unroute("**/api/dashboard?day=*");
  await page.getByRole("button", { name: "Retry", exact: true }).click();
  await expect(page.locator(".daybar strong")).not.toHaveText(before);
  await page.getByRole("button", { name: "Appointments", exact: true }).focus();
  await page.keyboard.press("Enter");
  await expect(
    page.getByRole("heading", { name: "Appointment register" }),
  ).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(
    390,
  );
});

test("browser WebRTC, mute, structured receipts and committed SSE snapshots", async ({
  page,
  request,
  context,
  browser,
}) => {
  await context.grantPermissions(["microphone"]);
  const secondContext = await browser.newContext();
  const second = await secondContext.newPage();
  await Promise.all([page.goto("/"), second.goto("http://127.0.0.1:8011/")]);
  await page.getByRole("button", { name: "Try call", exact: true }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByRole("status")).toContainText("Listening", {
    timeout: 35000,
  });
  await expect
    .poll(
      async () => (await (await request.get("/fixture/audio")).json()).frames,
    )
    .toBeGreaterThan(0);
  await dialog.getByRole("button", { name: "Mute", exact: true }).click();
  await expect(dialog.getByRole("button", { name: "Unmute" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await dialog.getByRole("button", { name: "Unmute" }).click();
  await request.post("/fixture/partial");
  await expect(
    dialog.getByText("Fixture partial", { exact: false }),
  ).toBeVisible();
  await request.post("/fixture/final");
  await request.post("/fixture/final");
  await expect(dialog.getByText("Fixture final", { exact: false })).toHaveCount(
    1,
  );
  await expect(
    dialog.getByText("Fixture partial", { exact: false }),
  ).toHaveCount(0);
  const booked = await (await request.post("/fixture/book")).json();
  expect(booked.receipt.status).toBe("Confirmed");
  await expect(dialog.getByText(booked.receipt.reference)).toBeVisible();
  await expect(dialog.getByText("Fixture transcript")).toBeVisible();
  await expect(
    second.getByRole("row").filter({ hasText: booked.receipt.reference }),
  ).toContainText("Confirmed");
  const day = booked.receipt.start.slice(0, 10);
  const snapshot = await (
    await request.get("/api/dashboard?day=" + day)
  ).json();
  expect(
    snapshot.doctors[0].slots.some(
      (s: { status: string }) => s.status === "Booked",
    ),
  ).toBeTruthy();
  if (process.env.ASTER_CAPTURE_FIXTURE === "1")
    await page.screenshot({
      path: path.resolve("../docs/evidence/fixture-booked.png"),
    });
  await secondContext.setOffline(true);
  await request.post("/fixture/cancel");
  await secondContext.setOffline(false);
  await second.bringToFront();
  await expect(
    second.getByRole("row").filter({ hasText: booked.receipt.reference }),
  ).toContainText("Cancelled");
  await expect(
    dialog.locator(".receipt").filter({ hasText: "Cancelled" }),
  ).toBeVisible();
  await secondContext.close();
  await dialog.getByRole("button", { name: "End call" }).click();
  await expect(dialog.getByRole("status")).toHaveText("Ended");
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
});

test("missing provider and denied microphone are actionable", async ({
  page,
}) => {
  await page.route("**/api/dashboard*", async (route) => {
    const res = await route.fetch();
    const data = await res.json();
    data.missing = ["ELEVENLABS_API_KEY"];
    await route.fulfill({ json: data });
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Try call", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("ELEVENLABS_API_KEY");
  await page.unroute("**/api/dashboard*");
  await page.context().grantPermissions([]);
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByRole("alert")).toContainText(/microphone|permission/i);
});
