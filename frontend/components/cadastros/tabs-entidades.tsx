"use client";
import { cn } from "@/lib/utils";

export interface TabEntidade<T extends string> {
  key: T;
  label: string;
}

interface TabsEntidadesProps<T extends string> {
  tabs: TabEntidade<T>[];
  atual: T;
  onChange: (key: T) => void;
}

export function TabsEntidades<T extends string>({
  tabs,
  atual,
  onChange,
}: TabsEntidadesProps<T>) {
  return (
    <nav className="flex gap-0 overflow-x-auto">
      {tabs.map(({ key, label }) => (
        <button
          key={key}
          onClick={() => onChange(key)}
          className={cn(
            "px-4 py-2 text-sm font-medium border-b-2 border-transparent whitespace-nowrap",
            atual === key
              ? "text-slate-900 border-blue-500"
              : "text-slate-500 hover:text-slate-700"
          )}
        >
          {label}
        </button>
      ))}
    </nav>
  );
}
