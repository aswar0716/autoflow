"use client";

import { useCallback } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  addEdge,
  useNodesState,
  useEdgesState,
  Connection,
  BackgroundVariant,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import ToolNode from "./ToolNode";
import { WorkflowNode, WorkflowEdge } from "@/lib/api";

const nodeTypes = { toolNode: ToolNode };

interface Props {
  initialNodes: WorkflowNode[];
  initialEdges: WorkflowEdge[];
  onChange: (nodes: WorkflowNode[], edges: WorkflowEdge[]) => void;
}

export default function WorkflowCanvas({ initialNodes, initialEdges, onChange }: Props) {
  const [nodes, setNodes, onNodesChange] = useNodesState(
    initialNodes.map((n) => ({ ...n, type: "toolNode" }))
  );
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  const onConnect = useCallback(
    (connection: Connection) => {
      setEdges((eds) => {
        const next = addEdge(connection, eds);
        onChange(nodes as WorkflowNode[], next as WorkflowEdge[]);
        return next;
      });
    },
    [nodes, setEdges, onChange]
  );

  // Notify parent whenever nodes move or edges change
  const handleNodesChange = useCallback(
    (changes: Parameters<typeof onNodesChange>[0]) => {
      onNodesChange(changes);
      // Use setTimeout so state has settled before we read nodes
      setTimeout(() => {
        setNodes((current) => {
          onChange(current as WorkflowNode[], edges as WorkflowEdge[]);
          return current;
        });
      }, 0);
    },
    [onNodesChange, setNodes, edges, onChange]
  );

  return (
    <div className="w-full h-full rounded-xl overflow-hidden border border-gray-200">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={handleNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        nodeTypes={nodeTypes}
        fitView
        deleteKeyCode="Backspace"
      >
        <Background variant={BackgroundVariant.Dots} gap={16} size={1} color="#e5e7eb" />
        <Controls />
        <MiniMap nodeColor={() => "#6366f1"} maskColor="rgba(0,0,0,0.05)" />
      </ReactFlow>
    </div>
  );
}
