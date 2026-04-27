"use client";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useAuthStore } from "@/stores/auth";

const schema = z.object({
  email: z.string().email("Введите корректный email"),
  password: z.string().min(8, "Минимум 8 символов"),
});
type FormData = z.infer<typeof schema>;

export default function LoginPage() {
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
      await login(data.email, data.password);
      router.push("/dashboard/control");
    } catch {
      setError("root", { message: "Неверный email или пароль" });
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-muted/40 px-4">
      <div className="w-full max-w-sm rounded-xl border bg-card p-8 shadow-sm">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-primary">ReZeb</h1>
          <p className="text-sm text-muted-foreground mt-1">AI-платформа строительного контроля</p>
        </div>

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

          <div>
            <label className="text-sm font-medium" htmlFor="password">Пароль</label>
            <input
              id="password"
              type="password"
              {...register("password")}
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              placeholder="••••••••"
            />
            {errors.password && <p className="text-xs text-destructive mt-1">{errors.password.message}</p>}
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
            {isSubmitting ? "Вход..." : "Войти"}
          </button>
        </form>
      </div>
    </div>
  );
}
