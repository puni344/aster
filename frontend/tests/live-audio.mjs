import { chromium } from "@playwright/test";
import path from "node:path";
const wav = process.argv[2];
if (!wav)
  throw Error("Pass a WAV file containing a fictional availability question.");
const browser = await chromium.launch({
  channel: "msedge",
  args: [
    "--use-fake-device-for-media-stream",
    "--use-file-for-fake-audio-capture=" + path.resolve(wav),
    "--autoplay-policy=no-user-gesture-required",
  ],
});
try {
  const ctx = await browser.newContext({ permissions: ["microphone"] });
  const page = await ctx.newPage();
  await page.goto(process.env.ASTER_BASE_URL || "http://127.0.0.1:8000");
  const started = performance.now();
  await page.getByRole("button", { name: "Try call", exact: true }).click();
  await page.waitForFunction(
    () => document.querySelector("audio")?.srcObject,
    {},
    { timeout: 30000 },
  );
  console.log("Click to remote track attached (ms):", Math.round(performance.now() - started));
  const audible = await page.evaluate(async () => {
    const audio = document.querySelector("audio");
    const ac = new AudioContext();
    await ac.resume();
    const node = ac.createMediaStreamSource(audio.srcObject),
      fft = ac.createAnalyser();
    node.connect(fft);
    const values = new Float32Array(fft.fftSize);
    let peak = 0;
    try {
      for (let i = 0; i < 180 && peak < 0.01; i++) {
        fft.getFloatTimeDomainData(values);
        for (const x of values) peak = Math.max(peak, Math.abs(x));
        await new Promise((r) => setTimeout(r, 50));
      }
    } finally {
      node.disconnect();
      await ac.close();
    }
    return peak;
  });
  console.log("Remote audio peak:", audible);
  await page
    .locator(".callerLine:not(.draft)")
    .first()
    .waitFor({ timeout: 35000 });
  console.log(
    "Committed caller transcript:",
    await page.locator(".callerLine:not(.draft)").first().innerText(),
  );
  await page
    .waitForFunction(
      () =>
        document.querySelectorAll(".agentLine:not(.draft)").length >= 2 ||
        document.querySelector(".callError"),
      {},
      { timeout: 25000 },
    )
    .catch(() => {});
  console.log(
    "Response:",
    await page.locator(".agentLine:not(.draft),.callError").last().innerText(),
  );
  const end = page.getByRole("button", { name: "End call" });
  if (await end.count()) await end.click();
  if (audible < 0.01 || await page.locator(".callError").count() || await page.locator(".agentLine:not(.draft)").count() < 2) process.exitCode = 1;
} finally {
  await browser.close();
}
