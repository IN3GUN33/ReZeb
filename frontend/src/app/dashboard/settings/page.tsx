"use client";
import { useAuthStore } from "@/stores/auth";

export default function SettingsPage() {
  const { user } = useAuthStore();

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold">Настройки</h1>

      <div className="rounded-xl border bg-card p-6 space-y-4">
        <h2 className="font-semibold">Профиль</h2>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-muted-foreground">Email</p>
            <p className="font-medium">{user?.email}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Имя</p>
            <p className="font-medium">{user?.full_name}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Роль</p>
            <p className="font-medium">{user?.role}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Статус</p>
            <p className="font-medium">{user?.is_active ? "Активен" : "Заблокирован"}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
