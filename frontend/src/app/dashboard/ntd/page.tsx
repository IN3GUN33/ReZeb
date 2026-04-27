"use client";
import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";

interface NTDDoc { id: string; code: string; title: string; doc_type: string; version: string | null }
interface ClauseResult { clause_id: string; doc_code: string; doc_title: string; clause_number: string; title: string | null; text: string; score: number }

export default function NTDPage() {
  const [searchQ, setSearchQ] = useState("");
  const [results, setResults] = useState<ClauseResult[]>([]);

  const { data: docs = [] } = useQuery<NTDDoc[]>({
    queryKey: ["ntd-docs"],
    queryFn: () => api.get("/ntd/documents").then((r) => r.data),
  });

  const search = useMutation({
    mutationFn: (q: string) => api.get("/ntd/search", { params: { q, top_k: 5 } }).then((r) => r.data),
    onSuccess: setResults,
  });

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold">База НТД</h1>
        <p className="text-sm text-muted-foreground">Нормативно-техническая документация (СП, ГОСТ, СНиП)</p>
      </div>

      <div className="rounded-xl border bg-card p-6 space-y-4">
        <div className="flex gap-2">
          <input
            value={searchQ}
            onChange={(e) => setSearchQ(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && search.mutate(searchQ)}
            className="flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            placeholder="Поиск по НТД: расстояние между опорами, армирование..."
          />
          <button
            onClick={() => search.mutate(searchQ)}
            disabled={searchQ.length < 3 || search.isPending}
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {search.isPending ? "..." : "Поиск"}
          </button>
        </div>

        {results.length > 0 && (
          <div className="space-y-3">
            {results.map((r) => (
              <div key={r.clause_id} className="rounded-lg border p-3 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono bg-muted px-1.5 py-0.5 rounded">
                    {r.doc_code} п.{r.clause_number}
                  </span>
                  <span className="text-xs text-muted-foreground">{Math.round(r.score * 100)}%</span>
                </div>
                {r.title && <p className="text-sm font-medium">{r.title}</p>}
                <p className="text-sm text-muted-foreground line-clamp-3">{r.text}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="rounded-xl border bg-card p-6">
        <h2 className="font-semibold mb-4">Загруженные документы ({docs.length})</h2>
        {docs.length === 0 ? (
          <p className="text-sm text-muted-foreground">Документы не загружены</p>
        ) : (
          <div className="space-y-2">
            {docs.map((d) => (
              <div key={d.id} className="flex items-center justify-between rounded-lg border p-3">
                <div>
                  <p className="text-sm font-medium">{d.code}</p>
                  <p className="text-xs text-muted-foreground">{d.title}</p>
                </div>
                <span className="text-xs border rounded px-1.5 py-0.5">{d.doc_type}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
