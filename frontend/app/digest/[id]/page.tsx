import { notFound } from "next/navigation";
import { Metadata } from "next";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

interface DigestData {
  id: number;
  topic_id: number;
  topic_name: string;
  subject: string;
  summary: string;
  html_content: string;
  status: string;
  sent_to: string[];
  created_at: string;
}

async function fetchDigest(id: string): Promise<DigestData | null> {
  try {
    const res = await fetch(`${API_BASE}/digests/${id}`, { cache: "no-store" });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export async function generateMetadata(
  { params }: { params: Promise<{ id: string }> }
): Promise<Metadata> {
  const { id } = await params;
  const digest = await fetchDigest(id);
  if (!digest) return { title: "Digest not found" };
  return {
    title: digest.subject,
    description: digest.summary,
  };
}

export default async function DigestPage(
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const digest = await fetchDigest(id);
  if (!digest) notFound();

  const date = new Date(digest.created_at).toLocaleDateString("en-AU", {
    weekday: "long", year: "numeric", month: "long", day: "numeric",
  });

  return (
    <div className="min-h-screen bg-gray-50">

      {/* Top bar */}
      <div className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-indigo-600 font-bold text-sm">AutoFlow</span>
          <span className="text-gray-300">·</span>
          <span className="text-gray-500 text-sm">{digest.topic_name}</span>
        </div>
        <span className="text-xs text-gray-400">{date}</span>
      </div>

      {/* Email preview */}
      <div className="max-w-3xl mx-auto py-8 px-4">

        {/* Meta */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 mb-4">
          <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Subject</p>
          <h1 className="text-lg font-semibold text-gray-900">{digest.subject}</h1>
          {digest.summary && (
            <p className="mt-2 text-sm text-gray-600 leading-relaxed">{digest.summary}</p>
          )}
          <div className="mt-3 flex items-center gap-4 text-xs text-gray-400">
            <span
              className={`px-2 py-0.5 rounded-full font-medium
                ${digest.status === "sent" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}
            >
              {digest.status}
            </span>
            {digest.sent_to.length > 0 && (
              <span>Sent to {digest.sent_to.join(", ")}</span>
            )}
          </div>
        </div>

        {/* Rendered HTML email */}
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <iframe
            srcDoc={digest.html_content}
            className="w-full border-0"
            style={{ height: "700px" }}
            title={digest.subject}
          />
        </div>
      </div>
    </div>
  );
}
