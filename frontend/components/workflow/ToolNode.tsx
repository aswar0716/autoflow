"use client";

import { Handle, Position } from "@xyflow/react";

const TOOL_COLORS: Record<string, string> = {
  search:    "bg-blue-100 border-blue-400 text-blue-800",
  summarize: "bg-purple-100 border-purple-400 text-purple-800",
  email:     "bg-green-100 border-green-400 text-green-800",
  task:      "bg-indigo-100 border-indigo-400 text-indigo-800",
  result:    "bg-gray-100 border-gray-400 text-gray-700",
};

const TOOL_ICONS: Record<string, string> = {
  search:    "🔍",
  summarize: "📄",
  email:     "✉️",
  task:      "📝",
  result:    "✅",
};

interface ToolNodeData {
  label: string;
  toolName?: string;
  description?: string;
}

export default function ToolNode({ data }: { data: ToolNodeData }) {
  const key = data.toolName ?? "result";
  const colorClass = TOOL_COLORS[key] ?? "bg-white border-gray-300 text-gray-700";
  const icon = TOOL_ICONS[key] ?? "🔧";

  return (
    <div className={`rounded-xl border-2 px-4 py-3 shadow-sm min-w-[130px] text-center ${colorClass}`}>
      <Handle type="target" position={Position.Top} className="!bg-gray-400" />
      <div className="text-2xl mb-1">{icon}</div>
      <div className="font-semibold text-sm">{data.label}</div>
      {data.description && (
        <div className="text-xs mt-0.5 opacity-70">{data.description}</div>
      )}
      <Handle type="source" position={Position.Bottom} className="!bg-gray-400" />
    </div>
  );
}
