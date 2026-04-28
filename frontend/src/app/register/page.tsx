"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";

const schema = z.object({
  full_name: z.string().min(2, "Минимум 2 символа").max(255),
  email: z.string().email("Введите корректный email"),
  password: z.string().min(8, "Минимум 8 символов").max(128),
  password_confirm: z.string(),
}).refine((d) => d.password === d.password_confirm, {
  message: "Пароли не совпадают",
  path: ["password_confirm"],
});
type FormData = z.infer<typeof schema>;

export default function RegisterPage() {
  const router = useRouter();
  const login = useAuthStore((s) => s.login);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  const onSubmit = async (data: FormData) => {
    try {
      await api.post("/auth/register", {
        email: data.email,
        password: data.password,
        full_name: data.full_name,
      });
      await login(data.email, data.password);
      router.push("/dashboard/control");
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Ошибка регистрации. Возможно, email уже занят.";
      setError("root", { message: msg });
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-muted/40 px-4">
      <div className="w-full max-w-sm rounded-xl border bg-card p-8 shadow-sm">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-primary">ReZeb</h1>
          <p className="text-sm text-muted-foreground mt-1">Создать аккаунт</p>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label className="text-sm font-medium" htmlFor="full_name">Имя и фамилия</label>
            <input
              id="full_name"
              type="text"
              {...register("full_name")}
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              placeholder="Иванов Иван"
            />
            {errors.full_name && <p className="text-xs text-destructive mt-1">{errors.full_name.message}</p>}
          </div>

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

          <div>
            <label className="text-sm font-medium" htmlFor="password">Пароль</label>
            <input
              id="password"
              type="password"
              {...register("password")}
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              placeholder="Минимум 8 символов"
            />
            {errors.password && <p className="text-xs text-destructive mt-1">{errors.password.message}</p>}
          </div>

          <div>
            <label className="text-sm font-medium" htmlFor="password_confirm">Повторите пароль</label>
            <input
              id="password_confirm"
              type="password"
              {...register("password_confirm")}
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              placeholder="••••••••"
            />
            {errors.password_confirm && <p className="text-xs text-destructive mt-1">{errors.password_confirm.message}</p>}
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
            {isSubmitting ? "Регистрация..." : "Зарегистрироваться"}
          </button>
        </form>

        <p className="text-center text-sm text-muted-foreground mt-6">
          Уже есть аккаунт?{" "}
          <Link href="/login" className="text-primary hover:underline font-medium">Войти</Link>
        </p>
      </div>
    </div>
  );
}
