"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuthStore } from "@/stores/auth";
import { useToast } from "@/components/ui/toast";
import { api } from "@/lib/api";

interface APIKey {
  id: string;
  name: string;
  key_prefix: string;
  created_at: string;
  last_used_at: string | null;
}

export default function SettingsPage() {
  const { user, fetchMe } = useAuthStore();
  const { addToast } = useToast();
  const qc = useQueryClient();

  // Profile form
  const [fullName, setFullName] = useState(user?.full_name ?? "");
  const updateProfile = useMutation({
    mutationFn: (data: { full_name: string }) => api.patch("/auth/profile", data),
    onSuccess: () => { fetchMe(); addToast("Профиль обновлён", "success"); },
    onError: () => addToast("Ошибка обновления профиля", "error"),
  });

  // Password form
  const [currentPwd, setCurrentPwd] = useState("");
  const [newPwd, setNewPwd] = useState("");
  const changePassword = useMutation({
    mutationFn: () => api.post("/auth/profile/change-password", {
      current_password: currentPwd,
      new_password: newPwd,
    }),
    onSuccess: () => {
      setCurrentPwd(""); setNewPwd("");
      addToast("Пароль изменён", "success");
    },
    onError: () => addToast("Ошибка изменения пароля. Проверьте текущий пароль.", "error"),
  });

  // API keys
  const [newKeyName, setNewKeyName] = useState("");
  const [createdKey, setCreatedKey] = useState<string | null>(null);

  const { data: apiKeys = [] } = useQuery<APIKey[]>({
    queryKey: ["api-keys"],
    queryFn: () => api.get("/auth/api-keys").then((r) => r.data),
  });

  const createKey = useMutation({
    mutationFn: (name: string) => api.post("/auth/api-keys", { name }).then((r) => r.data),
    onSuccess: (data) => {
      setCreatedKey(data.key);
      setNewKeyName("");
      qc.invalidateQueries({ queryKey: ["api-keys"] });
      addToast("API ключ создан. Сохраните его — он больше не будет показан.", "success");
    },
  });

  const revokeKey = useMutation({
    mutationFn: (id: string) => api.delete(`/auth/api-keys/${id}`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["api-keys"] }); addToast("Ключ отозван", "success"); },
  });

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold">Настройки</h1>

      {/* Profile */}
      <div className="rounded-xl border bg-card p-6 space-y-4">
        <h2 className="font-semibold">Профиль</h2>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <label className="font-medium">Email</label>
            <p className="text-muted-foreground mt-0.5">{user?.email}</p>
          </div>
          <div>
            <label className="font-medium">Роль</label>
            <p className="text-muted-foreground mt-0.5">{user?.role}</p>
          </div>
        </div>
        <div>
          <label className="text-sm font-medium">Имя</label>
          <input value={fullName} onChange={(e) => setFullName(e.target.value)}
            className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
        </div>
        <button
          onClick={() => updateProfile.mutate({ full_name: fullName })}
          disabled={updateProfile.isPending || fullName === user?.full_name}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {updateProfile.isPending ? "Сохранение..." : "Сохранить"}
        </button>
      </div>

      {/* Change password */}
      <div className="rounded-xl border bg-card p-6 space-y-4">
        <h2 className="font-semibold">Изменить пароль</h2>
        <div className="space-y-3">
          <div>
            <label className="text-sm font-medium">Текущий пароль</label>
            <input type="password" value={currentPwd} onChange={(e) => setCurrentPwd(e.target.value)}
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
          </div>
          <div>
            <label className="text-sm font-medium">Новый пароль (мин. 8 символов)</label>
            <input type="password" value={newPwd} onChange={(e) => setNewPwd(e.target.value)}
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
          </div>
        </div>
        <button
          onClick={() => changePassword.mutate()}
          disabled={!currentPwd || newPwd.length < 8 || changePassword.isPending}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {changePassword.isPending ? "Изменение..." : "Изменить пароль"}
        </button>
      </div>

      {/* API Keys */}
      <div className="rounded-xl border bg-card p-6 space-y-4">
        <h2 className="font-semibold">API ключи</h2>
        <p className="text-xs text-muted-foreground">
          Для программного доступа к ReZeb API. Ключ показывается только при создании.
        </p>

        {createdKey && (
          <div className="rounded-lg bg-green-50 border border-green-200 p-3">
            <p className="text-xs font-medium text-green-800 mb-1">Ваш новый API ключ (сохраните сейчас!):</p>
            <code className="text-xs font-mono break-all text-green-900">{createdKey}</code>
            <button onClick={() => { navigator.clipboard.writeText(createdKey); addToast("Скопировано", "success"); }}
              className="mt-2 text-xs text-green-700 underline block">Скопировать</button>
          </div>
        )}

        <div className="flex gap-2">
          <input value={newKeyName} onChange={(e) => setNewKeyName(e.target.value)}
            className="flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            placeholder="Название ключа (например: CI/CD pipeline)" />
          <button
            onClick={() => createKey.mutate(newKeyName)}
            disabled={!newKeyName.trim() || createKey.isPending}
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 whitespace-nowrap"
          >
            Создать
          </button>
        </div>

        {apiKeys.length > 0 && (
          <div className="space-y-2">
            {apiKeys.map((k) => (
              <div key={k.id} className="flex items-center justify-between rounded-lg border p-3">
                <div>
                  <p className="text-sm font-medium">{k.name}</p>
                  <p className="text-xs font-mono text-muted-foreground">{k.key_prefix}…</p>
                </div>
                <button onClick={() => revokeKey.mutate(k.id)}
                  className="text-xs text-destructive hover:underline">
                  Отозвать
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
