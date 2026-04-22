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
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const config_1 = require("./config");
const folding_1 = require("./folding");
const matcher_1 = require("./matcher");
const styles_1 = require("./styles");
function getEnabledUpdateTarget() {
    return vscode.workspace.workspaceFolders &&
        vscode.workspace.workspaceFolders.length > 0
        ? vscode.ConfigurationTarget.Workspace
        : vscode.ConfigurationTarget.Global;
}
function isSupportedDocument(document, config) {
    return config.enabled && config.languageIds.includes(document.languageId);
}
function buildDecorationOptions(document, config) {
    return (0, matcher_1.findPrismBlocks)(document.getText(), {
        prefix: config.markerPrefix,
        markerKinds: config.markerKinds,
    }).flatMap((block) => block.contentRanges
        .filter((range) => range.endCharacter > range.startCharacter)
        .map((range) => ({
        range: new vscode.Range(new vscode.Position(range.line, range.startCharacter), new vscode.Position(range.line, range.endCharacter)),
    })));
}
function buildDecorationOptionsByKind(document, config) {
    const optionsByKind = new Map();
    (0, matcher_1.findPrismBlocks)(document.getText(), {
        prefix: config.markerPrefix,
        markerKinds: config.markerKinds,
    }).forEach((block) => {
        const blockOptions = block.contentRanges
            .filter((range) => range.endCharacter > range.startCharacter)
            .map((range) => ({
            range: new vscode.Range(new vscode.Position(range.line, range.startCharacter), new vscode.Position(range.line, range.endCharacter)),
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
function createDecorationTypeFromPalette(palette) {
    return vscode.window.createTextEditorDecorationType({
        color: palette.foregroundColor,
        backgroundColor: palette.backgroundColor,
        rangeBehavior: vscode.DecorationRangeBehavior.ClosedClosed,
    });
}
function createDecorationResources(config) {
    const fallbackPalette = (0, styles_1.resolveStylePalette)(config.styleMode, config.customColor);
    const kindDecorations = new Map();
    if (config.multicolorEnabled) {
        const uniqueKinds = [...new Set(config.markerKinds)];
        uniqueKinds.forEach((kind) => {
            kindDecorations.set(kind, createDecorationTypeFromPalette((0, styles_1.resolveMarkerKindPalette)(kind, config.multicolorColors, fallbackPalette)));
        });
    }
    return {
        defaultDecoration: createDecorationTypeFromPalette(fallbackPalette),
        kindDecorations,
    };
}
function clearDecorations(editor, decorations) {
    editor.setDecorations(decorations.defaultDecoration, []);
    decorations.kindDecorations.forEach((decorationType) => {
        editor.setDecorations(decorationType, []);
    });
}
function disposeDecorationResources(decorations) {
    decorations.defaultDecoration.dispose();
    decorations.kindDecorations.forEach((decorationType) => {
        decorationType.dispose();
    });
}
function activate(context) {
    let config = (0, config_1.getExtensionConfig)();
    let decorations = createDecorationResources(config);
    let foldingRegistration;
    const settingsQuery = "@ext:Prism.prism-comment-highlighter prismCommentDocs";
    const refreshEditor = (editor) => {
        if (!editor) {
            return;
        }
        if (!isSupportedDocument(editor.document, config)) {
            clearDecorations(editor, decorations);
            return;
        }
        if (!config.multicolorEnabled) {
            editor.setDecorations(decorations.defaultDecoration, buildDecorationOptions(editor.document, config));
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
    const refreshVisibleEditors = () => {
        vscode.window.visibleTextEditors.forEach((editor) => {
            refreshEditor(editor);
        });
    };
    const registerFoldingProvider = () => {
        foldingRegistration?.dispose();
        foldingRegistration = undefined;
        if (!config.enabled ||
            !config.foldingEnabled ||
            config.languageIds.length === 0) {
            return;
        }
        foldingRegistration = vscode.languages.registerFoldingRangeProvider(config.languageIds.map((language) => ({ language })), {
            provideFoldingRanges(document) {
                const currentConfig = (0, config_1.getExtensionConfig)();
                if (!isSupportedDocument(document, currentConfig) ||
                    !currentConfig.foldingEnabled) {
                    return [];
                }
                return (0, folding_1.getFoldablePrismRanges)(document.getText(), {
                    prefix: currentConfig.markerPrefix,
                    markerKinds: currentConfig.markerKinds,
                }).map((range) => new vscode.FoldingRange(range.startLine, range.endLine, vscode.FoldingRangeKind.Comment));
            },
        });
    };
    const rebuildResources = () => {
        disposeDecorationResources(decorations);
        config = (0, config_1.getExtensionConfig)();
        decorations = createDecorationResources(config);
        registerFoldingProvider();
        refreshVisibleEditors();
    };
    const runFoldCommand = async (commandId) => {
        const editor = vscode.window.activeTextEditor;
        if (!editor ||
            !isSupportedDocument(editor.document, config) ||
            !config.foldingEnabled) {
            return;
        }
        const selectionLines = (0, folding_1.getFoldablePrismStartLines)(editor.document.getText(), {
            prefix: config.markerPrefix,
            markerKinds: config.markerKinds,
        });
        if (selectionLines.length === 0) {
            return;
        }
        await vscode.commands.executeCommand(commandId, {
            selectionLines,
        });
    };
    context.subscriptions.push(vscode.commands.registerCommand("prismCommentDocs.toggleEnabled", async () => {
        const nextEnabled = !config.enabled;
        await vscode.workspace
            .getConfiguration("prismCommentDocs")
            .update("enabled", nextEnabled, getEnabledUpdateTarget());
        vscode.window.setStatusBarMessage(`Prism Comment Docs ${nextEnabled ? "enabled" : "disabled"}`, 3000);
    }), vscode.commands.registerCommand("prismCommentDocs.openSettings", async () => {
        await vscode.commands.executeCommand("workbench.action.openSettings", settingsQuery);
    }), vscode.commands.registerCommand("prismCommentDocs.foldAll", async () => {
        await runFoldCommand("editor.fold");
    }), vscode.commands.registerCommand("prismCommentDocs.unfoldAll", async () => {
        await runFoldCommand("editor.unfold");
    }), vscode.window.onDidChangeActiveTextEditor((editor) => refreshEditor(editor)), vscode.window.onDidChangeVisibleTextEditors(() => refreshVisibleEditors()), vscode.workspace.onDidOpenTextDocument(() => refreshVisibleEditors()), vscode.workspace.onDidChangeTextDocument((event) => {
        const matchingEditor = vscode.window.visibleTextEditors.find((editor) => editor.document.uri.toString() === event.document.uri.toString());
        refreshEditor(matchingEditor);
    }), vscode.workspace.onDidChangeConfiguration((event) => {
        if (event.affectsConfiguration("prismCommentDocs")) {
            rebuildResources();
        }
    }), {
        dispose: () => {
            foldingRegistration?.dispose();
            disposeDecorationResources(decorations);
        },
    });
    registerFoldingProvider();
    refreshVisibleEditors();
}
function deactivate() { }
//# sourceMappingURL=extension.js.map
