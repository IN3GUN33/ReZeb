import { create } from "zustand";
import { persist } from "zustand/middleware";
import { api } from "@/lib/api";

interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
}

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  fetchMe: () => Promise<void>;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,

      async login(email, password) {
        const resp = await api.post("/auth/login", { email, password });
        const { access_token, refresh_token } = resp.data;
        localStorage.setItem("access_token", access_token);
        localStorage.setItem("refresh_token", refresh_token);
        set({ accessToken: access_token, refreshToken: refresh_token });
        await get().fetchMe();
      },

      async logout() {
        const { refreshToken } = get();
        if (refreshToken) {
          try {
            await api.post("/auth/logout", { refresh_token: refreshToken });
          } catch {}
        }
        localStorage.clear();
        set({ user: null, accessToken: null, refreshToken: null });
      },

      async fetchMe() {
        const resp = await api.get("/auth/me");
        set({ user: resp.data });
      },
    }),
    { name: "rezeb-auth", partialize: (s) => ({ accessToken: s.accessToken, refreshToken: s.refreshToken }) }
  )
);
