"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.DEFAULT_KIND_FOREGROUNDS = void 0;
exports.resolveStylePalette = resolveStylePalette;
exports.resolveMarkerKindPalette = resolveMarkerKindPalette;
const DEFAULT_CUSTOM_FOREGROUND = "#ffd54f";
exports.DEFAULT_KIND_FOREGROUNDS = {
    warning: "#ff8a65",
    deprecated: "#e57373",
    note: "#64b5f6",
    notes: "#64b5f6",
    additional: "#4db6ac",
    additionals: "#4db6ac",
    runbook: "#9575cd",
    task: "#ffd54f",
};
function clampChannel(value) {
    return Math.max(0, Math.min(255, Math.round(value)));
}
function parseHexColor(color) {
    const normalized = color.trim();
    if (/^#[0-9a-fA-F]{3}$/.test(normalized)) {
        const r = normalized[1] + normalized[1];
        const g = normalized[2] + normalized[2];
        const b = normalized[3] + normalized[3];
        return {
            r: parseInt(r, 16),
            g: parseInt(g, 16),
            b: parseInt(b, 16),
        };
    }
    if (/^#[0-9a-fA-F]{6}$/.test(normalized)) {
        return {
            r: parseInt(normalized.slice(1, 3), 16),
            g: parseInt(normalized.slice(3, 5), 16),
            b: parseInt(normalized.slice(5, 7), 16),
        };
    }
    return null;
}
function parseRgbColor(color) {
    const match = /^rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})(?:\s*,\s*(?:0|1|0?\.\d+))?\s*\)$/i.exec(color.trim());
    if (!match) {
        return null;
    }
    return {
        r: clampChannel(Number(match[1])),
        g: clampChannel(Number(match[2])),
        b: clampChannel(Number(match[3])),
    };
}
function parseColor(color) {
    return parseHexColor(color) ?? parseRgbColor(color);
}
function rgbaString(parsed, alpha) {
    return `rgba(${parsed.r}, ${parsed.g}, ${parsed.b}, ${alpha})`;
}
function paletteFromForegroundColor(foregroundColor, backgroundAlpha) {
    const parsed = parseColor(foregroundColor);
    if (!parsed) {
        return {
            foregroundColor,
        };
    }
    return {
        foregroundColor,
        backgroundColor: rgbaString(parsed, backgroundAlpha),
    };
}
function resolveStylePalette(styleMode, customColor) {
    if (styleMode === "yellow") {
        return paletteFromForegroundColor("#ffd54f", 0.16);
    }
    if (styleMode === "amber") {
        return paletteFromForegroundColor("#c88719", 0.14);
    }
    if (styleMode === "faded") {
        return {
            foregroundColor: "rgba(150, 140, 92, 0.55)",
            backgroundColor: "rgba(255, 213, 79, 0.03)",
        };
    }
    const parsed = parseColor(customColor);
    if (!parsed) {
        return {
            foregroundColor: DEFAULT_CUSTOM_FOREGROUND,
        };
    }
    return {
        foregroundColor: customColor.trim(),
        backgroundColor: rgbaString(parsed, 0.14),
    };
}
function resolveMarkerKindPalette(kind, markerKindColors, fallbackPalette) {
    const normalizedKind = kind.trim().toLowerCase();
    const configuredColor = markerKindColors[normalizedKind]?.trim();
    if (configuredColor && parseColor(configuredColor)) {
        return paletteFromForegroundColor(configuredColor, 0.14);
    }
    const defaultForegroundColor = exports.DEFAULT_KIND_FOREGROUNDS[normalizedKind];
    if (!defaultForegroundColor) {
        return fallbackPalette;
    }
    return paletteFromForegroundColor(defaultForegroundColor, 0.14);
}
//# sourceMappingURL=styles.js.map
