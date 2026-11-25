import { chromium } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import { resolve } from "node:path";

const origin = process.env.ASTER_BASE_URL || "http://127.0.0.1:8023";
const folder = resolve("docs/qa/evidence/screenshots");
await mkdir(folder, {recursive:true});
const browser = await chromium.launch({channel:process.env.ASTER_BROWSER || "msedge"});
try {
  for (const width of [320,390,768,1024,1280,1440]) {
    const context = await browser.newContext({viewport:{width,height:900}, reducedMotion:"reduce"});
    const page = await context.newPage();
    await page.goto(origin);
    await page.getByText("Dr Asha Menon").waitFor();
    const actual = await page.evaluate(()=>document.documentElement.scrollWidth);
    console.log(width, actual);
    if (actual !== width) throw Error("Horizontal overflow at "+width);
    if ([390,1440].includes(width)) {
      await page.screenshot({path:resolve(folder,width+".png")});
      await context.grantPermissions([]);
      await page.getByRole("button",{name:"Try call",exact:true}).click();
      await page.getByRole("alert").filter({hasText:/microphone|permission/i}).waitFor();
      await page.screenshot({path:resolve(folder,width+"-denied.png")});
    }
    await context.close();
  }
} finally {
  await browser.close();
}
