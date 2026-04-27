"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { PTOQuery } from "@/types";

export default function PTOPage() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<"single" | "batch" | "import">("single");
  const [rawText, setRawText] = useState("");
  const [batchText, setBatchText] = useState("");
  const [activeQueryIds, setActiveQueryIds] = useState<string[]>([]);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importResult, setImportResult] = useState<{ imported: number; skipped: number; errors: number } | null>(null);

  const createQuery = useMutation({
    mutationFn: (text: string) =>
      api.post("/pto/queries", { raw_text: text }).then((r) => r.data),
    onSuccess: (q: PTOQuery) => {
      setActiveQueryIds((prev) => [q.id, ...prev]);
      setRawText("");
    },
  });

  const handleBatchSubmit = async () => {
    const lines = batchText.split("\n").map((l) => l.trim()).filter((l) => l.length > 2);
    for (const line of lines) {
      const q: PTOQuery = await api.post("/pto/queries", { raw_text: line }).then((r) => r.data);
      setActiveQueryIds((prev) => [q.id, ...prev]);
    }
    setBatchText("");
  };

  const importMutation = useMutation({
    mutationFn: async (file: File) => {
      const fd = new FormData();
      fd.append("file", file);
      return api.post("/pto/registry/import", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      }).then((r) => r.data);
    },
    onSuccess: (result) => {
      setImportResult(result);
      setImportFile(null);
    },
  });

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Ассистент ПТО</h1>
        <p className="text-sm text-muted-foreground">
          Подбор материалов из реестра по наименованиям из проектной документации
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 rounded-lg bg-muted p-1 w-fit">
        {(["single", "batch", "import"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`rounded-md px-4 py-1.5 text-sm font-medium transition-colors ${
              tab === t ? "bg-background shadow-sm" : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {t === "single" ? "Одна позиция" : t === "batch" ? "Пакет" : "Импорт реестра"}
          </button>
        ))}
      </div>

      {tab === "single" && (
        <div className="rounded-xl border bg-card p-6 space-y-4">
          <label className="text-sm font-medium">Наименование материала</label>
          <textarea
            value={rawText}
            onChange={(e) => setRawText(e.target.value)}
            rows={4}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-none"
            placeholder="Кирпич керамический рядовой полнотелый М150 250×120×65 ГОСТ 530-2012..."
          />
          <button
            onClick={() => createQuery.mutate(rawText)}
            disabled={rawText.trim().length < 2 || createQuery.isPending}
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {createQuery.isPending ? "Отправка..." : "Найти в реестре"}
          </button>
        </div>
      )}

      {tab === "batch" && (
        <div className="rounded-xl border bg-card p-6 space-y-4">
          <div>
            <label className="text-sm font-medium">Список позиций (одна позиция — одна строка)</label>
            <p className="text-xs text-muted-foreground mt-0.5">Скопируйте из Excel или Word</p>
          </div>
          <textarea
            value={batchText}
            onChange={(e) => setBatchText(e.target.value)}
            rows={10}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-ring resize-none"
            placeholder={"Арматура А400 ф12 ГОСТ 5781-82\nБетон В25 ГОСТ 26633-2015\nКирпич М150 250×120×65"}
          />
          <div className="flex items-center justify-between">
            <p className="text-xs text-muted-foreground">
              {batchText.split("\n").filter((l) => l.trim().length > 2).length} позиций
            </p>
            <button
              onClick={handleBatchSubmit}
              disabled={batchText.trim().length < 2}
              className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              Запустить подбор
            </button>
          </div>
        </div>
      )}

      {tab === "import" && (
        <div className="rounded-xl border bg-card p-6 space-y-4">
          <div>
            <h2 className="text-sm font-medium">Импорт реестра материалов</h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              Загрузите Excel-файл (.xlsx) с реестром. Колонки: наименование, код, ед.изм., категория
            </p>
          </div>

          <div className="rounded-lg border-2 border-dashed border-border p-8 text-center">
            <input
              type="file"
              accept=".xlsx,.xls"
              onChange={(e) => setImportFile(e.target.files?.[0] ?? null)}
              className="hidden"
              id="registry-upload"
            />
            <label htmlFor="registry-upload" className="cursor-pointer">
              <div className="text-4xl mb-2">📊</div>
              <p className="text-sm text-muted-foreground">
                {importFile ? importFile.name : "Выберите Excel-файл реестра"}
              </p>
            </label>
          </div>

          {importResult && (
            <div className="rounded-lg bg-muted p-3 text-sm">
              <p className="font-medium">Результат импорта:</p>
              <p>Добавлено: <span className="text-green-600">{importResult.imported}</span></p>
              <p>Пропущено (дубли): <span className="text-yellow-600">{importResult.skipped}</span></p>
              <p>Ошибок: <span className="text-red-600">{importResult.errors}</span></p>
            </div>
          )}

          <button
            onClick={() => importFile && importMutation.mutate(importFile)}
            disabled={!importFile || importMutation.isPending}
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {importMutation.isPending ? "Импорт..." : "Загрузить реестр"}
          </button>
        </div>
      )}

      {/* Query Results */}
      {activeQueryIds.length > 0 && (
        <div className="space-y-3">
          <h2 className="font-semibold">Результаты ({activeQueryIds.length})</h2>
          {activeQueryIds.map((qid) => (
            <QueryResult key={qid} queryId={qid} />
          ))}
        </div>
      )}
    </div>
  );
}

function QueryResult({ queryId }: { queryId: string }) {
  const { data } = useQuery<PTOQuery>({
    queryKey: ["pto-query", queryId],
    queryFn: () => api.get(`/pto/queries/${queryId}`).then((r) => r.data),
    refetchInterval: (query) => {
      const s = query.state.data?.status;
      return s === "completed" || s === "failed" ? false : 2000;
    },
  });

  if (!data) return <div className="rounded-lg border p-3 text-sm text-muted-foreground">Загрузка...</div>;

  const matchBadge = {
    exact: { label: "Точное совпадение", cls: "bg-green-50 text-green-700" },
    analog: { label: "Аналог", cls: "bg-yellow-50 text-yellow-700" },
    not_found: { label: "Не найдено", cls: "bg-red-50 text-red-700" },
  };

  return (
    <div className="rounded-xl border bg-card p-4 space-y-2">
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-medium line-clamp-2">{data.raw_text}</p>
        {data.status === "processing" && (
          <div className="h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-primary border-t-transparent mt-0.5" />
        )}
        {data.match_status && (
          <span className={`shrink-0 text-xs rounded-full px-2 py-0.5 font-medium ${matchBadge[data.match_status]?.cls ?? "bg-gray-100 text-gray-600"}`}>
            {matchBadge[data.match_status]?.label}
          </span>
        )}
      </div>

      {data.normalized_text && data.normalized_text !== data.raw_text && (
        <p className="text-xs text-muted-foreground">↳ {data.normalized_text}</p>
      )}

      {data.results.length > 0 && (
        <div className="space-y-1">
          {data.results.slice(0, 3).map((r) => (
            <div key={r.registry_id} className="flex items-center justify-between text-xs bg-muted rounded px-2 py-1">
              <span className="truncate">{r.name}</span>
              {r.unit && <span className="ml-2 text-muted-foreground shrink-0">{r.unit}</span>}
            </div>
          ))}
        </div>
      )}

      {data.confidence != null && (
        <p className="text-xs text-muted-foreground">Уверенность: {Math.round(data.confidence * 100)}%</p>
      )}
    </div>
  );
}
