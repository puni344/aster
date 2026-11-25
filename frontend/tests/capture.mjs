import { chromium } from "@playwright/test";
import { mkdir } from "node:fs/promises";
const dir = new URL("../../docs/evidence/", import.meta.url);
await mkdir(dir, { recursive: true });
const browser = await chromium.launch({
  channel: process.env.ASTER_BROWSER || "msedge",
});
try {
  for (const [width, height] of [
    [1440, 900],
    [1280, 800],
    [390, 844],
  ]) {
    const page = await browser.newPage({ viewport: { width, height } });
    await page.goto("http://127.0.0.1:8000");
    await page.getByText("Dr Asha Menon").waitFor();
    await page.screenshot({
      path: decodeURIComponent(
        new URL((process.argv[2] || "final") + "-" + width + ".png", dir)
          .pathname,
      ).replace(/^\/(\w:)/, "$1"),
    });
    console.log(
      width,
      "viewport / document width",
      await page.evaluate(() => document.documentElement.scrollWidth),
    );
    if (width !== 1280) {
      await page.getByRole("button", { name: "Try call", exact: true }).click();
      await page.getByRole("dialog").waitFor();
      await page
        .getByRole("status")
        .filter({ hasText: "Call unavailable" })
        .waitFor({ timeout: 3500 })
        .catch(() => {});
      await page.screenshot({
        path: decodeURIComponent(
          new URL((process.argv[2] || "final") + "-call-" + width + ".png", dir)
            .pathname,
        ).replace(/^\/(\w:)/, "$1"),
      });
    }
    await page.close();
  }
} finally {
  await browser.close();
}
