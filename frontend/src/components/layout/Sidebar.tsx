"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth";

const navItems = [
  { href: "/dashboard", label: "Обзор", icon: "🏠", exact: true },
  { href: "/dashboard/projects", label: "Проекты", icon: "🏗️" },
  { href: "/dashboard/control", label: "Контроль", icon: "🔍" },
  { href: "/dashboard/pto", label: "ПТО", icon: "📋" },
  { href: "/dashboard/ntd", label: "НТД", icon: "📚" },
  { href: "/dashboard/settings", label: "Настройки", icon: "⚙️" },
  { href: "/dashboard/admin", label: "Администрирование", icon: "🛡️", adminOnly: true },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuthStore();
  const isAdmin = user?.role === "superadmin" || user?.role === "org_admin";

  return (
    <aside className="flex h-full w-60 flex-col border-r bg-card">
      <div className="flex h-16 items-center px-6 border-b">
        <span className="text-xl font-bold text-primary">ReZeb</span>
      </div>

      <nav className="flex-1 space-y-1 p-4">
        {navItems
          .filter((item) => !("adminOnly" in item) || isAdmin)
          .map((item) => {
            const isActive = "exact" in item && item.exact
              ? pathname === item.href
              : pathname.startsWith(item.href) && item.href !== "/dashboard";
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  isActive || pathname === item.href
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                )}
              >
                <span>{item.icon}</span>
                {item.label}
              </Link>
            );
          })}
      </nav>

      <div className="border-t p-4">
        <div className="mb-2 text-xs text-muted-foreground">{user?.email}</div>
        <button
          onClick={logout}
          className="w-full rounded-md border px-3 py-1.5 text-sm hover:bg-accent transition-colors"
        >
          Выйти
        </button>
      </div>
    </aside>
  );
}
