"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import {
  BookOpen,
  Bot,
  Compass,
  Inbox,
  MessageSquare,
  ScrollText,
  Settings,
  Wrench,
} from "lucide-react";

import { NexarLogo } from "@/components/layout/nexar-logo";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/agent-overview", label: "Agent Overview", icon: Compass },
  { href: "/chat", label: "Chat", icon: MessageSquare },
  { href: "/sops", label: "SOPs", icon: Bot },
  { href: "/messages", label: "Messages", icon: Inbox },
  { href: "/kb", label: "Knowledge Base", icon: BookOpen },
  { href: "/resources", label: "Tools & Resources", icon: Wrench },
  { href: "/agent-rules", label: "Agent Rules", icon: ScrollText },
  { href: "/settings", label: "Agent Settings", icon: Settings },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <aside className="sticky top-0 flex h-screen w-64 shrink-0 flex-col border-r border-sidebar-border bg-sidebar shadow-[4px_0_24px_oklch(0.2_0.02_275/0.04)] dark:shadow-[4px_0_24px_oklch(0_0_0/0.35)]">
        <div className="border-b border-sidebar-border px-6 py-7">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center">
              <NexarLogo className="h-10 w-10" />
            </div>
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">
                Custom
              </p>
              <h1 className="text-lg font-semibold tracking-tight text-foreground">
                Ops Agent
              </h1>
            </div>
          </div>
        </div>
        <nav className="flex flex-1 flex-col gap-1 p-4">
          {navItems.map((item) => {
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
            const Icon = item.icon;
            return (
              <Link key={item.href} href={item.href} className="relative">
                {active && (
                  <motion.span
                    layoutId="nav-active"
                    className="absolute inset-0 rounded-xl bg-sidebar-accent shadow-sm"
                    transition={{ type: "spring", stiffness: 380, damping: 30 }}
                  />
                )}
                <span
                  className={cn(
                    "relative flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm transition-colors",
                    active
                      ? "font-semibold text-sidebar-accent-foreground"
                      : "font-medium text-sidebar-foreground hover:text-foreground",
                  )}
                >
                  <Icon
                    className={cn(
                      "h-4 w-4 shrink-0",
                      active ? "text-primary" : "text-muted-foreground",
                    )}
                  />
                  {item.label}
                </span>
              </Link>
            );
          })}
        </nav>
        <div className="space-y-4 border-t border-sidebar-border px-5 py-5">
          <ThemeToggle />
          <p className="px-1 text-xs leading-relaxed text-muted-foreground">
            Internal AI operations platform for Nexar dash cam support.
          </p>
        </div>
      </aside>
      <main className="h-screen flex-1 overflow-y-auto bg-[radial-gradient(ellipse_at_top_right,oklch(0.95_0.03_275),transparent_50%)] dark:bg-[radial-gradient(ellipse_at_top_right,oklch(0.28_0.06_275),transparent_50%)]">
        {children}
      </main>
    </div>
  );
}
