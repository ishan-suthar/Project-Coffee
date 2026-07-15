#!/usr/bin/env node
/**
 * Brew 42 (docs/design/learning-loop-and-release-design.md Section 4.1,
 * Question 5): a one-shot bundle size report. This Next.js version's
 * Turbopack build no longer prints a per-route First Load JS table the
 * way older Next.js builds did (confirmed by running `npx next build`
 * directly), so this fills that gap.
 *
 * Report-only, no budget/threshold, no build-failing exit code - unlike
 * checkAssetBudget.mjs, there is no agreed total-JS budget yet (Brew 42
 * is asked to record a number, not enforce one).
 *
 * Reports two numbers, since they answer different questions:
 *   1. "Always-shipped baseline" - build-manifest.json's rootMainFiles +
 *      polyfillFiles: the JS every page load pulls in regardless of
 *      route, the closest available proxy to older Next.js's First
 *      Load JS now that App Router's real per-route RSC chunk mapping
 *      isn't exposed in a simple static manifest.
 *   2. "Full chunk directory" - every file under .next/static/chunks/,
 *      which is NOT what any single page load ships (Turbopack splits
 *      aggressively across every route/dynamic import) - reported for
 *      completeness, explicitly labeled so it is never mistaken for a
 *      real page-weight number.
 *
 * Run after `npx next build`:
 *   node scripts/reportBundleSize.mjs
 */
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const NEXT_ROOT = fileURLToPath(new URL("../.next", import.meta.url));
const CHUNKS_ROOT = join(NEXT_ROOT, "static", "chunks");

function collectJsFiles(dir) {
  const files = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) {
      files.push(...collectJsFiles(path));
    } else if (entry.name.endsWith(".js")) {
      files.push(path);
    }
  }
  return files;
}

function fileSizeBytes(relativePath) {
  try {
    return statSync(join(NEXT_ROOT, relativePath)).size;
  } catch {
    return 0;
  }
}

let manifest;
try {
  manifest = JSON.parse(readFileSync(join(NEXT_ROOT, "build-manifest.json"), "utf-8"));
} catch (err) {
  if (err.code === "ENOENT") {
    console.error("No .next/build-manifest.json found - run `npx next build` first.");
    process.exit(1);
  }
  throw err;
}

const baselineFiles = [...(manifest.rootMainFiles ?? []), ...(manifest.polyfillFiles ?? [])];
const baselineBytes = baselineFiles.reduce((sum, path) => sum + fileSizeBytes(path), 0);

console.log(`Always-shipped baseline (rootMainFiles + polyfillFiles, ${baselineFiles.length} file(s)):`);
for (const path of baselineFiles) {
  console.log(`  ${(fileSizeBytes(path) / 1024).toFixed(1).padStart(8)} KB  ${path}`);
}
console.log(`  Baseline total: ${(baselineBytes / 1024).toFixed(1)} KB\n`);

let chunkFiles;
try {
  chunkFiles = collectJsFiles(CHUNKS_ROOT);
} catch (err) {
  if (err.code === "ENOENT") {
    console.error("No .next/static/chunks directory found - run `npx next build` first.");
    process.exit(1);
  }
  throw err;
}
const chunkTotalBytes = chunkFiles.reduce((sum, path) => sum + statSync(path).size, 0);
console.log(
  `Full .next/static/chunks/ directory (${chunkFiles.length} file(s), NOT what any single ` +
    `page load ships - Turbopack splits per route/dynamic-import): ` +
    `${(chunkTotalBytes / 1024).toFixed(1)} KB`
);
