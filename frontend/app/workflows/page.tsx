"use client";

import { useEffect, useState, useCallback } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import {
  getTools, getWorkflows, createWorkflow, updateWorkflow, deleteWorkflow,
  runWorkflowStream,
  Tool, Workflow, WorkflowNode, WorkflowEdge, StepLog,
} from "@/lib/api";
import StepFeed from "@/components/StepFeed";

// Dynamically import the canvas (React Flow uses browser APIs — can't SSR)
const WorkflowCanvas = dynamic(
  () => import("@/components/workflow/WorkflowCanvas"),
  { ssr: false, loading: () => <div className="flex-1 flex items-center justify-center text-gray-400">Loading canvas…</div> }
);

// ─── Default canvas layout when creating a new workflow ──────────────────────
function defaultNodes(tools: string[]): WorkflowNode[] {
  const TOOL_DESCRIPTIONS: Record<string, string> = {
    search: "Search the web",
    summarize: "Summarize text",
    email: "Send email",
  };

  const nodes: WorkflowNode[] = [
    {
      id: "task",
      type: "toolNode",
      position: { x: 250, y: 0 },
      data: { label: "Task Input", toolName: "task", description: "Your task goes here" },
    },
  ];

  tools.forEach((tool, i) => {
    nodes.push({
      id: tool,
      type: "toolNode",
      position: { x: 100 + i * 200, y: 150 },
      data: { label: tool.charAt(0).toUpperCase() + tool.slice(1), toolName: tool, description: TOOL_DESCRIPTIONS[tool] ?? "" },
    });
  });

  nodes.push({
    id: "result",
    type: "toolNode",
    position: { x: 250, y: 320 },
    data: { label: "Result", toolName: "result", description: "Final answer" },
  });

  return nodes;
}

function defaultEdges(tools: string[]): WorkflowEdge[] {
  const edges: WorkflowEdge[] = tools.map((tool) => ({
    id: `task-${tool}`,
    source: "task",
    target: tool,
  }));
  tools.forEach((tool) => {
    edges.push({ id: `${tool}-result`, source: tool, target: "result" });
  });
  return edges;
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function WorkflowsPage() {
  const [tools, setTools] = useState<Tool[]>([]);
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [selected, setSelected] = useState<Workflow | null>(null);

  // Canvas state (synced from WorkflowCanvas child)
  const [canvasNodes, setCanvasNodes] = useState<WorkflowNode[]>([]);
  const [canvasEdges, setCanvasEdges] = useState<WorkflowEdge[]>([]);

  // Workflow form
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [selectedTools, setSelectedTools] = useState<string[]>([]);

  // Run panel
  const [taskInput, setTaskInput] = useState("");
  const [steps, setSteps] = useState<StepLog[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);

  // Panel toggle
  const [showRun, setShowRun] = useState(false);

  useEffect(() => {
    getTools().then(setTools).catch(console.error);
    refreshWorkflows();
  }, []);

  async function refreshWorkflows() {
    try { setWorkflows(await getWorkflows()); } catch { /* backend offline */ }
  }

  function selectWorkflow(w: Workflow) {
    setSelected(w);
    setName(w.name);
    setDescription(w.description);
    setSelectedTools(w.tools);
    setCanvasNodes(w.nodes);
    setCanvasEdges(w.edges);
    setSteps([]);
    setRunError(null);
    setShowRun(false);
  }

  function newWorkflow() {
    setSelected(null);
    setName("");
    setDescription("");
    setSelectedTools([]);
    setCanvasNodes([]);
    setCanvasEdges([]);
    setSteps([]);
    setRunError(null);
    setShowRun(false);
  }

  function toggleTool(toolName: string) {
    const next = selectedTools.includes(toolName)
      ? selectedTools.filter((t) => t !== toolName)
      : [...selectedTools, toolName];
    setSelectedTools(next);
    // Rebuild default canvas layout whenever tools change
    setCanvasNodes(defaultNodes(next));
    setCanvasEdges(defaultEdges(next));
  }

  const handleCanvasChange = useCallback((nodes: WorkflowNode[], edges: WorkflowEdge[]) => {
    setCanvasNodes(nodes);
    setCanvasEdges(edges);
  }, []);

  async function handleSave() {
    if (!name.trim() || selectedTools.length === 0) return;
    const payload = { name, description, tools: selectedTools, nodes: canvasNodes, edges: canvasEdges };
    if (selected) {
      const updated = await updateWorkflow(selected.id, payload);
      setSelected(updated);
    } else {
      const created = await createWorkflow(payload);
      setSelected(created);
    }
    refreshWorkflows();
  }

  async function handleDelete() {
    if (!selected) return;
    await deleteWorkflow(selected.id);
    newWorkflow();
    refreshWorkflows();
  }

  async function handleRun() {
    if (!selected || !taskInput.trim() || isRunning) return;
    setSteps([]);
    setRunError(null);
    setIsRunning(true);
    await runWorkflowStream(
      selected.id,
      taskInput,
      (step) => setSteps((prev) => [...prev, step]),
      () => setIsRunning(false),
      (msg) => { setRunError(msg); setIsRunning(false); }
    );
  }

  // Show canvas with current state (or rebuild when tools change)
  const canvasKey = selectedTools.join(",") + (selected?.id ?? "new");

  return (
    <div className="flex h-screen bg-gray-50 text-gray-900">

      {/* ── Sidebar ─────────────────────────────── */}
      <aside className="w-60 flex-shrink-0 bg-white border-r border-gray-200 flex flex-col">
        <div className="px-4 py-5 border-b border-gray-100">
          <Link href="/" className="text-xs text-indigo-500 hover:underline">← Task Runner</Link>
          <h1 className="text-lg font-bold text-indigo-600 mt-1">Workflows</h1>
          <p className="text-xs text-gray-400">Build & save agent workflows</p>
        </div>

        <div className="flex-1 overflow-y-auto px-2 py-3">
          {workflows.length === 0 && (
            <p className="text-xs text-gray-400 text-center py-4">No workflows yet</p>
          )}
          {workflows.map((w) => (
            <button
              key={w.id}
              onClick={() => selectWorkflow(w)}
              className={`w-full text-left px-3 py-2.5 rounded-lg text-sm mb-1 transition-colors
                ${selected?.id === w.id ? "bg-indigo-50 text-indigo-700 font-medium" : "text-gray-600 hover:bg-gray-100"}`}
            >
              <div className="font-medium truncate">{w.name}</div>
              <div className="text-xs text-gray-400">{w.tools.join(", ")}</div>
            </button>
          ))}
        </div>

        <div className="px-4 py-3 border-t border-gray-100">
          <button onClick={newWorkflow} className="w-full text-sm text-indigo-600 hover:text-indigo-800 font-medium">
            + New Workflow
          </button>
        </div>
      </aside>

      {/* ── Main ────────────────────────────────── */}
      <main className="flex-1 flex flex-col overflow-hidden">

        {/* Toolbar */}
        <div className="bg-white border-b border-gray-200 px-6 py-3 flex items-center gap-4">
          <div className="flex-1 flex items-center gap-3">
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Workflow name…"
              className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 w-48"
            />
            <input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Description (optional)"
              className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 w-64"
            />
          </div>

          <div className="flex items-center gap-2">
            {selected && (
              <button
                onClick={() => setShowRun(!showRun)}
                className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors
                  ${showRun ? "bg-indigo-600 text-white" : "border border-indigo-400 text-indigo-600 hover:bg-indigo-50"}`}
              >
                ▶ Run
              </button>
            )}
            <button
              onClick={handleSave}
              disabled={!name.trim() || selectedTools.length === 0}
              className="px-4 py-1.5 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 disabled:opacity-40"
            >
              {selected ? "Save" : "Create"}
            </button>
            {selected && (
              <button
                onClick={handleDelete}
                className="px-4 py-1.5 rounded-lg border border-red-300 text-red-600 text-sm hover:bg-red-50"
              >
                Delete
              </button>
            )}
          </div>
        </div>

        {/* Tool picker */}
        <div className="bg-white border-b border-gray-100 px-6 py-2 flex items-center gap-2">
          <span className="text-xs text-gray-500 font-medium mr-1">Tools:</span>
          {tools.map((tool) => {
            const active = selectedTools.includes(tool.name);
            return (
              <button
                key={tool.name}
                onClick={() => toggleTool(tool.name)}
                title={tool.description}
                className={`px-3 py-1 rounded-full text-xs font-medium border transition-all
                  ${active ? "bg-indigo-600 text-white border-indigo-600" : "bg-white text-gray-600 border-gray-300 hover:border-indigo-400"}`}
              >
                {tool.name}
              </button>
            );
          })}
          {selectedTools.length === 0 && (
            <span className="text-xs text-gray-400 ml-2">Select at least one tool to build a workflow</span>
          )}
        </div>

        {/* Canvas + Run panel */}
        <div className="flex-1 flex overflow-hidden">

          {/* React Flow canvas */}
          <div className="flex-1 p-4">
            {selectedTools.length > 0 ? (
              <WorkflowCanvas
                key={canvasKey}
                initialNodes={canvasNodes.length > 0 ? canvasNodes : defaultNodes(selectedTools)}
                initialEdges={canvasEdges.length > 0 ? canvasEdges : defaultEdges(selectedTools)}
                onChange={handleCanvasChange}
              />
            ) : (
              <div className="w-full h-full flex flex-col items-center justify-center text-gray-400 border-2 border-dashed border-gray-200 rounded-xl">
                <span className="text-5xl mb-3">🔧</span>
                <p className="text-sm font-medium">Select tools above to start building</p>
                <p className="text-xs mt-1">Each tool becomes a node you can drag and connect</p>
              </div>
            )}
          </div>

          {/* Run panel (slides in) */}
          {showRun && selected && (
            <div className="w-96 border-l border-gray-200 bg-white flex flex-col">
              <div className="px-4 py-3 border-b border-gray-100">
                <p className="text-sm font-semibold text-gray-700">Run: {selected.name}</p>
                <p className="text-xs text-gray-400 mt-0.5">Tools: {selected.tools.join(", ")}</p>
              </div>

              <div className="px-4 py-3 border-b border-gray-100 space-y-2">
                <textarea
                  value={taskInput}
                  onChange={(e) => setTaskInput(e.target.value)}
                  disabled={isRunning}
                  placeholder="Describe your task…"
                  rows={3}
                  className="w-full resize-none rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 disabled:opacity-60"
                />
                <button
                  onClick={handleRun}
                  disabled={isRunning || !taskInput.trim()}
                  className="w-full py-2 rounded-lg bg-indigo-600 text-white text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50"
                >
                  {isRunning ? "Running…" : "▶ Run Workflow"}
                </button>
              </div>

              <div className="flex-1 overflow-y-auto px-4 py-3">
                <StepFeed steps={steps} isRunning={isRunning} finalResult={null} error={runError} />
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
