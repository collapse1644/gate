import type { Metadata } from "next";
import "katex/dist/katex.min.css";

import { AppShell } from "@/components/app-shell";

import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "GATE CS 2027 — Local-first PYQ Tutor",
    template: "%s · GATE CS 2027 Tutor",
  },
  description:
    "A local-first GATE Computer Science 2027 study workspace built on the official syllabus and your own PYQ PDFs.",
};

const themeScript = `
(function () {
  try {
    var stored = localStorage.getItem('gate-theme');
    var prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    var dark = stored ? stored === 'dark' : prefersDark;
    if (dark) {
      document.documentElement.classList.add('dark');
      document.documentElement.style.colorScheme = 'dark';
    }
  } catch (e) {}
})();
`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
