import assert from "node:assert/strict";
import test from "node:test";
import { money, number } from "../src/lib/format";

test("exibe zero para números ausentes ou inválidos", () => {
  assert.equal(number(undefined), "0");
  assert.equal(number(Number.NaN), "0");
  assert.equal(money(undefined), money(0));
  assert.equal(money(Number.NaN), money(0));
});
