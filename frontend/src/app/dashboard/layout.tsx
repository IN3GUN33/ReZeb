"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/layout/Sidebar";
import { useAuthStore } from "@/stores/auth";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { accessToken, fetchMe, user } = useAuthStore();

  useEffect(() => {
    if (!accessToken) {
      router.replace("/login");
      return;
    }
    if (!user) fetchMe().catch(() => router.replace("/login"));
  }, [accessToken, user, router, fetchMe]);

  if (!accessToken) return null;

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-auto bg-muted/30 p-6">{children}</main>
    </div>
  );
}
