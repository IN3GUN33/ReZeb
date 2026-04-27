"use client";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

interface CostInfo {
  total_rub: number;
  budget_rub: number;
  ratio: number;
  alert: boolean;
}

interface UserItem {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
}

export default function AdminPage() {
  const { user } = useAuthStore();
  const router = useRouter();
  const isAdmin = user?.role === "superadmin" || user?.role === "org_admin";

  useEffect(() => {
    if (user && !isAdmin) router.replace("/dashboard");
  }, [user, isAdmin, router]);

  const { data: costs } = useQuery<CostInfo>({
    queryKey: ["admin-costs"],
    queryFn: () => api.get("/admin/costs").then((r) => r.data),
    enabled: isAdmin,
    refetchInterval: 60_000,
  });

  const { data: users = [] } = useQuery<UserItem[]>({
    queryKey: ["admin-users"],
    queryFn: () => api.get("/admin/users").then((r) => r.data),
    enabled: isAdmin,
  });

  if (!isAdmin) return null;

  const pct = costs ? Math.round(costs.ratio * 100) : 0;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold">Администрирование</h1>

      {/* Budget panel */}
      {costs && (
        <div className={`rounded-xl border p-6 ${costs.alert ? "border-orange-300 bg-orange-50" : "bg-card"}`}>
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold">Бюджет LLM — текущий месяц</h2>
            {costs.alert && (
              <span className="text-xs rounded-full bg-orange-100 text-orange-700 px-2 py-0.5 font-medium">
                Внимание: {pct}% бюджета
              </span>
            )}
          </div>

          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>Использовано: {costs.total_rub.toLocaleString("ru")} ₽</span>
              <span>Бюджет: {costs.budget_rub.toLocaleString("ru")} ₽</span>
            </div>
            <div className="h-3 rounded-full bg-muted overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${
                  pct >= 100 ? "bg-red-500" : pct >= 80 ? "bg-orange-400" : "bg-primary"
                }`}
                style={{ width: `${Math.min(pct, 100)}%` }}
              />
            </div>
            <p className="text-xs text-muted-foreground">{pct}% от месячного лимита</p>
          </div>
        </div>
      )}

      {/* Users table */}
      <div className="rounded-xl border bg-card p-6">
        <h2 className="font-semibold mb-4">Пользователи ({users.length})</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-muted-foreground">
                <th className="pb-2 pr-4">Email</th>
                <th className="pb-2 pr-4">Имя</th>
                <th className="pb-2 pr-4">Роль</th>
                <th className="pb-2">Статус</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {users.map((u) => (
                <tr key={u.id} className="hover:bg-muted/30">
                  <td className="py-2 pr-4 font-mono text-xs">{u.email}</td>
                  <td className="py-2 pr-4">{u.full_name}</td>
                  <td className="py-2 pr-4">
                    <span className="text-xs border rounded px-1.5 py-0.5">{u.role}</span>
                  </td>
                  <td className="py-2">
                    <span className={`text-xs rounded-full px-2 py-0.5 font-medium ${
                      u.is_active ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"
                    }`}>
                      {u.is_active ? "Активен" : "Заблокирован"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
