export const DEFAULT_MARKER_KINDS = [
	"warning",
	"deprecated",
	"note",
	"notes",
	"additional",
	"additionals",
	"runbook",
	"task",
] as const;

export interface MatcherOptions {
	prefix: string;
	markerKinds: readonly string[];
}

export interface PrismContentRange {
	line: number;
	startCharacter: number;
	endCharacter: number;
}

export interface PrismBlock {
	startLine: number;
	endLine: number;
	kind: string;
	contentRanges: PrismContentRange[];
}

interface HashCommentLine {
	content: string;
	contentStart: number;
}

interface MarkerLine extends HashCommentLine {
	kind: string;
}

function escapeRegex(value: string): string {
	return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function normalizeMarkerKinds(markerKinds: readonly string[]): string[] {
	return markerKinds
		.map((kind) => kind.trim())
		.filter(
			(kind, index, kinds) => kind.length > 0 && kinds.indexOf(kind) === index,
		);
}

function parseHashCommentLine(lineText: string): HashCommentLine | null {
	const match = /^(\s*)#( ?)(.*)$/.exec(lineText);
	if (!match) {
		return null;
	}

	const indent = match[1] ?? "";
	const optionalSpace = match[2] ?? "";
	const content = match[3] ?? "";
	return {
		content,
		contentStart: indent.length + 1 + optionalSpace.length,
	};
}

function parseMarkerLine(
	lineText: string,
	options: MatcherOptions,
): MarkerLine | null {
	const comment = parseHashCommentLine(lineText);
	if (!comment) {
		return null;
	}

	const markerKinds = normalizeMarkerKinds(options.markerKinds);
	const prefix = options.prefix.trim();
	if (!prefix || markerKinds.length === 0) {
		return null;
	}

	const kindPattern = markerKinds.map(escapeRegex).join("|");
	const prefixPattern = escapeRegex(prefix);
	const markerRegex = new RegExp(
		`^${prefixPattern}~(${kindPattern})(?::|\\s|$)`,
	);
	const markerMatch = markerRegex.exec(comment.content);
	if (!markerMatch) {
		return null;
	}

	return {
		...comment,
		kind: markerMatch[1] ?? "",
	};
}

export function findPrismBlocks(
	text: string,
	options: MatcherOptions,
): PrismBlock[] {
	const lines = text.split(/\r?\n/);
	const blocks: PrismBlock[] = [];

	for (let lineNumber = 0; lineNumber < lines.length; lineNumber += 1) {
		const marker = parseMarkerLine(lines[lineNumber] ?? "", options);
		if (!marker) {
			continue;
		}

		const contentRanges: PrismContentRange[] = [];
		let endLine = lineNumber;

		for (let cursor = lineNumber; cursor < lines.length; cursor += 1) {
			if (cursor > lineNumber) {
				const nextMarker = parseMarkerLine(lines[cursor] ?? "", options);
				if (nextMarker) {
					break;
				}
			}

			const commentLine = parseHashCommentLine(lines[cursor] ?? "");
			if (!commentLine) {
				break;
			}

			contentRanges.push({
				line: cursor,
				startCharacter: commentLine.contentStart,
				endCharacter: (lines[cursor] ?? "").length,
			});
			endLine = cursor;
		}

		blocks.push({
			startLine: lineNumber,
			endLine,
			kind: marker.kind,
			contentRanges,
		});
		lineNumber = endLine;
	}

	return blocks;
}
