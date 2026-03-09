"use client";

import { Task } from "@/lib/api";

interface Props {
  tasks: Task[];
  onSelect: (task: Task) => void;
  selectedId: number | null;
}

const STATUS_DOT: Record<string, string> = {
  completed: "bg-green-400",
  failed: "bg-red-400",
  running: "bg-yellow-400 animate-pulse",
  pending: "bg-gray-300",
};

export default function TaskHistory({ tasks, onSelect, selectedId }: Props) {
  if (tasks.length === 0) {
    return (
      <p className="text-sm text-gray-400 px-2 py-4 text-center">No tasks yet</p>
    );
  }

  return (
    <ul className="space-y-1">
      {tasks.map((task) => (
        <li key={task.id}>
          <button
            onClick={() => onSelect(task)}
            className={`w-full text-left px-3 py-2.5 rounded-lg text-sm transition-colors
              ${selectedId === task.id
                ? "bg-indigo-50 text-indigo-700 font-medium"
                : "text-gray-600 hover:bg-gray-100"
              }`}
          >
            <div className="flex items-center gap-2">
              <span className={`flex-shrink-0 w-2 h-2 rounded-full ${STATUS_DOT[task.status] ?? "bg-gray-300"}`} />
              <span className="truncate">{task.task}</span>
            </div>
            <div className="text-xs text-gray-400 mt-0.5 ml-4">
              {new Date(task.created_at).toLocaleString()}
            </div>
          </button>
        </li>
      ))}
    </ul>
  );
}
