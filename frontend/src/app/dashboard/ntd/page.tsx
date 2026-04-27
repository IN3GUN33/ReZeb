"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

interface NTDDoc { id: string; code: string; title: string; doc_type: string; version: string | null }
interface ClauseResult {
  clause_id: string; doc_code: string; doc_title: string;
  clause_number: string; title: string | null; text: string; score: number
}

export default function NTDPage() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<"search" | "upload">("search");
  const [searchQ, setSearchQ] = useState("");
  const [results, setResults] = useState<ClauseResult[]>([]);

  // Upload form state
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [code, setCode] = useState("");
  const [title, setTitle] = useState("");
  const [docType, setDocType] = useState("SP");

  const { data: docs = [] } = useQuery<NTDDoc[]>({
    queryKey: ["ntd-docs"],
    queryFn: () => api.get("/ntd/documents").then((r) => r.data),
  });

  const search = useMutation({
    mutationFn: (q: string) => api.get("/ntd/search", { params: { q, top_k: 5 } }).then((r) => r.data),
    onSuccess: setResults,
  });

  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (!uploadFile) return;
      const fd = new FormData();
      fd.append("file", uploadFile);
      fd.append("code", code);
      fd.append("title", title);
      fd.append("doc_type", docType);
      return api.post("/ntd/documents", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      }).then((r) => r.data);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ntd-docs"] });
      setUploadFile(null);
      setCode("");
      setTitle("");
      setTab("search");
    },
  });

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold">База НТД</h1>
        <p className="text-sm text-muted-foreground">
          Нормативно-техническая документация — СП, ГОСТ, СНиП, СТО
        </p>
      </div>

      <div className="flex gap-1 rounded-lg bg-muted p-1 w-fit">
        {(["search", "upload"] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`rounded-md px-4 py-1.5 text-sm font-medium transition-colors ${
              tab === t ? "bg-background shadow-sm" : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {t === "search" ? "Поиск" : "Загрузить документ"}
          </button>
        ))}
      </div>

      {tab === "search" && (
        <>
          <div className="rounded-xl border bg-card p-6 space-y-4">
            <div className="flex gap-2">
              <input
                value={searchQ}
                onChange={(e) => setSearchQ(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && search.mutate(searchQ)}
                className="flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                placeholder="Расстояние между хомутами, толщина защитного слоя бетона..."
              />
              <button
                onClick={() => search.mutate(searchQ)}
                disabled={searchQ.length < 3 || search.isPending}
                className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
              >
                {search.isPending ? "..." : "Найти"}
              </button>
            </div>

            {results.length > 0 && (
              <div className="space-y-3">
                {results.map((r) => (
                  <div key={r.clause_id} className="rounded-lg border p-3 space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-mono bg-primary/10 text-primary px-2 py-0.5 rounded">
                        {r.doc_code} п.{r.clause_number}
                      </span>
                      <span className="text-xs text-muted-foreground">{Math.round(r.score * 100)}% релевантность</span>
                    </div>
                    {r.title && <p className="text-sm font-medium">{r.title}</p>}
                    <p className="text-sm text-muted-foreground leading-relaxed line-clamp-4">{r.text}</p>
                    <p className="text-xs text-muted-foreground italic">{r.doc_title}</p>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="rounded-xl border bg-card p-6">
            <h2 className="font-semibold mb-4">Загруженные документы ({docs.length})</h2>
            {docs.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-sm text-muted-foreground mb-3">Нормативные документы не загружены</p>
                <button onClick={() => setTab("upload")}
                  className="text-sm text-primary underline underline-offset-2">
                  Загрузить первый документ
                </button>
              </div>
            ) : (
              <div className="space-y-2">
                {docs.map((d) => (
                  <div key={d.id} className="flex items-center justify-between rounded-lg border p-3">
                    <div>
                      <p className="text-sm font-medium">{d.code}</p>
                      <p className="text-xs text-muted-foreground">{d.title}</p>
                    </div>
                    <span className="text-xs border rounded px-1.5 py-0.5 font-mono">{d.doc_type}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}

      {tab === "upload" && (
        <div className="rounded-xl border bg-card p-6 space-y-4">
          <h2 className="font-semibold">Загрузить нормативный документ</h2>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium">Код документа *</label>
              <input value={code} onChange={(e) => setCode(e.target.value)}
                className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                placeholder="СП 63.13330.2018" />
            </div>
            <div>
              <label className="text-sm font-medium">Тип</label>
              <select value={docType} onChange={(e) => setDocType(e.target.value)}
                className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring">
                <option value="SP">СП</option>
                <option value="GOST">ГОСТ</option>
                <option value="SNIP">СНиП</option>
                <option value="STO">СТО</option>
                <option value="OTHER">Другой</option>
              </select>
            </div>
          </div>

          <div>
            <label className="text-sm font-medium">Наименование *</label>
            <input value={title} onChange={(e) => setTitle(e.target.value)}
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              placeholder="Бетонные и железобетонные конструкции. Основные положения" />
          </div>

          <div className="rounded-lg border-2 border-dashed border-border p-6 text-center">
            <input type="file" accept=".pdf,.docx,.doc,.txt"
              onChange={(e) => setUploadFile(e.target.files?.[0] ?? null)}
              className="hidden" id="ntd-upload" />
            <label htmlFor="ntd-upload" className="cursor-pointer">
              <div className="text-3xl mb-2">📄</div>
              <p className="text-sm text-muted-foreground">
                {uploadFile ? uploadFile.name : "PDF, DOCX или TXT"}
              </p>
            </label>
          </div>

          <div className="flex gap-2">
            <button onClick={() => setTab("search")}
              className="rounded-md border px-4 py-2 text-sm hover:bg-accent transition-colors">
              Отмена
            </button>
            <button
              onClick={() => uploadMutation.mutate()}
              disabled={!uploadFile || !code || !title || uploadMutation.isPending}
              className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {uploadMutation.isPending ? "Загрузка и индексация..." : "Загрузить и проиндексировать"}
            </button>
          </div>
          {uploadMutation.isPending && (
            <p className="text-xs text-muted-foreground">
              Документ обрабатывается: нарезка на клаузулы и векторная индексация...
            </p>
          )}
        </div>
      )}
    </div>
  );
}
