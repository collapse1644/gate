"use client";

import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";

export function ThemeToggle({ compact = false }: { compact?: boolean }) {
  const [dark, setDark] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    setDark(document.documentElement.classList.contains("dark"));
  }, []);

  function toggle() {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    document.documentElement.style.colorScheme = next ? "dark" : "light";
    window.localStorage.setItem("gate-theme", next ? "dark" : "light");
  }

  if (!mounted) {
    return <div className={compact ? "h-9 w-9" : "h-9 w-full"} aria-hidden />;
  }

  if (compact) {
    return (
      <button
        type="button"
        onClick={toggle}
        className="btn-secondary h-9 w-9 p-0"
        aria-label={dark ? "Switch to light theme" : "Switch to dark theme"}
        title={dark ? "Light theme" : "Dark theme"}
      >
        {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
      </button>
    );
  }

  return (
    <button type="button" onClick={toggle} className="btn-secondary w-full justify-between">
      <span className="flex items-center gap-2">
        {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        {dark ? "Light theme" : "Dark theme"}
      </span>
      <span className="text-[10px] uppercase tracking-widest text-muted">
        {dark ? "On" : "Off"}
      </span>
    </button>
  );
}
