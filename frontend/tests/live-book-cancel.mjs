/* Opt-in live browser evaluation. Only caller microphone input is synthetic. */
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { chromium } from "@playwright/test";

const origin = process.env.ASTER_LIVE_DESK || "http://127.0.0.1:8024";
assert.equal(new URL(origin).hostname, "127.0.0.1");
const clips = {};
for (const name of ["book","time","phone","yes","cancel"])
  clips[name] = (await readFile(".tools/qa-caller/"+name+".wav")).toString("base64");
const browser = await chromium.launch({channel:"msedge",args:["--use-fake-device-for-media-stream","--autoplay-policy=no-user-gesture-required"]});
let outcome = "No committed booking observed";
try {
  const context = await browser.newContext({permissions:["microphone"]});
  await context.addInitScript(() => {
    const original = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
    navigator.mediaDevices.getUserMedia = async (constraints) => {
      if (!constraints.audio) return original(constraints);
      const ac = window.callerAudio ??= new AudioContext();
      const dest = window.callerDestination ??= ac.createMediaStreamDestination();
      if (!window.silenceClock) {
        const silence = ac.createConstantSource();
        silence.offset.value = 0;
        silence.connect(dest);
        silence.start();
        window.silenceClock = silence;
      }
      await ac.resume();
      return dest.stream.clone();
    };
    window.sayFixture = async (encoded) => {
      const data = Uint8Array.from(atob(encoded), s => s.charCodeAt(0));
      const ac = window.callerAudio;
      const clip = ac.createBufferSource();
      clip.buffer = await ac.decodeAudioData(data.buffer);
      clip.connect(window.callerDestination);
      await new Promise(done => {clip.onended = done;clip.start();});
      clip.disconnect();
    };
  });
  const page = await context.newPage();
  await page.goto(origin);
  const snapshot = await (await context.request.get(origin+"/api/dashboard")).json();
  assert.equal(snapshot.appointments.length,0,"Use an empty fictional database for this probe");
  await page.getByRole("button",{name:"Try call",exact:true}).click();
  let oldCount=0, sentCancel=false, previousText="", repeats=0;
  const started=Date.now();
  for (let turn=0; turn<9 && Date.now()-started<150000; turn++) {
    await page.waitForFunction(n=>document.querySelector(".callError") || document.querySelectorAll(".agentLine:not(.draft)").length>n, oldCount, {timeout:35000});
    if (await page.locator(".callError").count()) throw Error(await page.locator(".callError").innerText());
    const lines=page.locator(".agentLine:not(.draft)");
    oldCount=await lines.count();
    const text=await lines.last().innerText();
    console.log("Assistant turn",turn+1,text);
    console.log("Latest caller transcript:",await page.locator(".callerLine:not(.draft)").last().textContent({timeout:300}).catch(()=>""));
    repeats=text===previousText?repeats+1:0;
    previousText=text;
    if (repeats>=2) throw Error("Assistant repeated the same prompt three times");
    const receipt=await page.locator(".receipt").allInnerTexts();
    if (receipt.length) console.log("Receipt:",receipt[0]);
    if (receipt.some(r=>r.includes("Cancelled"))) {outcome="Live cancellation observed";break;}
    let action;
    if (turn===0) action="book";
    else if (receipt.some(r=>r.includes("Confirmed")) && !sentCancel) {
      assert.match(receipt[0],/Asha Menon/);
      assert.match(receipt[0],/09:00/);
      outcome="Live booking observed"; action="cancel";sentCancel=true;
    } else if (/\d(?:[\s,-]*\d){9}/.test(text)) {
      action=text.replace(/\D/g,"")==="9876543210"?"yes":"phone";
    } else if (/should i (?:book|cancel)|shall i (?:book|cancel)|would you like me to (?:book|cancel)/i.test(text)) {
      assert.match(text,/Asha Menon/i);
      assert.match(text,/09:00|9[: ]?00|nine/i);
      action="yes";
    }
    else if (/phone|mobile|number/i.test(text)) action="phone";
    else if (/time|nine|9:00|available|slots/i.test(text)) action="time";
    else throw Error("Cannot select a truthful caller reply to this assistant turn");
    console.log("Synthetic caller clip:",action);
    await page.evaluate(encoded=>window.sayFixture(encoded), clips[action]);
  }
  assert.equal(outcome,"Live cancellation observed");
} finally {
  console.log("Observed outcome:",outcome);
  await browser.close();
}
