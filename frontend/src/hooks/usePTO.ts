import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { PTOQuery, RegistryItem } from "@/types";

export function usePTOQuery(queryId: string | null) {
  return useQuery<PTOQuery>({
    queryKey: ["pto-query", queryId],
    queryFn: () => api.get(`/pto/queries/${queryId}`).then((r) => r.data),
    enabled: !!queryId,
    refetchInterval: (query) => {
      const s = query.state.data?.status;
      return s === "completed" || s === "failed" ? false : 2000;
    },
  });
}

export function useCreatePTOQuery() {
  return useMutation({
    mutationFn: ({ rawText, projectId }: { rawText: string; projectId?: string }) =>
      api.post("/pto/queries", { raw_text: rawText, project_id: projectId ?? null }).then((r) => r.data),
  });
}

export function useRegistrySearch(query: string) {
  return useQuery<RegistryItem[]>({
    queryKey: ["registry-search", query],
    queryFn: () => api.get("/pto/registry/search", { params: { q: query, limit: 20 } }).then((r) => r.data),
    enabled: query.length >= 2,
    staleTime: 30_000,
  });
}

export function useImportRegistry() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (file: File) => {
      const fd = new FormData();
      fd.append("file", file);
      return api.post("/pto/registry/import", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      }).then((r) => r.data);
    },
  });
}
