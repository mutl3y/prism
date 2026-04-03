import test from "node:test";
import assert from "node:assert/strict";

import { findPrismBlocks } from "../matcher";

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

test("matches supported Prism marker kinds", () => {
  const text = [
    "# prism~warning: caution",
    "# prism~deprecated: old setting",
    "# prism~note: helpful context",
    "# prism~task: Restart service | note: approved",
  ].join("\n");

  const blocks = findPrismBlocks(text, defaultOptions);
  assert.equal(blocks.length, 4);
  assert.deepEqual(
    blocks.map((block) => block.kind),
    ["warning", "deprecated", "note", "task"],
  );
});

test("respects the configured prefix", () => {
  const text = "# opsdoc~note: custom prefix";

  const blocks = findPrismBlocks(text, {
    ...defaultOptions,
    prefix: "opsdoc",
  });

  assert.equal(blocks.length, 1);
  assert.equal(blocks[0]?.kind, "note");
});

test("ignores inline or non-comment matches", () => {
  const text = [
    'message = "prism~note: not a real comment"',
    "value: prism~note: still not a comment",
    "# ordinary comment only",
  ].join("\n");

  assert.equal(findPrismBlocks(text, defaultOptions).length, 0);
});

test("keeps styling after the leading hash only", () => {
  const text = "  # prism~note: highlighted text";
  const [block] = findPrismBlocks(text, defaultOptions);
  assert.ok(block);
  assert.deepEqual(block.contentRanges[0], {
    line: 0,
    startCharacter: 4,
    endCharacter: text.length,
  });
});

test("treats all contiguous hash comments after a Prism marker as one block", () => {
  const text = [
    "# prism~note: line one",
    "# line two",
    "#",
    "# line four",
    "value: true",
    "# prism~warning: next block",
  ].join("\n");

  const blocks = findPrismBlocks(text, defaultOptions);
  assert.equal(blocks.length, 2);
  assert.equal(blocks[0]?.startLine, 0);
  assert.equal(blocks[0]?.endLine, 3);
  assert.equal(blocks[1]?.startLine, 5);
  assert.equal(blocks[1]?.endLine, 5);
});
