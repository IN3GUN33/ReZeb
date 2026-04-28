"use client";
import Link from "next/link";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { api } from "@/lib/api";

const schema = z.object({
  email: z.string().email("Введите корректный email"),
});
type FormData = z.infer<typeof schema>;

export default function ForgotPasswordPage() {
  const [sent, setSent] = useState(false);
  const [debugToken, setDebugToken] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  const onSubmit = async (data: FormData) => {
    const resp = await api.post("/auth/forgot-password", { email: data.email });
    if (resp.data.debug_token) {
      setDebugToken(resp.data.debug_token);
    }
    setSent(true);
  };

  if (sent) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-muted/40 px-4">
        <div className="w-full max-w-sm rounded-xl border bg-card p-8 shadow-sm text-center space-y-4">
          <div className="text-4xl">📧</div>
          <h2 className="text-lg font-semibold">Письмо отправлено</h2>
          <p className="text-sm text-muted-foreground">
            Если аккаунт с таким email существует, вы получите инструкции по сбросу пароля.
          </p>
          {debugToken && (
            <div className="rounded-lg bg-yellow-50 border border-yellow-200 p-3 text-left">
              <p className="text-xs font-medium text-yellow-800">DEV: токен сброса</p>
              <p className="text-xs font-mono break-all mt-1 text-yellow-700">{debugToken}</p>
              <Link
                href={`/reset-password?token=${debugToken}`}
                className="text-xs text-primary hover:underline mt-2 block"
              >
                → Перейти к сбросу пароля
              </Link>
            </div>
          )}
          <Link href="/login" className="text-sm text-primary hover:underline">← Вернуться к входу</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-muted/40 px-4">
      <div className="w-full max-w-sm rounded-xl border bg-card p-8 shadow-sm">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-primary">ReZeb</h1>
          <p className="text-sm text-muted-foreground mt-1">Сброс пароля</p>
        </div>

        <p className="text-sm text-muted-foreground mb-4">
          Введите email вашего аккаунта. Мы пришлём ссылку для сброса пароля.
        </p>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label className="text-sm font-medium" htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              {...register("email")}
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              placeholder="you@company.ru"
            />
            {errors.email && <p className="text-xs text-destructive mt-1">{errors.email.message}</p>}
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
          >
            {isSubmitting ? "Отправка..." : "Отправить инструкции"}
          </button>
        </form>

        <p className="text-center text-sm text-muted-foreground mt-6">
          <Link href="/login" className="text-primary hover:underline">← Вернуться к входу</Link>
        </p>
      </div>
    </div>
  );
}
