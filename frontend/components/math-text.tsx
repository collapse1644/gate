"use client";

import katex from "katex";
import { useMemo } from "react";

const DELIMITER =
  /(\$\$[\s\S]+?\$\$|\$[^$\n]+?\$|\\\[[\s\S]+?\\\]|\\\([\s\S]+?\\\))/g;

function render(source: string, displayMode: boolean): string {
  try {
    return katex.renderToString(source, {
      displayMode,
      throwOnError: false,
      strict: "ignore",
      trust: false,
      output: "html",
    });
  } catch {
    return "";
  }
}

export function MathText({
  text,
  className,
  inline = false,
}: {
  text: string;
  className?: string;
  inline?: boolean;
}) {
  const parts = useMemo(() => {
    if (!text) return [];
    return text.split(DELIMITER).filter((part) => part !== "");
  }, [text]);

  if (inline) {
    return (
      <span className={className}>
        {parts.map((part, index) => {
          const display = part.startsWith("$$") || part.startsWith("\\[");
          if (
            part.startsWith("$$") ||
            part.startsWith("$") ||
            part.startsWith("\\(") ||
            part.startsWith("\\[")
          ) {
            const inner = part
              .replace(/^\$\$|\$\$$/g, "")
              .replace(/^\$|\$$/g, "")
              .replace(/^\\\[|\\\]$/g, "")
              .replace(/^\\\(|\\\)$/g, "");
            return (
              <span
                key={index}
                dangerouslySetInnerHTML={{ __html: render(inner, display) }}
              />
            );
          }
          return <span key={index}>{part}</span>;
        })}
      </span>
    );
  }

  return (
    <div className={`math-content ${className ?? ""}`}>
      {parts.map((part, index) => {
        const display = part.startsWith("$$") || part.startsWith("\\[");
        if (
          part.startsWith("$$") ||
          part.startsWith("$") ||
          part.startsWith("\\(") ||
          part.startsWith("\\[")
        ) {
          const inner = part
            .replace(/^\$\$|\$\$$/g, "")
            .replace(/^\$|\$$/g, "")
            .replace(/^\\\[|\\\]$/g, "")
            .replace(/^\\\(|\\\)$/g, "");
          return (
            <span
              key={index}
              className={display ? "block overflow-x-auto" : undefined}
              dangerouslySetInnerHTML={{ __html: render(inner, display) }}
            />
          );
        }
        return <span key={index}>{part}</span>;
      })}
    </div>
  );
}

export function Latex({ latex, display = false, className }: { latex: string; display?: boolean; className?: string }) {
  const html = useMemo(() => {
    const value = latex
      .replace(/^\$\$|\$\$$/g, "")
      .replace(/^\$|\$$/g, "")
      .replace(/^\\\[|\\\]$/g, "")
      .replace(/^\\\(|\\\)$/g, "");
    return render(value, display);
  }, [latex, display]);
  return (
    <span
      className={className}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
