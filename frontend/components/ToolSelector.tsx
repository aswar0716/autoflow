"use client";

import { Tool } from "@/lib/api";

interface Props {
  tools: Tool[];
  selected: string[];
  onChange: (selected: string[]) => void;
  disabled: boolean;
}

const ICONS: Record<string, string> = {
  search: "🔍",
  summarize: "📄",
  email: "✉️",
};

export default function ToolSelector({ tools, selected, onChange, disabled }: Props) {
  function toggle(name: string) {
    if (selected.includes(name)) {
      onChange(selected.filter((t) => t !== name));
    } else {
      onChange([...selected, name]);
    }
  }

  return (
    <div className="flex flex-wrap gap-2">
      {tools.map((tool) => {
        const active = selected.includes(tool.name);
        return (
          <button
            key={tool.name}
            onClick={() => toggle(tool.name)}
            disabled={disabled}
            title={tool.description}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium border transition-all
              ${active
                ? "bg-indigo-600 text-white border-indigo-600"
                : "bg-white text-gray-600 border-gray-300 hover:border-indigo-400"
              }
              ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}`}
          >
            <span>{ICONS[tool.name] ?? "🔧"}</span>
            {tool.name}
          </button>
        );
      })}
    </div>
  );
}
