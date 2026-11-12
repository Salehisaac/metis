// Copy pinned browser libraries from node_modules into site/vendor (the site has no build step).
// Run after `npm install`: npm run vendor
import { cpSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";

const NM = new URL("../node_modules/", import.meta.url);
const OUT = new URL("../site/vendor/", import.meta.url);
const LANGS = ["python", "sql", "go", "bash", "json", "plaintext"];

const files = [
  ["marked/lib/marked.esm.js", "marked.esm.js"],
  ["marked/LICENSE", "LICENSE.marked"],
  ["dompurify/dist/purify.es.mjs", "purify.es.mjs"],
  ["dompurify/LICENSE", "LICENSE.dompurify"],
  ["@highlightjs/cdn-assets/es/core.min.js", "highlight/core.min.js"],
  ["@highlightjs/cdn-assets/LICENSE", "LICENSE.highlightjs"],
  ...LANGS.map((l) => [`@highlightjs/cdn-assets/es/languages/${l}.min.js`, `highlight/languages/${l}.min.js`]),
  // Barlow / Barlow Condensed (SIL OFL 1.1), latin subset only: the UI's type (Transit theme)
  ...["400", "500", "600"].map((w) => [`@fontsource/barlow/files/barlow-latin-${w}-normal.woff2`, `fonts/barlow-${w}.woff2`]),
  ...["600", "700"].map((w) => [`@fontsource/barlow-condensed/files/barlow-condensed-latin-${w}-normal.woff2`, `fonts/barlow-condensed-${w}.woff2`]),
  ["@fontsource/barlow/LICENSE", "fonts/LICENSE.barlow"],
];

mkdirSync(new URL("highlight/languages/", OUT), { recursive: true });
mkdirSync(new URL("fonts/", OUT), { recursive: true });
for (const [from, to] of files) cpSync(new URL(from, NM), new URL(to, OUT));

const versions = Object.fromEntries(["marked", "dompurify", "@highlightjs/cdn-assets", "@fontsource/barlow", "@fontsource/barlow-condensed"].map((p) =>
  [p, JSON.parse(readFileSync(new URL(`${p}/package.json`, NM))).version]));
writeFileSync(new URL("VERSIONS.json", OUT), JSON.stringify({ versions, languages: LANGS }, null, 2) + "\n");
console.log("vendored", versions);
