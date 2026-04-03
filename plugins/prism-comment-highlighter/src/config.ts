import * as vscode from "vscode";

import { DEFAULT_MARKER_KINDS } from "./matcher";
import {
	DEFAULT_KIND_FOREGROUNDS,
	type MarkerKindColorMap,
	type StyleMode,
} from "./styles";

export interface PrismCommentDocsConfig {
	enabled: boolean;
	markerPrefix: string;
	languageIds: string[];
	markerKinds: string[];
	styleMode: StyleMode;
	customColor: string;
	multicolorEnabled: boolean;
	multicolorColors: MarkerKindColorMap;
	foldingEnabled: boolean;
}

const DEFAULT_LANGUAGE_IDS = ["yaml", "ansible", "python", "shellscript"];
const CONFIG_SECTION = "prismCommentDocs";

function asStringArray(value: unknown, fallback: readonly string[]): string[] {
	if (!Array.isArray(value)) {
		return [...fallback];
	}

	const normalized = value
		.filter((entry): entry is string => typeof entry === "string")
		.map((entry) => entry.trim())
		.filter(
			(entry, index, entries) =>
				entry.length > 0 && entries.indexOf(entry) === index,
		);
	return normalized.length > 0 ? normalized : [...fallback];
}

function asStyleMode(value: unknown): StyleMode {
	if (
		value === "yellow" ||
		value === "amber" ||
		value === "faded" ||
		value === "custom"
	) {
		return value;
	}

	return "yellow";
}

function asTrimmedString(value: unknown, fallback: string): string {
	return typeof value === "string" && value.trim().length > 0
		? value.trim()
		: fallback;
}

function getMulticolorSettings(
	config: vscode.WorkspaceConfiguration,
): MarkerKindColorMap {
	return Object.fromEntries(
		Object.entries(DEFAULT_KIND_FOREGROUNDS).map(([kind, defaultColor]) => [
			kind,
			asTrimmedString(config.get(`multicolor.${kind}Color`), defaultColor),
		]),
	);
}

export function getExtensionConfig(): PrismCommentDocsConfig {
	const config = vscode.workspace.getConfiguration(CONFIG_SECTION);
	return {
		enabled: config.get<boolean>("enabled", true),
		markerPrefix: config.get<string>("markerPrefix", "prism").trim() || "prism",
		languageIds: asStringArray(config.get("languageIds"), DEFAULT_LANGUAGE_IDS),
		markerKinds: asStringArray(config.get("markerKinds"), DEFAULT_MARKER_KINDS),
		styleMode: asStyleMode(config.get("styleMode")),
		customColor:
			config.get<string>("customColor", "#ffd54f").trim() || "#ffd54f",
		multicolorEnabled: config.get<boolean>("multicolorEnabled", false),
		multicolorColors: getMulticolorSettings(config),
		foldingEnabled: config.get<boolean>("foldingEnabled", true),
	};
}
