import test from "node:test";
import assert from "node:assert/strict";

import { resolveMarkerKindPalette, resolveStylePalette } from "../styles";

test("resolves the yellow palette", () => {
  const palette = resolveStylePalette("yellow", "#ffd54f");
  assert.equal(palette.foregroundColor, "#ffd54f");
  assert.match(palette.backgroundColor ?? "", /rgba\(255, 213, 79, 0\.16\)/);
});

test("resolves the amber palette", () => {
  const palette = resolveStylePalette("amber", "#ffd54f");
  assert.equal(palette.foregroundColor, "#c88719");
  assert.ok(palette.backgroundColor);
});

test("resolves the faded palette", () => {
  const palette = resolveStylePalette("faded", "#ffd54f");
  assert.match(palette.foregroundColor, /^rgba\(/);
  assert.ok(palette.backgroundColor);
});

test("derives a background for valid custom colors", () => {
  const palette = resolveStylePalette("custom", "#112233");
  assert.equal(palette.foregroundColor, "#112233");
  assert.equal(palette.backgroundColor, "rgba(17, 34, 51, 0.14)");
});

test("falls back for invalid custom colors", () => {
  const palette = resolveStylePalette("custom", "not-a-color");
  assert.equal(palette.foregroundColor, "#ffd54f");
  assert.equal(palette.backgroundColor, undefined);
});

test("resolves a dedicated palette for known Prism marker kinds", () => {
  const fallbackPalette = resolveStylePalette("yellow", "#ffd54f");
  const palette = resolveMarkerKindPalette("warning", {}, fallbackPalette);
  assert.equal(palette.foregroundColor, "#ff8a65");
  assert.equal(palette.backgroundColor, "rgba(255, 138, 101, 0.14)");
});

test("prefers configured multicolor overrides for known Prism marker kinds", () => {
  const fallbackPalette = resolveStylePalette("yellow", "#ffd54f");
  const palette = resolveMarkerKindPalette("warning", { warning: "#123456" }, fallbackPalette);
  assert.equal(palette.foregroundColor, "#123456");
  assert.equal(palette.backgroundColor, "rgba(18, 52, 86, 0.14)");
});

test("falls back to default marker colors when an override is invalid", () => {
  const fallbackPalette = resolveStylePalette("yellow", "#ffd54f");
  const palette = resolveMarkerKindPalette("warning", { warning: "not-a-color" }, fallbackPalette);
  assert.equal(palette.foregroundColor, "#ff8a65");
  assert.equal(palette.backgroundColor, "rgba(255, 138, 101, 0.14)");
});

test("falls back to the active single-color palette for unknown marker kinds", () => {
  const fallbackPalette = resolveStylePalette("amber", "#ffd54f");
  const palette = resolveMarkerKindPalette("customKind", {}, fallbackPalette);
  assert.deepEqual(palette, fallbackPalette);
});
