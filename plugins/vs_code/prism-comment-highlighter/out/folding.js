"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.getFoldablePrismRanges = getFoldablePrismRanges;
exports.getFoldablePrismStartLines = getFoldablePrismStartLines;
const matcher_1 = require("./matcher");
function getFoldablePrismRanges(text, options) {
    return (0, matcher_1.findPrismBlocks)(text, options)
        .filter((block) => block.endLine > block.startLine)
        .map((block) => ({
        startLine: block.startLine,
        endLine: block.endLine,
    }));
}
function getFoldablePrismStartLines(text, options) {
    return getFoldablePrismRanges(text, options).map((range) => range.startLine);
}
//# sourceMappingURL=folding.js.map
