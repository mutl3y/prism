"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const node_test_1 = __importDefault(require("node:test"));
const strict_1 = __importDefault(require("node:assert/strict"));
const matcher_1 = require("../matcher");
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
(0, node_test_1.default)("matches supported Prism marker kinds", () => {
    const text = [
        "# prism~warning: caution",
        "# prism~deprecated: old setting",
        "# prism~note: helpful context",
        "# prism~task: Restart service | note: approved",
    ].join("\n");
    const blocks = (0, matcher_1.findPrismBlocks)(text, defaultOptions);
    strict_1.default.equal(blocks.length, 4);
    strict_1.default.deepEqual(blocks.map((block) => block.kind), ["warning", "deprecated", "note", "task"]);
});
(0, node_test_1.default)("respects the configured prefix", () => {
    const text = "# opsdoc~note: custom prefix";
    const blocks = (0, matcher_1.findPrismBlocks)(text, {
        ...defaultOptions,
        prefix: "opsdoc",
    });
    strict_1.default.equal(blocks.length, 1);
    strict_1.default.equal(blocks[0]?.kind, "note");
});
(0, node_test_1.default)("ignores inline or non-comment matches", () => {
    const text = [
        'message = "prism~note: not a real comment"',
        "value: prism~note: still not a comment",
        "# ordinary comment only",
    ].join("\n");
    strict_1.default.equal((0, matcher_1.findPrismBlocks)(text, defaultOptions).length, 0);
});
(0, node_test_1.default)("keeps styling after the leading hash only", () => {
    const text = "  # prism~note: highlighted text";
    const [block] = (0, matcher_1.findPrismBlocks)(text, defaultOptions);
    strict_1.default.ok(block);
    strict_1.default.deepEqual(block.contentRanges[0], {
        line: 0,
        startCharacter: 4,
        endCharacter: text.length,
    });
});
(0, node_test_1.default)("treats all contiguous hash comments after a Prism marker as one block", () => {
    const text = [
        "# prism~note: line one",
        "# line two",
        "#",
        "# line four",
        "value: true",
        "# prism~warning: next block",
    ].join("\n");
    const blocks = (0, matcher_1.findPrismBlocks)(text, defaultOptions);
    strict_1.default.equal(blocks.length, 2);
    strict_1.default.equal(blocks[0]?.startLine, 0);
    strict_1.default.equal(blocks[0]?.endLine, 3);
    strict_1.default.equal(blocks[1]?.startLine, 5);
    strict_1.default.equal(blocks[1]?.endLine, 5);
});
//# sourceMappingURL=matcher.test.js.map
