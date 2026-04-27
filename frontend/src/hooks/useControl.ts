import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Session } from "@/types";

export function useSessions(limit = 20) {
  return useQuery<Session[]>({
    queryKey: ["sessions", limit],
    queryFn: () => api.get("/control/sessions", { params: { limit } }).then((r) => r.data),
  });
}

export function useSession(sessionId: string | null) {
  return useQuery<Session>({
    queryKey: ["session", sessionId],
    queryFn: () => api.get(`/control/sessions/${sessionId}`).then((r) => r.data),
    enabled: !!sessionId,
    refetchInterval: (query) => {
      const s = query.state.data?.status;
      return s === "completed" || s === "failed" ? false : 3000;
    },
  });
}

export function useCreateSession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (projectId?: string) =>
      api.post("/control/sessions", { project_id: projectId ?? null }).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sessions"] }),
  });
}

export function useUploadPhoto(sessionId: string) {
  return useMutation({
    mutationFn: async (file: File) => {
      const fd = new FormData();
      fd.append("file", file);
      return api.post(`/control/sessions/${sessionId}/photos`, fd, {
        headers: { "Content-Type": "multipart/form-data" },
      }).then((r) => r.data);
    },
  });
}

export function useStartAnalysis() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (sessionId: string) =>
      api.post(`/control/sessions/${sessionId}/analyze`).then((r) => r.data),
    onSuccess: (_, sessionId) => {
      qc.invalidateQueries({ queryKey: ["session", sessionId] });
      qc.invalidateQueries({ queryKey: ["sessions"] });
    },
  });
}
