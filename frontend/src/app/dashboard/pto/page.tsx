"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { PTOQuery } from "@/types";

export default function PTOPage() {
  const qc = useQueryClient();
  const [rawText, setRawText] = useState("");
  const [activeQueryId, setActiveQueryId] = useState<string | null>(null);

  const { data: activeQuery } = useQuery<PTOQuery>({
    queryKey: ["pto-query", activeQueryId],
    queryFn: () => api.get(`/pto/queries/${activeQueryId}`).then((r) => r.data),
    enabled: !!activeQueryId,
    refetchInterval: (query) => {
      const s = query.state.data?.status;
      return s === "completed" || s === "failed" ? false : 2000;
    },
  });

  const createQuery = useMutation({
    mutationFn: (text: string) =>
      api.post("/pto/queries", { raw_text: text }).then((r) => r.data),
    onSuccess: (q: PTOQuery) => {
      setActiveQueryId(q.id);
      setRawText("");
    },
  });

  const matchStatusLabel = (s: string | null | undefined) => {
    if (s === "exact") return { label: "Точное совпадение", cls: "bg-green-50 text-green-700" };
    if (s === "analog") return { label: "Аналог", cls: "bg-yellow-50 text-yellow-700" };
    if (s === "not_found") return { label: "Не найдено", cls: "bg-red-50 text-red-700" };
    return { label: "—", cls: "bg-gray-100 text-gray-600" };
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Ассистент ПТО</h1>
        <p className="text-sm text-muted-foreground">
          Введите наименование материала из проектной документации для поиска в реестре
        </p>
      </div>

      <div className="rounded-xl border bg-card p-6 space-y-4">
        <label className="text-sm font-medium">Наименование материала</label>
        <textarea
          value={rawText}
          onChange={(e) => setRawText(e.target.value)}
          rows={4}
          className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-none"
          placeholder="Например: Кирпич КО-22 ГОСТ 530-2012, полнотелый, 250×120×65, М150..."
        />
        <button
          onClick={() => createQuery.mutate(rawText)}
          disabled={rawText.trim().length < 2 || createQuery.isPending}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {createQuery.isPending ? "Отправка..." : "Найти в реестре"}
        </button>
      </div>

      {activeQuery && (
        <div className="rounded-xl border bg-card p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold">Результат подбора</h2>
            <span className={`text-xs rounded-full px-2 py-0.5 font-medium ${
              activeQuery.status === "completed" ? "bg-green-50 text-green-700" :
              activeQuery.status === "failed" ? "bg-red-50 text-red-700" :
              "bg-yellow-50 text-yellow-700"
            }`}>
              {activeQuery.status === "completed" ? "Готово" :
               activeQuery.status === "failed" ? "Ошибка" : "Обработка..."}
            </span>
          </div>

          {activeQuery.status === "processing" && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
              Нормализация и поиск в реестре...
            </div>
          )}

          {activeQuery.status === "completed" && (
            <div className="space-y-3">
              {activeQuery.normalized_text && (
                <div className="rounded-lg bg-muted p-3">
                  <p className="text-xs text-muted-foreground">Нормализованный запрос:</p>
                  <p className="text-sm">{activeQuery.normalized_text}</p>
                </div>
              )}

              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">Статус:</span>
                {(() => {
                  const { label, cls } = matchStatusLabel(activeQuery.match_status);
                  return <span className={`text-xs rounded-full px-2 py-0.5 font-medium ${cls}`}>{label}</span>;
                })()}
                {activeQuery.confidence != null && (
                  <span className="text-xs text-muted-foreground">
                    {Math.round(activeQuery.confidence * 100)}% уверенность
                  </span>
                )}
              </div>

              {activeQuery.results.length > 0 && (
                <div className="space-y-2">
                  <p className="text-sm font-medium">Кандидаты из реестра:</p>
                  {activeQuery.results.map((r, i) => (
                    <div key={r.registry_id} className="rounded-lg border p-3">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <p className="text-sm font-medium">{r.name}</p>
                          {r.code && <p className="text-xs text-muted-foreground">Код: {r.code}</p>}
                        </div>
                        {r.unit && <span className="text-xs border rounded px-1.5 py-0.5">{r.unit}</span>}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
