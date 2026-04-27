"use client";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";
import Link from "next/link";

interface Stats {
  users_total: number;
  control_sessions_total: number;
  pto_queries_total: number;
  registry_items: number;
  monthly_llm_cost_rub: number;
}

function StatCard({ label, value, href }: { label: string; value: string | number; href?: string }) {
  const content = (
    <div className="rounded-xl border bg-card p-5 hover:shadow-sm transition-shadow">
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="text-2xl font-bold mt-1">{value}</p>
    </div>
  );
  return href ? <Link href={href}>{content}</Link> : content;
}

export default function DashboardHome() {
  const { user } = useAuthStore();
  const isAdmin = user?.role === "superadmin" || user?.role === "org_admin";

  const { data: stats } = useQuery<Stats>({
    queryKey: ["admin-stats"],
    queryFn: () => api.get("/admin/stats").then((r) => r.data),
    enabled: isAdmin,
    staleTime: 30_000,
  });

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Добро пожаловать, {user?.full_name}</h1>
        <p className="text-sm text-muted-foreground">AI-платформа строительного контроля ReZeb</p>
      </div>

      {/* Quick actions */}
      <div className="grid grid-cols-2 gap-4">
        <Link href="/dashboard/control">
          <div className="rounded-xl border bg-card p-6 hover:shadow-md transition-shadow cursor-pointer">
            <div className="text-3xl mb-3">🔍</div>
            <h2 className="font-semibold">Ассистент контроля</h2>
            <p className="text-sm text-muted-foreground mt-1">
              Загрузите фото конструкции для AI-анализа дефектов
            </p>
          </div>
        </Link>
        <Link href="/dashboard/pto">
          <div className="rounded-xl border bg-card p-6 hover:shadow-md transition-shadow cursor-pointer">
            <div className="text-3xl mb-3">📋</div>
            <h2 className="font-semibold">Ассистент ПТО</h2>
            <p className="text-sm text-muted-foreground mt-1">
              Подбор материалов из реестра по документации
            </p>
          </div>
        </Link>
      </div>

      {/* Admin stats */}
      {isAdmin && stats && (
        <div className="space-y-4">
          <h2 className="font-semibold text-lg">Статистика системы</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard label="Пользователей" value={stats.users_total} href="/dashboard/admin" />
            <StatCard label="Сессий контроля" value={stats.control_sessions_total} href="/dashboard/control" />
            <StatCard label="Запросов ПТО" value={stats.pto_queries_total} href="/dashboard/pto" />
            <StatCard label="Позиций в реестре" value={stats.registry_items.toLocaleString("ru")} href="/dashboard/pto" />
          </div>
          <div className="rounded-xl border bg-card p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Расходы на LLM (текущий месяц)</p>
                <p className="text-2xl font-bold mt-1">
                  {stats.monthly_llm_cost_rub.toLocaleString("ru", { style: "currency", currency: "RUB", maximumFractionDigits: 0 })}
                </p>
              </div>
              <Link href="/dashboard/admin"
                className="text-sm text-primary underline underline-offset-2">
                Подробнее
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* Recent activity placeholder */}
      <div className="rounded-xl border bg-card p-6">
        <h2 className="font-semibold mb-3">Быстрый старт</h2>
        <ol className="space-y-2 text-sm text-muted-foreground list-decimal list-inside">
          <li>Создайте новую сессию в разделе <Link href="/dashboard/control" className="text-primary underline">Контроль</Link></li>
          <li>Загрузите одну или несколько фотографий строительной конструкции</li>
          <li>Нажмите «Запустить анализ» — AI проверит дефекты и сославшись на НТД</li>
          <li>В разделе <Link href="/dashboard/pto" className="text-primary underline">ПТО</Link> вставьте наименования материалов из проектной документации</li>
          <li>Загрузите реестр материалов вашей организации (Excel) для точного подбора</li>
        </ol>
      </div>
    </div>
  );
}
