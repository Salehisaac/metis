// Markdown -> sanitized DocumentFragment. Pipeline: marked.lexer -> swap quiz/exercise fences for
// placeholders -> marked.parser -> DOMPurify (RETURN_DOM_FRAGMENT, so no innerHTML here) -> mount blocks -> highlight.
import { marked } from "../../vendor/marked.esm.js";
import DOMPurify from "../../vendor/purify.es.mjs";
import hljs from "../../vendor/highlight/core.min.js";
import python from "../../vendor/highlight/languages/python.min.js";
import sql from "../../vendor/highlight/languages/sql.min.js";
import go from "../../vendor/highlight/languages/go.min.js";
import bash from "../../vendor/highlight/languages/bash.min.js";
import json from "../../vendor/highlight/languages/json.min.js";
import plaintext from "../../vendor/highlight/languages/plaintext.min.js";

for (const [name, lang] of Object.entries({ python, sql, go, bash, json, plaintext })) hljs.registerLanguage(name, lang);
hljs.registerAliases(["py"], { languageName: "python" });
hljs.registerAliases(["sh", "shell", "console"], { languageName: "bash" });

const BLOCK_KINDS = new Set(["quiz", "exercise"]);

// Only registered languages are highlighted; anything else stays plain text (no console warnings).
export function highlight(codeEl) {
  const lang = [...codeEl.classList].find((c) => c.startsWith("language-"))?.slice(9);
  if (lang && hljs.getLanguage(lang)) hljs.highlightElement(codeEl);
}

// mountBlock({kind, raw}) -> Node. Blocks are found by a per-render nonce so Markdown authors
// can't forge placeholders with their own data attributes.
export function renderMarkdown(text, mountBlock) {
  const nonce = Math.random().toString(36).slice(2);
  const tokens = marked.lexer(text);
  const blocks = [];
  tokens.forEach((t, i) => {
    if (t.type === "code" && BLOCK_KINDS.has(t.lang)) {
      blocks.push({ kind: t.lang, raw: t.text });
      tokens[i] = { type: "html", raw: t.raw, pre: false, block: true, text: `<div data-block="${nonce}-${blocks.length - 1}"></div>\n` };
    }
  });
  const frag = DOMPurify.sanitize(marked.parser(tokens), { RETURN_DOM_FRAGMENT: true });
  frag.querySelectorAll("pre code").forEach(highlight); // before mounting: blocks highlight their own code
  for (const el of frag.querySelectorAll("[data-block]")) {
    const [n, i] = el.getAttribute("data-block").split("-");
    if (n === nonce && blocks[i]) el.replaceWith(mountBlock(blocks[i]));
    else el.remove();
  }
  return frag;
}
