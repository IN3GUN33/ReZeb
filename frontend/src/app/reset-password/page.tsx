"use client";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { api } from "@/lib/api";

const schema = z.object({
  new_password: z.string().min(8, "Минимум 8 символов").max(128),
  confirm: z.string(),
}).refine((d) => d.new_password === d.confirm, {
  message: "Пароли не совпадают",
  path: ["confirm"],
});
type FormData = z.infer<typeof schema>;

function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  const onSubmit = async (data: FormData) => {
    try {
      await api.post("/auth/reset-password", {
        token,
        new_password: data.new_password,
      });
      router.push("/login?reset=success");
    } catch {
      setError("root", { message: "Ссылка недействительна или истекла. Запросите новую." });
    }
  };

  if (!token) {
    return (
      <div className="text-center space-y-4 p-8">
        <p className="text-sm text-destructive">Ссылка недействительна. Токен отсутствует.</p>
        <Link href="/forgot-password" className="text-sm text-primary hover:underline">
          Запросить новую ссылку
        </Link>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div>
        <label className="text-sm font-medium" htmlFor="new_password">Новый пароль</label>
        <input
          id="new_password"
          type="password"
          {...register("new_password")}
          className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          placeholder="Минимум 8 символов"
        />
        {errors.new_password && <p className="text-xs text-destructive mt-1">{errors.new_password.message}</p>}
      </div>

      <div>
        <label className="text-sm font-medium" htmlFor="confirm">Повторите пароль</label>
        <input
          id="confirm"
          type="password"
          {...register("confirm")}
          className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          placeholder="••••••••"
        />
        {errors.confirm && <p className="text-xs text-destructive mt-1">{errors.confirm.message}</p>}
      </div>

      {errors.root && (
        <div className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {errors.root.message}
        </div>
      )}

      <button
        type="submit"
        disabled={isSubmitting}
        className="w-full rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
      >
        {isSubmitting ? "Сохранение..." : "Установить новый пароль"}
      </button>
    </form>
  );
}

export default function ResetPasswordPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-muted/40 px-4">
      <div className="w-full max-w-sm rounded-xl border bg-card p-8 shadow-sm">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-primary">ReZeb</h1>
          <p className="text-sm text-muted-foreground mt-1">Установить новый пароль</p>
        </div>
        <Suspense fallback={<p className="text-sm text-muted-foreground">Загрузка...</p>}>
          <ResetPasswordForm />
        </Suspense>
        <p className="text-center text-sm text-muted-foreground mt-6">
          <Link href="/login" className="text-primary hover:underline">← Вернуться к входу</Link>
        </p>
      </div>
    </div>
  );
}
