"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  BookOpen,
  Bot,
  CircleDollarSign,
  Compass,
  Inbox,
  MessageSquare,
  PanelLeft,
  PanelLeftClose,
  ScrollText,
  Settings,
  Wrench,
} from "lucide-react";

import { OpsLogo } from "@/components/layout/ops-logo";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const SIDEBAR_KEY = "ops-agent.sidebar-collapsed";

const workspaceNav = [
  { href: "/agent-overview", label: "Overview", icon: Compass },
  { href: "/chat", label: "Chat", icon: MessageSquare },
  { href: "/messages", label: "Messages", icon: Inbox },
  { href: "/usage", label: "Usage", icon: CircleDollarSign },
];

const configureNav = [
  { href: "/sops", label: "SOPs", icon: Bot },
  { href: "/kb", label: "Knowledge Base", icon: BookOpen },
  { href: "/resources", label: "Tools", icon: Wrench },
  { href: "/agent-rules", label: "Agent Rules", icon: ScrollText },
  { href: "/settings", label: "Settings", icon: Settings },
];

function NavGroup({
  label,
  items,
  pathname,
  collapsed,
}: {
  label: string;
  items: typeof workspaceNav;
  pathname: string;
  collapsed: boolean;
}) {
  return (
    <div className="space-y-1">
      {!collapsed && (
        <p className="px-2.5 pb-1 pt-2.5 text-[11px] font-semibold tracking-[-0.01em] text-muted-foreground">
          {label}
        </p>
      )}
      {items.map((item) => {
        const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
        const Icon = item.icon;
        return (
          <Link
            key={item.href}
            href={item.href}
            title={item.label}
            aria-label={item.label}
            className={cn("relative block overflow-hidden", collapsed && "mx-auto w-8")}
          >
            {active && (
              <motion.span
                layoutId="nav-active"
                className="absolute inset-0 rounded-xl bg-sidebar-accent shadow-sm"
                transition={{ type: "spring", stiffness: 380, damping: 30 }}
              />
            )}
            <span
              className={cn(
                "relative flex items-center rounded-lg py-[7px] text-[13px] leading-none tracking-[-0.01em] transition-colors",
                collapsed ? "justify-center px-0" : "gap-2.5 px-2.5",
                active
                  ? "font-semibold text-sidebar-accent-foreground"
                  : "font-medium text-sidebar-foreground/85 hover:text-foreground",
              )}
            >
              <Icon
                className={cn(
                  "h-3.5 w-3.5 shrink-0",
                  active ? "text-primary" : "text-muted-foreground",
                )}
              />
              {!collapsed && item.label}
            </span>
          </Link>
        );
      })}
    </div>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    setCollapsed(localStorage.getItem(SIDEBAR_KEY) === "1");
  }, []);

  const toggleCollapsed = () => {
    setCollapsed((current) => {
      const next = !current;
      localStorage.setItem(SIDEBAR_KEY, next ? "1" : "0");
      return next;
    });
  };

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <aside
        className={cn(
          "sticky top-0 flex h-screen shrink-0 flex-col overflow-hidden border-r border-sidebar-border bg-sidebar font-sans antialiased transition-[width] duration-200",
          collapsed ? "w-14" : "w-52",
        )}
      >
        <div className={cn("border-b border-sidebar-border", collapsed ? "px-1.5 py-2.5" : "px-3 py-2.5")}>
          <div className={cn("flex items-center", collapsed ? "flex-col gap-2" : "gap-2")}>
            <OpsLogo className="h-7 w-7 shrink-0" />
            {!collapsed && (
              <div className="min-w-0 flex-1">
                <h1 className="text-[13px] font-semibold leading-tight tracking-[-0.02em] text-foreground">
                  Ops Agent
                </h1>
                <p className="text-[11px] font-medium leading-tight tracking-[-0.01em] text-muted-foreground">
                  Support copilot
                </p>
              </div>
            )}
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-7 w-7 shrink-0"
              onClick={toggleCollapsed}
              title={collapsed ? "Expand navigation" : "Collapse navigation"}
              aria-label={collapsed ? "Expand navigation" : "Collapse navigation"}
            >
              {collapsed ? <PanelLeft className="h-3.5 w-3.5" /> : <PanelLeftClose className="h-3.5 w-3.5" />}
            </Button>
          </div>
        </div>
        <nav className={cn("flex flex-1 flex-col overflow-y-auto py-1.5", collapsed ? "px-1.5" : "px-2")}>
          <NavGroup label="Workspace" items={workspaceNav} pathname={pathname} collapsed={collapsed} />
          <NavGroup label="Configure" items={configureNav} pathname={pathname} collapsed={collapsed} />
        </nav>
        <div className={cn("space-y-2 border-t border-sidebar-border py-2.5", collapsed ? "px-1.5" : "px-2.5")}>
          {!collapsed ? (
            <div className="flex items-center justify-between rounded-lg border border-sidebar-border bg-sidebar-accent/40 px-2.5 py-1.5">
              <div>
                <p className="text-[12px] font-semibold leading-tight tracking-[-0.01em] text-foreground">
                  Workspace
                </p>
                <p className="text-[11px] font-medium leading-tight tracking-[-0.01em] text-muted-foreground">
                  Simulated tools
                </p>
              </div>
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-1.5 py-0.5 text-[11px] font-medium tracking-[-0.01em] text-emerald-700 dark:text-emerald-300">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                Ready
              </span>
            </div>
          ) : (
            <div
              className="flex justify-center"
              title="Workspace ready"
            >
              <span className="h-2 w-2 rounded-full bg-emerald-500" />
            </div>
          )}
          <ThemeToggle compact={collapsed} />
        </div>
      </aside>
      <main className="h-screen min-w-0 flex-1 overflow-y-auto bg-[radial-gradient(ellipse_at_top_right,oklch(0.95_0.03_275),transparent_50%)] dark:bg-[radial-gradient(ellipse_at_top_right,oklch(0.28_0.06_275),transparent_50%)]">
        {children}
      </main>
    </div>
  );
}
