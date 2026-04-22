"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.getExtensionConfig = getExtensionConfig;
const vscode = __importStar(require("vscode"));
const matcher_1 = require("./matcher");
const styles_1 = require("./styles");
const DEFAULT_LANGUAGE_IDS = ["yaml", "ansible", "python", "shellscript"];
const CONFIG_SECTION = "prismCommentDocs";
function asStringArray(value, fallback) {
    if (!Array.isArray(value)) {
        return [...fallback];
    }
    const normalized = value
        .filter((entry) => typeof entry === "string")
        .map((entry) => entry.trim())
        .filter((entry, index, entries) => entry.length > 0 && entries.indexOf(entry) === index);
    return normalized.length > 0 ? normalized : [...fallback];
}
function asStyleMode(value) {
    if (value === "yellow" ||
        value === "amber" ||
        value === "faded" ||
        value === "custom") {
        return value;
    }
    return "yellow";
}
function asTrimmedString(value, fallback) {
    return typeof value === "string" && value.trim().length > 0
        ? value.trim()
        : fallback;
}
function getMulticolorSettings(config) {
    return Object.fromEntries(Object.entries(styles_1.DEFAULT_KIND_FOREGROUNDS).map(([kind, defaultColor]) => [
        kind,
        asTrimmedString(config.get(`multicolor.${kind}Color`), defaultColor),
    ]));
}
function getExtensionConfig() {
    const config = vscode.workspace.getConfiguration(CONFIG_SECTION);
    return {
        enabled: config.get("enabled", true),
        markerPrefix: config.get("markerPrefix", "prism").trim() || "prism",
        languageIds: asStringArray(config.get("languageIds"), DEFAULT_LANGUAGE_IDS),
        markerKinds: asStringArray(config.get("markerKinds"), matcher_1.DEFAULT_MARKER_KINDS),
        styleMode: asStyleMode(config.get("styleMode")),
        customColor: config.get("customColor", "#ffd54f").trim() || "#ffd54f",
        multicolorEnabled: config.get("multicolorEnabled", false),
        multicolorColors: getMulticolorSettings(config),
        foldingEnabled: config.get("foldingEnabled", true),
    };
}
//# sourceMappingURL=config.js.map
