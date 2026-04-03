import * as vscode from "vscode";

import { getExtensionConfig, type PrismCommentDocsConfig } from "./config";
import { getFoldablePrismRanges, getFoldablePrismStartLines } from "./folding";
import { findPrismBlocks } from "./matcher";
import { resolveMarkerKindPalette, resolveStylePalette } from "./styles";

interface DecorationResources {
	defaultDecoration: vscode.TextEditorDecorationType;
	kindDecorations: Map<string, vscode.TextEditorDecorationType>;
}

function getEnabledUpdateTarget(): vscode.ConfigurationTarget {
	return vscode.workspace.workspaceFolders &&
		vscode.workspace.workspaceFolders.length > 0
		? vscode.ConfigurationTarget.Workspace
		: vscode.ConfigurationTarget.Global;
}

function isSupportedDocument(
	document: vscode.TextDocument,
	config: PrismCommentDocsConfig,
): boolean {
	return config.enabled && config.languageIds.includes(document.languageId);
}

function buildDecorationOptions(
	document: vscode.TextDocument,
	config: PrismCommentDocsConfig,
): vscode.DecorationOptions[] {
	return findPrismBlocks(document.getText(), {
		prefix: config.markerPrefix,
		markerKinds: config.markerKinds,
	}).flatMap((block) =>
		block.contentRanges
			.filter((range) => range.endCharacter > range.startCharacter)
			.map((range) => ({
				range: new vscode.Range(
					new vscode.Position(range.line, range.startCharacter),
					new vscode.Position(range.line, range.endCharacter),
				),
			})),
	);
}

function buildDecorationOptionsByKind(
	document: vscode.TextDocument,
	config: PrismCommentDocsConfig,
): Map<string, vscode.DecorationOptions[]> {
	const optionsByKind = new Map<string, vscode.DecorationOptions[]>();

	findPrismBlocks(document.getText(), {
		prefix: config.markerPrefix,
		markerKinds: config.markerKinds,
	}).forEach((block) => {
		const blockOptions = block.contentRanges
			.filter((range) => range.endCharacter > range.startCharacter)
			.map((range) => ({
				range: new vscode.Range(
					new vscode.Position(range.line, range.startCharacter),
					new vscode.Position(range.line, range.endCharacter),
				),
			}));

		if (blockOptions.length === 0) {
			return;
		}

		const existing = optionsByKind.get(block.kind) ?? [];
		existing.push(...blockOptions);
		optionsByKind.set(block.kind, existing);
	});

	return optionsByKind;
}

function createDecorationTypeFromPalette(
	palette: ReturnType<typeof resolveStylePalette>,
): vscode.TextEditorDecorationType {
	return vscode.window.createTextEditorDecorationType({
		color: palette.foregroundColor,
		backgroundColor: palette.backgroundColor,
		rangeBehavior: vscode.DecorationRangeBehavior.ClosedClosed,
	});
}

function createDecorationResources(
	config: PrismCommentDocsConfig,
): DecorationResources {
	const fallbackPalette = resolveStylePalette(
		config.styleMode,
		config.customColor,
	);
	const kindDecorations = new Map<string, vscode.TextEditorDecorationType>();

	if (config.multicolorEnabled) {
		const uniqueKinds = [...new Set(config.markerKinds)];
		uniqueKinds.forEach((kind) => {
			kindDecorations.set(
				kind,
				createDecorationTypeFromPalette(
					resolveMarkerKindPalette(
						kind,
						config.multicolorColors,
						fallbackPalette,
					),
				),
			);
		});
	}

	return {
		defaultDecoration: createDecorationTypeFromPalette(fallbackPalette),
		kindDecorations,
	};
}

function clearDecorations(
	editor: vscode.TextEditor,
	decorations: DecorationResources,
): void {
	editor.setDecorations(decorations.defaultDecoration, []);
	decorations.kindDecorations.forEach((decorationType) => {
		editor.setDecorations(decorationType, []);
	});
}

function disposeDecorationResources(decorations: DecorationResources): void {
	decorations.defaultDecoration.dispose();
	decorations.kindDecorations.forEach((decorationType) => {
		decorationType.dispose();
	});
}

export function activate(context: vscode.ExtensionContext): void {
	let config = getExtensionConfig();
	let decorations = createDecorationResources(config);
	let foldingRegistration: vscode.Disposable | undefined;
	const settingsQuery = "@ext:Prism.prism-comment-highlighter prismCommentDocs";

	const refreshEditor = (editor: vscode.TextEditor | undefined): void => {
		if (!editor) {
			return;
		}

		if (!isSupportedDocument(editor.document, config)) {
			clearDecorations(editor, decorations);
			return;
		}

		if (!config.multicolorEnabled) {
			editor.setDecorations(
				decorations.defaultDecoration,
				buildDecorationOptions(editor.document, config),
			);
			decorations.kindDecorations.forEach((decorationType) => {
				editor.setDecorations(decorationType, []);
			});
			return;
		}

		editor.setDecorations(decorations.defaultDecoration, []);
		const optionsByKind = buildDecorationOptionsByKind(editor.document, config);
		decorations.kindDecorations.forEach((decorationType, kind) => {
			editor.setDecorations(decorationType, optionsByKind.get(kind) ?? []);
		});
	};

	const refreshVisibleEditors = (): void => {
		vscode.window.visibleTextEditors.forEach((editor) => {
			refreshEditor(editor);
		});
	};

	const registerFoldingProvider = (): void => {
		foldingRegistration?.dispose();
		foldingRegistration = undefined;

		if (
			!config.enabled ||
			!config.foldingEnabled ||
			config.languageIds.length === 0
		) {
			return;
		}

		foldingRegistration = vscode.languages.registerFoldingRangeProvider(
			config.languageIds.map((language) => ({ language })),
			{
				provideFoldingRanges(
					document: vscode.TextDocument,
				): vscode.FoldingRange[] {
					const currentConfig = getExtensionConfig();
					if (
						!isSupportedDocument(document, currentConfig) ||
						!currentConfig.foldingEnabled
					) {
						return [];
					}

					return getFoldablePrismRanges(document.getText(), {
						prefix: currentConfig.markerPrefix,
						markerKinds: currentConfig.markerKinds,
					}).map(
						(range) =>
							new vscode.FoldingRange(
								range.startLine,
								range.endLine,
								vscode.FoldingRangeKind.Comment,
							),
					);
				},
			},
		);
	};

	const rebuildResources = (): void => {
		disposeDecorationResources(decorations);
		config = getExtensionConfig();
		decorations = createDecorationResources(config);
		registerFoldingProvider();
		refreshVisibleEditors();
	};

	const runFoldCommand = async (
		commandId: "editor.fold" | "editor.unfold",
	): Promise<void> => {
		const editor = vscode.window.activeTextEditor;
		if (
			!editor ||
			!isSupportedDocument(editor.document, config) ||
			!config.foldingEnabled
		) {
			return;
		}

		const selectionLines = getFoldablePrismStartLines(
			editor.document.getText(),
			{
				prefix: config.markerPrefix,
				markerKinds: config.markerKinds,
			},
		);
		if (selectionLines.length === 0) {
			return;
		}

		await vscode.commands.executeCommand(commandId, {
			selectionLines,
		});
	};

	context.subscriptions.push(
		vscode.commands.registerCommand(
			"prismCommentDocs.toggleEnabled",
			async () => {
				const nextEnabled = !config.enabled;
				await vscode.workspace
					.getConfiguration("prismCommentDocs")
					.update("enabled", nextEnabled, getEnabledUpdateTarget());
				vscode.window.setStatusBarMessage(
					`Prism Comment Docs ${nextEnabled ? "enabled" : "disabled"}`,
					3000,
				);
			},
		),
		vscode.commands.registerCommand(
			"prismCommentDocs.openSettings",
			async () => {
				await vscode.commands.executeCommand(
					"workbench.action.openSettings",
					settingsQuery,
				);
			},
		),
		vscode.commands.registerCommand("prismCommentDocs.foldAll", async () => {
			await runFoldCommand("editor.fold");
		}),
		vscode.commands.registerCommand("prismCommentDocs.unfoldAll", async () => {
			await runFoldCommand("editor.unfold");
		}),
		vscode.window.onDidChangeActiveTextEditor((editor) =>
			refreshEditor(editor),
		),
		vscode.window.onDidChangeVisibleTextEditors(() => refreshVisibleEditors()),
		vscode.workspace.onDidOpenTextDocument(() => refreshVisibleEditors()),
		vscode.workspace.onDidChangeTextDocument((event) => {
			const matchingEditor = vscode.window.visibleTextEditors.find(
				(editor) =>
					editor.document.uri.toString() === event.document.uri.toString(),
			);
			refreshEditor(matchingEditor);
		}),
		vscode.workspace.onDidChangeConfiguration((event) => {
			if (event.affectsConfiguration("prismCommentDocs")) {
				rebuildResources();
			}
		}),
		{
			dispose: () => {
				foldingRegistration?.dispose();
				disposeDecorationResources(decorations);
			},
		},
	);

	registerFoldingProvider();
	refreshVisibleEditors();
}

export function deactivate(): void {}
