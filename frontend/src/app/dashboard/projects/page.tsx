"use client";
import { useState } from "react";
import { useProjects, useCreateProject, useDeleteProject } from "@/hooks/useProjects";
import { useToast } from "@/components/ui/toast";
import Link from "next/link";

export default function ProjectsPage() {
  const { data: projects = [], isLoading } = useProjects();
  const createProject = useCreateProject();
  const deleteProject = useDeleteProject();
  const { addToast } = useToast();

  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [location, setLocation] = useState("");

  const handleCreate = async () => {
    if (!name.trim()) return;
    try {
      await createProject.mutateAsync({ name, description: description || undefined, location: location || undefined });
      setName(""); setDescription(""); setLocation("");
      setShowForm(false);
      addToast("Проект создан", "success");
    } catch {
      addToast("Ошибка создания проекта", "error");
    }
  };

  const handleDelete = async (id: string, projectName: string) => {
    if (!confirm(`Удалить проект "${projectName}"?`)) return;
    try {
      await deleteProject.mutateAsync(id);
      addToast("Проект удалён", "success");
    } catch {
      addToast("Ошибка удаления проекта", "error");
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Проекты</h1>
          <p className="text-sm text-muted-foreground">Управление строительными объектами</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          {showForm ? "Отмена" : "+ Новый проект"}
        </button>
      </div>

      {showForm && (
        <div className="rounded-xl border bg-card p-6 space-y-4">
          <h2 className="font-semibold">Создать проект</h2>
          <div className="space-y-3">
            <div>
              <label className="text-sm font-medium">Название *</label>
              <input value={name} onChange={(e) => setName(e.target.value)}
                className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                placeholder="ЖК Северный берег, секция 3" />
            </div>
            <div>
              <label className="text-sm font-medium">Адрес / местоположение</label>
              <input value={location} onChange={(e) => setLocation(e.target.value)}
                className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                placeholder="г. Москва, ул. Северная, д. 15" />
            </div>
            <div>
              <label className="text-sm font-medium">Описание</label>
              <textarea value={description} onChange={(e) => setDescription(e.target.value)}
                rows={2} className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-none"
                placeholder="Монолитный жилой дом, 24 этажа..." />
            </div>
          </div>
          <button onClick={handleCreate}
            disabled={!name.trim() || createProject.isPending}
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50">
            {createProject.isPending ? "Создание..." : "Создать"}
          </button>
        </div>
      )}

      <div className="rounded-xl border bg-card p-6">
        {isLoading ? (
          <p className="text-sm text-muted-foreground">Загрузка...</p>
        ) : projects.length === 0 ? (
          <div className="text-center py-8">
            <div className="text-4xl mb-3">🏗️</div>
            <p className="text-sm text-muted-foreground">Проектов пока нет</p>
            <button onClick={() => setShowForm(true)}
              className="mt-3 text-sm text-primary underline underline-offset-2">
              Создать первый проект
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {projects.map((p) => (
              <div key={p.id} className="flex items-center justify-between rounded-lg border p-4 hover:bg-accent/30 transition-colors">
                <div className="space-y-0.5">
                  <p className="font-medium">{p.name}</p>
                  {p.location && <p className="text-xs text-muted-foreground">📍 {p.location}</p>}
                  {p.description && <p className="text-xs text-muted-foreground">{p.description}</p>}
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-xs rounded-full px-2 py-0.5 ${
                    p.status === "active" ? "bg-green-50 text-green-700" : "bg-gray-100 text-gray-600"
                  }`}>
                    {p.status === "active" ? "Активен" : p.status}
                  </span>
                  <button
                    onClick={() => handleDelete(p.id, p.name)}
                    className="text-xs text-muted-foreground hover:text-destructive transition-colors"
                  >
                    Удалить
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
