import { findPrismBlocks, type MatcherOptions } from "./matcher";

export interface FoldablePrismRange {
  startLine: number;
  endLine: number;
}

export function getFoldablePrismRanges(
  text: string,
  options: MatcherOptions,
): FoldablePrismRange[] {
  return findPrismBlocks(text, options)
    .filter((block) => block.endLine > block.startLine)
    .map((block) => ({
      startLine: block.startLine,
      endLine: block.endLine,
    }));
}

export function getFoldablePrismStartLines(
  text: string,
  options: MatcherOptions,
): number[] {
  return getFoldablePrismRanges(text, options).map((range) => range.startLine);
}
