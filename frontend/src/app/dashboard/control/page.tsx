"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Session } from "@/types";

function severityColor(s: string) {
  if (s === "critical") return "text-red-600 bg-red-50";
  if (s === "significant") return "text-orange-600 bg-orange-50";
  return "text-green-600 bg-green-50";
}

function severityLabel(s: string) {
  if (s === "critical") return "Критический";
  if (s === "significant") return "Значительный";
  return "Допустимый";
}

export default function ControlPage() {
  const qc = useQueryClient();
  const [activeSession, setActiveSession] = useState<string | null>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [pollingId, setPollingId] = useState<string | null>(null);

  const { data: sessions = [], isLoading } = useQuery<Session[]>({
    queryKey: ["sessions"],
    queryFn: () => api.get("/control/sessions").then((r) => r.data),
  });

  const { data: sessionDetail } = useQuery<Session>({
    queryKey: ["session", pollingId],
    queryFn: () => api.get(`/control/sessions/${pollingId}`).then((r) => r.data),
    enabled: !!pollingId,
    refetchInterval: (query) => {
      const s = query.state.data?.status;
      return s === "completed" || s === "failed" ? false : 2000;
    },
  });

  const createSession = useMutation({
    mutationFn: () => api.post("/control/sessions", {}).then((r) => r.data),
    onSuccess: (s: Session) => {
      setActiveSession(s.id);
      qc.invalidateQueries({ queryKey: ["sessions"] });
    },
  });

  const uploadPhoto = useMutation({
    mutationFn: async ({ sessionId, file }: { sessionId: string; file: File }) => {
      const fd = new FormData();
      fd.append("file", file);
      return api.post(`/control/sessions/${sessionId}/photos`, fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
    },
  });

  const analyze = useMutation({
    mutationFn: (sessionId: string) =>
      api.post(`/control/sessions/${sessionId}/analyze`).then((r) => r.data),
    onSuccess: (_, sessionId) => {
      setPollingId(sessionId);
      setActiveSession(null);
      setFiles([]);
    },
  });

  const handleStartAnalysis = async () => {
    if (!activeSession || files.length === 0) return;
    for (const f of files) {
      await uploadPhoto.mutateAsync({ sessionId: activeSession, file: f });
    }
    await analyze.mutateAsync(activeSession);
    qc.invalidateQueries({ queryKey: ["sessions"] });
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Ассистент контроля</h1>
          <p className="text-sm text-muted-foreground">Загрузите фото строительной конструкции для анализа</p>
        </div>
        <button
          onClick={() => createSession.mutate()}
          disabled={createSession.isPending}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          Новая сессия
        </button>
      </div>

      {activeSession && (
        <div className="rounded-xl border bg-card p-6 space-y-4">
          <h2 className="font-semibold">Сессия создана</h2>
          <div className="rounded-lg border-2 border-dashed border-border p-8 text-center">
            <input
              type="file"
              multiple
              accept="image/*"
              onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
              className="hidden"
              id="file-upload"
            />
            <label htmlFor="file-upload" className="cursor-pointer">
              <div className="text-4xl mb-2">📷</div>
              <p className="text-sm text-muted-foreground">Нажмите для выбора фотографий (JPEG, PNG)</p>
              {files.length > 0 && (
                <p className="text-sm font-medium mt-2 text-primary">
                  Выбрано: {files.length} {files.length === 1 ? "фото" : "фото"}
                </p>
              )}
            </label>
          </div>
          <button
            onClick={handleStartAnalysis}
            disabled={files.length === 0 || analyze.isPending || uploadPhoto.isPending}
            className="w-full rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {analyze.isPending || uploadPhoto.isPending ? "Обработка..." : "Запустить анализ"}
          </button>
        </div>
      )}

      {pollingId && sessionDetail && (
        <div className="rounded-xl border bg-card p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold">Результат анализа</h2>
            <StatusBadge status={sessionDetail.status} />
          </div>

          {sessionDetail.status === "processing" && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
              Идёт анализ с помощью AI...
            </div>
          )}

          {sessionDetail.status === "completed" && sessionDetail.verdict && (
            <div className="space-y-3">
              <div className="rounded-lg bg-muted p-3">
                <p className="text-sm font-medium">
                  Тип конструкции: {sessionDetail.construction_type ?? "—"}
                  {sessionDetail.construction_type_confidence != null && (
                    <span className="text-muted-foreground">
                      {" "}({Math.round(sessionDetail.construction_type_confidence * 100)}%)
                    </span>
                  )}
                </p>
                <p className="text-sm mt-1">{sessionDetail.verdict.overall_assessment}</p>
                {sessionDetail.escalated && (
                  <p className="text-xs text-orange-600 mt-1">Выполнена эскалация к модели Opus 4.7</p>
                )}
              </div>

              {sessionDetail.defects.length > 0 && (
                <div className="space-y-2">
                  <h3 className="text-sm font-semibold">Выявленные дефекты:</h3>
                  {sessionDetail.defects.map((d) => (
                    <div key={d.id} className="rounded-lg border p-3 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">{d.defect_type}</span>
                        <span className={`text-xs rounded-full px-2 py-0.5 font-medium ${severityColor(d.severity)}`}>
                          {severityLabel(d.severity)}
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground">{d.description}</p>
                      {d.measurement_mm != null && (
                        <p className="text-xs">Размер: {d.measurement_mm} мм</p>
                      )}
                      {d.ntd_references.length > 0 && (
                        <div className="text-xs text-muted-foreground">
                          НТД: {d.ntd_references.map((r) => `${r.code} п.${r.clause}`).join(", ")}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              <p className="text-xs text-muted-foreground italic">
                {sessionDetail.verdict.disclaimer}
              </p>
            </div>
          )}

          {sessionDetail.status === "failed" && (
            <p className="text-sm text-destructive">{sessionDetail.error_message}</p>
          )}
        </div>
      )}

      <div className="rounded-xl border bg-card p-6">
        <h2 className="font-semibold mb-4">История сессий</h2>
        {isLoading ? (
          <p className="text-sm text-muted-foreground">Загрузка...</p>
        ) : sessions.length === 0 ? (
          <p className="text-sm text-muted-foreground">Сессий пока нет</p>
        ) : (
          <div className="space-y-2">
            {sessions.map((s) => (
              <div
                key={s.id}
                className="flex items-center justify-between rounded-lg border p-3 cursor-pointer hover:bg-accent"
                onClick={() => setPollingId(s.id)}
              >
                <div>
                  <p className="text-sm font-medium">{s.construction_type ?? "Тип не определён"}</p>
                  <p className="text-xs text-muted-foreground">{s.id.slice(0, 8)}…</p>
                </div>
                <StatusBadge status={s.status} />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    pending: "bg-gray-100 text-gray-700",
    queued: "bg-blue-50 text-blue-700",
    processing: "bg-yellow-50 text-yellow-700",
    completed: "bg-green-50 text-green-700",
    failed: "bg-red-50 text-red-700",
  };
  const labels: Record<string, string> = {
    pending: "Ожидание", queued: "В очереди",
    processing: "Обработка", completed: "Готово", failed: "Ошибка",
  };
  return (
    <span className={`text-xs rounded-full px-2 py-0.5 font-medium ${map[status] ?? map.pending}`}>
      {labels[status] ?? status}
    </span>
  );
}
