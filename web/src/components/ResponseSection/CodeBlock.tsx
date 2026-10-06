"use client";

import { useEffect, useState } from "react";
import { codeToHtml } from "shiki";

interface CodeBlockProps {
  className?: string;
  children?: React.ReactNode;
}

/**
 * Shiki syntax highlighting for react-markdown code blocks. Shiki v4's
 * codeToHtml is async, so this renders plain text first and swaps in
 * highlighted HTML once ready - streaming markdown means this runs
 * repeatedly as text arrives, which is fine at chat-message code-block
 * volume.
 */
export function CodeBlock({ className, children }: CodeBlockProps) {
  const language = /language-(\w+)/.exec(className ?? "")?.[1] ?? "text";
  const code = String(children ?? "").replace(/\n$/, "");
  const [html, setHtml] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    let cancelled = false;
    codeToHtml(code, { lang: language, theme: "github-light" })
      .then((result) => {
        if (!cancelled) setHtml(result);
      })
      .catch(() => {
        // Unknown language or highlighter failure - fall back to plain text.
        if (!cancelled) setHtml(null);
      });
    return () => {
      cancelled = true;
    };
  }, [code, language]);

  async function handleCopy() {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  }

  const header = (
    <div className="flex items-center justify-between rounded-t border border-b-0 border-caramel bg-latte px-3 py-1 text-xs">
      <span data-testid="code-block-language-label" className="font-mono text-medium-roast">
        {language}
      </span>
      <button
        type="button"
        data-testid="code-block-copy-button"
        onClick={handleCopy}
        className="rounded px-1.5 py-0.5 text-medium-roast transition hover:bg-cream"
      >
        {copied ? "Copied" : "Copy"}
      </button>
    </div>
  );

  if (html !== null) {
    return (
      <div className="my-2 overflow-x-auto rounded border border-caramel text-sm [&_pre]:p-3">
        {header}
        <div dangerouslySetInnerHTML={{ __html: html }} />
      </div>
    );
  }

  return (
    <div className="my-2 overflow-x-auto rounded border border-caramel text-sm">
      {header}
      <pre className="rounded-b bg-cream p-3 font-mono text-sm">
        <code>{code}</code>
      </pre>
    </div>
  );
}
