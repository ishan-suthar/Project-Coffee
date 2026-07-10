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

  if (html !== null) {
    return (
      <div
        className="overflow-x-auto rounded border border-caramel text-sm [&_pre]:p-3"
        dangerouslySetInnerHTML={{ __html: html }}
      />
    );
  }

  return (
    <pre className="overflow-x-auto rounded border border-caramel bg-cream p-3 font-mono text-sm">
      <code>{code}</code>
    </pre>
  );
}
