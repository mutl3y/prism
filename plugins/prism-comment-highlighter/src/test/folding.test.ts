import test from "node:test";
import assert from "node:assert/strict";

import { getFoldablePrismRanges, getFoldablePrismStartLines } from "../folding";

const defaultOptions = {
  prefix: "prism",
  markerKinds: [
    "warning",
    "deprecated",
    "note",
    "notes",
    "additional",
    "additionals",
    "runbook",
    "task",
  ],
};

test("returns fold ranges only for multiline Prism blocks", () => {
  const text = [
    "# prism~note: line one",
    "# line two",
    "value: true",
    "# prism~warning: single line",
  ].join("\n");

  assert.deepEqual(getFoldablePrismRanges(text, defaultOptions), [
    { startLine: 0, endLine: 1 },
  ]);
});

test("returns fold start lines for Prism-only folding commands", () => {
  const text = [
    "# prism~task: first block",
    "# continuation",
    "value: true",
    "# ordinary comment",
    "# prism~runbook: second block",
    "# continuation",
  ].join("\n");

  assert.deepEqual(getFoldablePrismStartLines(text, defaultOptions), [0, 4]);
});
