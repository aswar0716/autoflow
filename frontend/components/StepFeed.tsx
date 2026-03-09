"use client";

import { StepLog } from "@/lib/api";

interface Props {
  steps: StepLog[];
  isRunning: boolean;
  finalResult: string | null;
  error: string | null;
}

const STEP_CONFIG = {
  tool_call: { icon: "⚙️", label: "Tool Call", bg: "bg-blue-50", border: "border-blue-200", text: "text-blue-800" },
  tool_result: { icon: "📨", label: "Result", bg: "bg-gray-50", border: "border-gray-200", text: "text-gray-700" },
  final: { icon: "✅", label: "Answer", bg: "bg-green-50", border: "border-green-200", text: "text-green-800" },
  start: { icon: "🚀", label: "Started", bg: "bg-indigo-50", border: "border-indigo-200", text: "text-indigo-800" },
  done: { icon: "✅", label: "Done", bg: "bg-green-50", border: "border-green-200", text: "text-green-800" },
  error: { icon: "❌", label: "Error", bg: "bg-red-50", border: "border-red-200", text: "text-red-800" },
};

export default function StepFeed({ steps, isRunning, finalResult, error }: Props) {
  if (steps.length === 0 && !isRunning && !finalResult && !error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-gray-400">
        <span className="text-5xl mb-3">🤖</span>
        <p className="text-sm">Describe a task above and hit Run</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {steps.map((step, i) => {
        const config = STEP_CONFIG[step.type] ?? STEP_CONFIG.tool_result;
        return (
          <div
            key={i}
            className={`rounded-lg border p-3 ${config.bg} ${config.border} animate-fadeIn`}
          >
            <div className="flex items-center gap-2 mb-1">
              <span>{config.icon}</span>
              <span className={`text-xs font-semibold uppercase tracking-wide ${config.text}`}>
                {step.tool_name ? `${config.label} — ${step.tool_name}` : config.label}
              </span>
              {step.step > 0 && (
                <span className="ml-auto text-xs text-gray-400">step {step.step}</span>
              )}
            </div>

            {step.tool_input && (
              <pre className="text-xs text-gray-500 bg-white/60 rounded p-2 mt-1 overflow-x-auto">
                {JSON.stringify(step.tool_input, null, 2)}
              </pre>
            )}

            <p className={`text-sm mt-1 whitespace-pre-wrap ${config.text}`}>
              {step.content}
            </p>
          </div>
        );
      })}

      {isRunning && (
        <div className="flex items-center gap-2 text-indigo-500 text-sm animate-pulse">
          <span className="inline-block w-2 h-2 rounded-full bg-indigo-500"></span>
          Agent is working…
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-red-700 text-sm">
          ❌ {error}
        </div>
      )}
    </div>
  );
}
