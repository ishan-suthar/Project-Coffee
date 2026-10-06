#!/usr/bin/env node
/**
 * Build-time check for Requirement 6 (docs/design/counter-scene-design.md
 * Section 7): the animated Coffee Counter scene's total asset footprint
 * must stay under 300 KB. Sums real file sizes under public/assets/
 * (counter/icons/branding) and fails the build if the total exceeds the
 * budget - run automatically via the "prebuild"/"pretest" npm scripts,
 * not a manual step someone has to remember.
 */
import { readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const BUDGET_BYTES = 300 * 1024;
const ASSET_ROOT = fileURLToPath(new URL("../public/assets", import.meta.url));

function totalSizeOf(dir) {
  let total = 0;
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) {
      total += totalSizeOf(path);
    } else {
      total += statSync(path).size;
    }
  }
  return total;
}

const totalBytes = totalSizeOf(ASSET_ROOT);
const totalKb = (totalBytes / 1024).toFixed(1);
const budgetKb = (BUDGET_BYTES / 1024).toFixed(0);

if (totalBytes > BUDGET_BYTES) {
  console.error(
    `Coffee Counter scene assets are ${totalKb} KB, exceeding the ${budgetKb} KB budget (public/assets/). ` +
      "Trim or re-encode an asset before building - see public/assets/counter/README.md."
  );
  process.exit(1);
}

console.log(`Coffee Counter scene assets: ${totalKb} KB / ${budgetKb} KB budget.`);
