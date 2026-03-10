"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { getTools, getTasks, runTaskStream, Task, Tool, StepLog } from "@/lib/api";
import ToolSelector from "@/components/ToolSelector";
import StepFeed from "@/components/StepFeed";
import TaskHistory from "@/components/TaskHistory";

export default function Home() {
  const [tools, setTools] = useState<Tool[]>([]);
  const [selectedTools, setSelectedTools] = useState<string[]>([]);
  const [taskInput, setTaskInput] = useState("");

  const [steps, setSteps] = useState<StepLog[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [finalResult, setFinalResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [history, setHistory] = useState<Task[]>([]);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);

  useEffect(() => {
    getTools().then(setTools).catch(console.error);
    refreshHistory();
  }, []);

  const refreshHistory = useCallback(async () => {
    try {
      const tasks = await getTasks();
      setHistory(tasks);
    } catch {
      // backend may not be running yet
    }
  }, []);

  function reset() {
    setSteps([]);
    setFinalResult(null);
    setError(null);
    setSelectedTask(null);
  }

  async function handleRun() {
    if (!taskInput.trim() || isRunning) return;
    reset();
    setIsRunning(true);

    const toolsToUse = selectedTools.length > 0 ? selectedTools : null;

    await runTaskStream(
      taskInput,
      toolsToUse,
      (step) => {
        setSteps((prev) => [...prev, step]);
        if (step.type === "final") setFinalResult(step.content);
      },
      async () => {
        setIsRunning(false);
        await refreshHistory();
      },
      (msg) => {
        setError(msg);
        setIsRunning(false);
      }
    );
  }

  function handleSelectHistory(task: Task) {
    setSelectedTask(task);
    setTaskInput(task.task);
    setSelectedTools(task.tools ?? []);
    setSteps(task.steps ?? []);
    setFinalResult(task.result);
    setError(task.error);
    setIsRunning(false);
  }

  const displaySteps = selectedTask ? (selectedTask.steps ?? []) : steps;
  const displayResult = selectedTask ? selectedTask.result : finalResult;
  const displayError = selectedTask ? selectedTask.error : error;

  return (
    <div className="flex h-screen bg-gray-50 text-gray-900">

      {/* Sidebar */}
      <aside className="w-64 flex-shrink-0 bg-white border-r border-gray-200 flex flex-col">
        <div className="px-4 py-5 border-b border-gray-100">
          <h1 className="text-lg font-bold text-indigo-600">AutoFlow</h1>
          <p className="text-xs text-gray-400 mt-0.5">AI Workflow Agent</p>
          <Link href="/workflows" className="text-xs text-indigo-500 hover:underline mt-1 inline-block">
            Workflow Builder →
          </Link>
        </div>

        <div className="flex-1 overflow-y-auto px-2 py-3">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider px-2 mb-2">
            Task History
          </p>
          <TaskHistory
            tasks={history}
            onSelect={handleSelectHistory}
            selectedId={selectedTask?.id ?? null}
          />
        </div>

        <div className="px-4 py-3 border-t border-gray-100">
          <button
            onClick={() => { reset(); setTaskInput(""); setSelectedTools([]); }}
            className="w-full text-sm text-indigo-600 hover:text-indigo-800 font-medium"
          >
            + New Task
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 flex flex-col overflow-hidden">

        {/* Input panel */}
        <div className="bg-white border-b border-gray-200 px-6 py-4 space-y-3">
          <textarea
            value={taskInput}
            onChange={(e) => setTaskInput(e.target.value)}
            disabled={isRunning}
            placeholder="Describe a task… e.g. Search for the latest AI news and summarise the top 3 stories"
            rows={3}
            className="w-full resize-none rounded-lg border border-gray-300 px-4 py-3 text-sm
              focus:outline-none focus:ring-2 focus:ring-indigo-400 disabled:opacity-60
              placeholder-gray-400"
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleRun();
            }}
          />

          <div className="flex items-center justify-between gap-4">
            <div className="flex-1">
              <p className="text-xs text-gray-500 mb-1.5">Tools (leave empty for all)</p>
              <ToolSelector
                tools={tools}
                selected={selectedTools}
                onChange={setSelectedTools}
                disabled={isRunning}
              />
            </div>

            <button
              onClick={handleRun}
              disabled={isRunning || !taskInput.trim()}
              className="flex-shrink-0 px-5 py-2.5 rounded-lg bg-indigo-600 text-white text-sm font-semibold
                hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isRunning ? "Running…" : "▶ Run"}
            </button>
          </div>

          <p className="text-xs text-gray-400">Tip: Ctrl+Enter to run</p>
        </div>

        {/* Step feed */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          <StepFeed
            steps={displaySteps}
            isRunning={isRunning && !selectedTask}
            finalResult={displayResult}
            error={displayError}
          />
        </div>
      </main>
    </div>
  );
}
