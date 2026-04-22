"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const node_test_1 = __importDefault(require("node:test"));
const strict_1 = __importDefault(require("node:assert/strict"));
const folding_1 = require("../folding");
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
(0, node_test_1.default)("returns fold ranges only for multiline Prism blocks", () => {
    const text = [
        "# prism~note: line one",
        "# line two",
        "value: true",
        "# prism~warning: single line",
    ].join("\n");
    strict_1.default.deepEqual((0, folding_1.getFoldablePrismRanges)(text, defaultOptions), [
        { startLine: 0, endLine: 1 },
    ]);
});
(0, node_test_1.default)("returns fold start lines for Prism-only folding commands", () => {
    const text = [
        "# prism~task: first block",
        "# continuation",
        "value: true",
        "# ordinary comment",
        "# prism~runbook: second block",
        "# continuation",
    ].join("\n");
    strict_1.default.deepEqual((0, folding_1.getFoldablePrismStartLines)(text, defaultOptions), [0, 4]);
});
//# sourceMappingURL=folding.test.js.map
