import assert from "node:assert/strict";
import test from "node:test";
import { acceptReceipt, shift, time } from "../src/data.ts";

test("out-of-order and duplicated receipts cannot supersede a new revision", () => {
  const seen = new Map();
  for (const [revision, expected] of [[2,true],[1,false],[2,false],[3,true]]) {
    assert.equal(acceptReceipt(seen,{reference:"AS-FIXTURE", revision}), expected);
  }
  assert.equal(acceptReceipt(seen,{reference:"AS-OTHER", revision:1}),true);
  assert.equal(acceptReceipt(new Map(),{reference:"AS-FIXTURE", revision:1}),true);
});

test("the desk displays midnight and noon in clinic time", () => {
  assert.equal(time("2028-02-28T18:30:00Z"),"00:00");
  assert.equal(time("2028-02-29T06:30:00Z"),"12:00");
  assert.equal(shift("2028-02-28",1),"2028-02-29");
  assert.equal(shift("2026-12-31",1),"2027-01-01");
});
