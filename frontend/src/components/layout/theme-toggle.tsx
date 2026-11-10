"use client";

import { useEffect, useState } from "react";
import { useTheme } from "next-themes";
import { Monitor, Moon, Sun } from "lucide-react";
import { motion } from "framer-motion";

import { cn } from "@/lib/utils";

const options = [
  { value: "light", label: "Light", icon: Sun },
  { value: "dark", label: "Dark", icon: Moon },
  { value: "system", label: "System", icon: Monitor },
] as const;

export function ThemeToggle({ compact = false }: { compact?: boolean }) {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const current = options.find((option) => option.value === theme) ?? options[2];

  if (compact) {
    const CompactIcon = current.icon;
    return (
      <button
        type="button"
        aria-label={`Theme: ${current.label}. Click to change.`}
        title={`Theme: ${current.label}`}
        onClick={() => {
          const index = options.findIndex((option) => option.value === current.value);
          const next = options[(index + 1) % options.length];
          setTheme(next.value);
        }}
        className="mx-auto flex h-7 w-7 items-center justify-center rounded-lg border border-sidebar-border bg-sidebar-accent/50 text-sidebar-foreground transition-colors hover:text-foreground"
      >
        <CompactIcon className="h-3.5 w-3.5" />
      </button>
    );
  }

  return (
    <div
      role="group"
      aria-label="Theme"
      className="relative flex rounded-lg border border-sidebar-border bg-sidebar-accent/50 p-0.5"
    >
      {options.map(({ value, label, icon: Icon }) => {
        const active = mounted && theme === value;
        return (
          <button
            key={value}
            type="button"
            aria-label={label}
            aria-pressed={active}
            title={label}
            onClick={() => setTheme(value)}
            className={cn(
              "relative flex h-7 flex-1 items-center justify-center rounded-md transition-colors",
              active
                ? "text-sidebar-accent-foreground"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            {active && (
              <motion.span
                layoutId="theme-toggle-active"
                className="absolute inset-0 rounded-lg bg-background shadow-sm"
                transition={{ type: "spring", stiffness: 400, damping: 30 }}
              />
            )}
            <Icon className="relative h-3.5 w-3.5" />
          </button>
        );
      })}
    </div>
  );
}
