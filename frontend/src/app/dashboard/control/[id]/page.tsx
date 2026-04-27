"use client";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Session, Defect } from "@/types";
import Link from "next/link";

function downloadJSON(data: unknown, filename: string) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function SeverityBadge({ severity }: { severity: string }) {
  const map: Record<string, { label: string; cls: string }> = {
    critical: { label: "Критический", cls: "bg-red-100 text-red-700 border-red-200" },
    significant: { label: "Значительный", cls: "bg-orange-100 text-orange-700 border-orange-200" },
    acceptable: { label: "Допустимый", cls: "bg-green-100 text-green-700 border-green-200" },
  };
  const { label, cls } = map[severity] ?? map.acceptable;
  return <span className={`text-xs rounded-full border px-2 py-0.5 font-medium ${cls}`}>{label}</span>;
}

function DefectCard({ defect }: { defect: Defect }) {
  return (
    <div className={`rounded-xl border p-4 space-y-2 ${
      defect.severity === "critical" ? "border-red-200 bg-red-50/50" :
      defect.severity === "significant" ? "border-orange-200 bg-orange-50/50" :
      "border-border bg-card"
    }`}>
      <div className="flex items-start justify-between gap-2">
        <div className="space-y-0.5">
          <p className="font-medium text-sm">{defect.defect_type.replace(/_/g, " ")}</p>
          {defect.measurement_mm != null && (
            <p className="text-xs text-muted-foreground">Размер: {defect.measurement_mm} мм</p>
          )}
        </div>
        <div className="flex flex-col items-end gap-1">
          <SeverityBadge severity={defect.severity} />
          <span className="text-xs text-muted-foreground">
            {Math.round(defect.confidence * 100)}% ув.
          </span>
        </div>
      </div>

      <p className="text-sm text-muted-foreground">{defect.description}</p>

      {defect.ntd_references.length > 0 && (
        <div className="rounded-lg bg-muted/60 p-2 space-y-1">
          <p className="text-xs font-medium text-muted-foreground">Нормативные ссылки:</p>
          {defect.ntd_references.map((ref, i) => (
            <div key={i} className="text-xs">
              <span className="font-mono font-medium">{ref.code}</span>
              {ref.clause && <span> п.{ref.clause}</span>}
              {ref.requirement && <span className="text-muted-foreground"> — {ref.requirement}</span>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function SessionDetailPage() {
  const { id } = useParams<{ id: string }>();

  const { data: session, isLoading } = useQuery<Session>({
    queryKey: ["session", id],
    queryFn: () => api.get(`/control/sessions/${id}`).then((r) => r.data),
    refetchInterval: (query) => {
      const s = query.state.data?.status;
      return s === "completed" || s === "failed" ? false : 3000;
    },
  });

  if (isLoading) {
    return <div className="text-sm text-muted-foreground">Загрузка...</div>;
  }
  if (!session) {
    return <div className="text-sm text-destructive">Сессия не найдена</div>;
  }

  const criticalCount = session.defects.filter((d) => d.severity === "critical").length;
  const significantCount = session.defects.filter((d) => d.severity === "significant").length;

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Link href="/dashboard/control" className="hover:text-primary">← К списку сессий</Link>
          </div>
          <h1 className="text-xl font-bold">
            {session.construction_type ?? "Тип конструкции не определён"}
          </h1>
          <p className="text-xs font-mono text-muted-foreground">{session.id}</p>
        </div>
        <div className="flex items-center gap-2">
          {session.status === "completed" && (
            <button
              onClick={async () => {
                const data = await api.get(`/control/sessions/${session.id}/export`).then((r) => r.data);
                downloadJSON(data, `rezeb-session-${session.id.slice(0, 8)}.json`);
              }}
              className="rounded-md border px-3 py-1.5 text-sm hover:bg-accent transition-colors"
            >
              Экспорт JSON
            </button>
          )}
          <StatusBadge status={session.status} />
        </div>
      </div>

      {/* Processing indicator */}
      {["pending", "queued", "processing"].includes(session.status) && (
        <div className="rounded-xl border bg-card p-4 flex items-center gap-3">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          <div>
            <p className="text-sm font-medium">Идёт анализ...</p>
            <p className="text-xs text-muted-foreground">YOLOv11 + Claude Sonnet 4.6</p>
          </div>
        </div>
      )}

      {/* Summary */}
      {session.status === "completed" && session.verdict && (
        <div className="rounded-xl border bg-card p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold">Сводка</h2>
            {session.escalated && (
              <span className="text-xs bg-purple-50 text-purple-700 rounded-full px-2 py-0.5 border border-purple-200">
                Эскалация → Opus 4.7
              </span>
            )}
          </div>

          {session.construction_type && (
            <div className="text-sm">
              <span className="text-muted-foreground">Тип конструкции: </span>
              <span className="font-medium">{session.construction_type}</span>
              {session.construction_type_confidence != null && (
                <span className="text-muted-foreground ml-1">
                  ({Math.round(session.construction_type_confidence * 100)}%)
                </span>
              )}
            </div>
          )}

          <p className="text-sm">{session.verdict.overall_assessment}</p>

          <div className="flex gap-3 flex-wrap">
            {criticalCount > 0 && (
              <span className="text-xs bg-red-50 text-red-700 rounded-full px-3 py-1 border border-red-200 font-medium">
                {criticalCount} критических
              </span>
            )}
            {significantCount > 0 && (
              <span className="text-xs bg-orange-50 text-orange-700 rounded-full px-3 py-1 border border-orange-200 font-medium">
                {significantCount} значительных
              </span>
            )}
            {session.defects.length === 0 && (
              <span className="text-xs bg-green-50 text-green-700 rounded-full px-3 py-1 border border-green-200 font-medium">
                Дефектов не выявлено
              </span>
            )}
          </div>

          {session.verdict.requires_immediate_action && (
            <div className="rounded-lg bg-red-50 border border-red-200 p-3 text-sm text-red-700 font-medium">
              ⚠️ Требуется немедленное устранение дефектов
            </div>
          )}

          <p className="text-xs text-muted-foreground italic">{session.verdict.disclaimer}</p>
        </div>
      )}

      {/* Error */}
      {session.status === "failed" && (
        <div className="rounded-xl border border-destructive/30 bg-destructive/5 p-4">
          <p className="text-sm text-destructive font-medium">Ошибка анализа</p>
          <p className="text-xs text-muted-foreground mt-1">{session.error_message}</p>
        </div>
      )}

      {/* Defects list */}
      {session.defects.length > 0 && (
        <div className="space-y-3">
          <h2 className="font-semibold">Выявленные дефекты ({session.defects.length})</h2>
          {/* Sort: critical first */}
          {[...session.defects]
            .sort((a, b) => {
              const order = { critical: 0, significant: 1, acceptable: 2 };
              return (order[a.severity] ?? 3) - (order[b.severity] ?? 3);
            })
            .map((d) => <DefectCard key={d.id} defect={d} />)
          }
        </div>
      )}

      {/* Photos */}
      {session.photos.length > 0 && (
        <div className="rounded-xl border bg-card p-5">
          <h2 className="font-semibold mb-3">Фотографии ({session.photos.length})</h2>
          <div className="grid grid-cols-2 gap-3">
            {session.photos.map((p) => (
              <div key={p.id} className="rounded-lg border p-2 space-y-1">
                <p className="text-xs font-medium truncate">{p.original_filename}</p>
                <div className="flex gap-2 text-xs text-muted-foreground flex-wrap">
                  {p.is_blurry && <span className="text-orange-600">⚠ Размыто</span>}
                  {p.has_aruco_marker && <span className="text-blue-600">📏 ArUco</span>}
                  {p.sharpness_score != null && (
                    <span>Резкость: {Math.round(p.sharpness_score)}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
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
    processing: "Обработка", completed: "Завершено", failed: "Ошибка",
  };
  return (
    <span className={`text-sm rounded-full px-3 py-1 font-medium ${map[status] ?? map.pending}`}>
      {labels[status] ?? status}
    </span>
  );
}
