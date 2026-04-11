"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const node_test_1 = __importDefault(require("node:test"));
const strict_1 = __importDefault(require("node:assert/strict"));
const styles_1 = require("../styles");
(0, node_test_1.default)("resolves the yellow palette", () => {
    const palette = (0, styles_1.resolveStylePalette)("yellow", "#ffd54f");
    strict_1.default.equal(palette.foregroundColor, "#ffd54f");
    strict_1.default.match(palette.backgroundColor ?? "", /rgba\(255, 213, 79, 0\.16\)/);
});
(0, node_test_1.default)("resolves the amber palette", () => {
    const palette = (0, styles_1.resolveStylePalette)("amber", "#ffd54f");
    strict_1.default.equal(palette.foregroundColor, "#c88719");
    strict_1.default.ok(palette.backgroundColor);
});
(0, node_test_1.default)("resolves the faded palette", () => {
    const palette = (0, styles_1.resolveStylePalette)("faded", "#ffd54f");
    strict_1.default.match(palette.foregroundColor, /^rgba\(/);
    strict_1.default.ok(palette.backgroundColor);
});
(0, node_test_1.default)("derives a background for valid custom colors", () => {
    const palette = (0, styles_1.resolveStylePalette)("custom", "#112233");
    strict_1.default.equal(palette.foregroundColor, "#112233");
    strict_1.default.equal(palette.backgroundColor, "rgba(17, 34, 51, 0.14)");
});
(0, node_test_1.default)("falls back for invalid custom colors", () => {
    const palette = (0, styles_1.resolveStylePalette)("custom", "not-a-color");
    strict_1.default.equal(palette.foregroundColor, "#ffd54f");
    strict_1.default.equal(palette.backgroundColor, undefined);
});
(0, node_test_1.default)("resolves a dedicated palette for known Prism marker kinds", () => {
    const fallbackPalette = (0, styles_1.resolveStylePalette)("yellow", "#ffd54f");
    const palette = (0, styles_1.resolveMarkerKindPalette)("warning", {}, fallbackPalette);
    strict_1.default.equal(palette.foregroundColor, "#ff8a65");
    strict_1.default.equal(palette.backgroundColor, "rgba(255, 138, 101, 0.14)");
});
(0, node_test_1.default)("prefers configured multicolor overrides for known Prism marker kinds", () => {
    const fallbackPalette = (0, styles_1.resolveStylePalette)("yellow", "#ffd54f");
    const palette = (0, styles_1.resolveMarkerKindPalette)("warning", { warning: "#123456" }, fallbackPalette);
    strict_1.default.equal(palette.foregroundColor, "#123456");
    strict_1.default.equal(palette.backgroundColor, "rgba(18, 52, 86, 0.14)");
});
(0, node_test_1.default)("falls back to default marker colors when an override is invalid", () => {
    const fallbackPalette = (0, styles_1.resolveStylePalette)("yellow", "#ffd54f");
    const palette = (0, styles_1.resolveMarkerKindPalette)("warning", { warning: "not-a-color" }, fallbackPalette);
    strict_1.default.equal(palette.foregroundColor, "#ff8a65");
    strict_1.default.equal(palette.backgroundColor, "rgba(255, 138, 101, 0.14)");
});
(0, node_test_1.default)("falls back to the active single-color palette for unknown marker kinds", () => {
    const fallbackPalette = (0, styles_1.resolveStylePalette)("amber", "#ffd54f");
    const palette = (0, styles_1.resolveMarkerKindPalette)("customKind", {}, fallbackPalette);
    strict_1.default.deepEqual(palette, fallbackPalette);
});
//# sourceMappingURL=styles.test.js.map
