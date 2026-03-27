"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  getTopics, createTopic, updateTopic, deleteTopic, runTopicNow,
  getDigests, Topic, Digest,
} from "@/lib/api";

const FREQUENCY_LABELS: Record<string, string> = {
  hourly: "Every hour",
  daily:  "Daily at 8am",
  weekly: "Mondays at 8am",
};

const STATUS_STYLE: Record<string, string> = {
  sent:    "bg-green-100 text-green-700",
  failed:  "bg-red-100 text-red-700",
  pending: "bg-yellow-100 text-yellow-700",
};

export default function TopicsPage() {
  const [topics, setTopics] = useState<Topic[]>([]);
  const [selected, setSelected] = useState<Topic | null>(null);
  const [digests, setDigests] = useState<Digest[]>([]);
  const [previewDigest, setPreviewDigest] = useState<Digest | null>(null);

  // Form state
  const [name, setName] = useState("");
  const [query, setQuery] = useState("");
  const [frequency, setFrequency] = useState("daily");
  const [recipientsRaw, setRecipientsRaw] = useState("");
  const [saving, setSaving] = useState(false);
  const [triggering, setTriggering] = useState(false);

  useEffect(() => { refresh(); }, []);

  async function refresh() {
    try { setTopics(await getTopics()); } catch { /* backend offline */ }
  }

  async function loadDigests(topic: Topic) {
    setSelected(topic);
    setPreviewDigest(null);
    try { setDigests(await getDigests(topic.id)); } catch { setDigests([]); }
  }

  function startNew() {
    setSelected(null);
    setName(""); setQuery(""); setFrequency("daily"); setRecipientsRaw("");
    setDigests([]); setPreviewDigest(null);
  }

  function populateForm(t: Topic) {
    setName(t.name);
    setQuery(t.query);
    setFrequency(t.frequency);
    setRecipientsRaw(t.recipients.join(", "));
    loadDigests(t);
  }

  function parseEmails(raw: string): string[] {
    return raw.split(/[,\n]/).map(e => e.trim()).filter(Boolean);
  }

  async function handleSave() {
    const recipients = parseEmails(recipientsRaw);
    if (!name.trim() || !query.trim() || recipients.length === 0) return;
    setSaving(true);
    try {
      if (selected) {
        const updated = await updateTopic(selected.id, { name, query, frequency, recipients });
        setSelected(updated);
      } else {
        const created = await createTopic({ name, query, frequency, recipients });
        setSelected(created);
        loadDigests(created);
      }
      refresh();
    } finally { setSaving(false); }
  }

  async function handleToggleActive() {
    if (!selected) return;
    const updated = await updateTopic(selected.id, { is_active: !selected.is_active });
    setSelected(updated);
    refresh();
  }

  async function handleDelete() {
    if (!selected) return;
    await deleteTopic(selected.id);
    startNew();
    refresh();
  }

  async function handleRunNow() {
    if (!selected || triggering) return;
    setTriggering(true);
    await runTopicNow(selected.id);
    // Poll for new digest after a few seconds
    setTimeout(async () => {
      await loadDigests(selected);
      setTriggering(false);
    }, 3000);
  }

  return (
    <div className="flex h-screen bg-gray-50 text-gray-900">

      {/* ── Sidebar ─────────────────────────────── */}
      <aside className="w-64 flex-shrink-0 bg-white border-r border-gray-200 flex flex-col">
        <div className="px-4 py-5 border-b border-gray-100">
          <Link href="/" className="text-xs text-indigo-500 hover:underline">← Task Runner</Link>
          <h1 className="text-lg font-bold text-indigo-600 mt-1">Digest Topics</h1>
          <p className="text-xs text-gray-400">Scheduled AI email digests</p>
        </div>

        <div className="flex-1 overflow-y-auto px-2 py-3">
          {topics.length === 0 && (
            <p className="text-xs text-gray-400 text-center py-6">No topics yet</p>
          )}
          {topics.map((t) => (
            <button
              key={t.id}
              onClick={() => populateForm(t)}
              className={`w-full text-left px-3 py-3 rounded-lg mb-1 transition-colors
                ${selected?.id === t.id ? "bg-indigo-50 text-indigo-700" : "text-gray-600 hover:bg-gray-100"}`}
            >
              <div className="flex items-center justify-between">
                <span className="font-medium text-sm truncate">{t.name}</span>
                <span className={`w-2 h-2 rounded-full flex-shrink-0 ${t.is_active ? "bg-green-400" : "bg-gray-300"}`} />
              </div>
              <div className="text-xs text-gray-400 mt-0.5">{FREQUENCY_LABELS[t.frequency]}</div>
            </button>
          ))}
        </div>

        <div className="px-4 py-3 border-t border-gray-100">
          <button onClick={startNew} className="w-full text-sm text-indigo-600 hover:text-indigo-800 font-medium">
            + New Topic
          </button>
        </div>
      </aside>

      {/* ── Main ────────────────────────────────── */}
      <main className="flex-1 flex overflow-hidden">

        {/* Topic form */}
        <div className="w-96 flex-shrink-0 bg-white border-r border-gray-200 flex flex-col overflow-y-auto">
          <div className="px-5 py-4 border-b border-gray-100">
            <h2 className="font-semibold text-gray-800">{selected ? "Edit Topic" : "New Topic"}</h2>
          </div>

          <div className="px-5 py-4 space-y-4 flex-1">
            <div>
              <label className="text-xs font-medium text-gray-600 block mb-1">Topic Name</label>
              <input
                value={name}
                onChange={e => setName(e.target.value)}
                placeholder="e.g. AI Funding News"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
              />
            </div>

            <div>
              <label className="text-xs font-medium text-gray-600 block mb-1">Search Query</label>
              <textarea
                value={query}
                onChange={e => setQuery(e.target.value)}
                placeholder="e.g. latest AI startup funding rounds 2025 Australia"
                rows={3}
                className="w-full resize-none border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
              />
              <p className="text-xs text-gray-400 mt-1">Write it like a search query — be specific.</p>
            </div>

            <div>
              <label className="text-xs font-medium text-gray-600 block mb-1">Frequency</label>
              <select
                value={frequency}
                onChange={e => setFrequency(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
              >
                <option value="hourly">Every hour (testing)</option>
                <option value="daily">Daily at 8am UTC</option>
                <option value="weekly">Mondays at 8am UTC</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-medium text-gray-600 block mb-1">Recipients</label>
              <textarea
                value={recipientsRaw}
                onChange={e => setRecipientsRaw(e.target.value)}
                placeholder="you@gmail.com, team@company.com"
                rows={2}
                className="w-full resize-none border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
              />
              <p className="text-xs text-gray-400 mt-1">Comma or newline separated.</p>
            </div>
          </div>

          {/* Actions */}
          <div className="px-5 py-4 border-t border-gray-100 space-y-2">
            <button
              onClick={handleSave}
              disabled={saving || !name.trim() || !query.trim() || !recipientsRaw.trim()}
              className="w-full py-2 rounded-lg bg-indigo-600 text-white text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50"
            >
              {saving ? "Saving…" : selected ? "Save Changes" : "Create Topic"}
            </button>

            {selected && (
              <div className="flex gap-2">
                <button
                  onClick={handleRunNow}
                  disabled={triggering}
                  className="flex-1 py-1.5 rounded-lg border border-indigo-300 text-indigo-600 text-sm hover:bg-indigo-50 disabled:opacity-50"
                >
                  {triggering ? "Running…" : "▶ Run Now"}
                </button>
                <button
                  onClick={handleToggleActive}
                  className={`flex-1 py-1.5 rounded-lg border text-sm
                    ${selected.is_active
                      ? "border-gray-300 text-gray-600 hover:bg-gray-50"
                      : "border-green-300 text-green-600 hover:bg-green-50"}`}
                >
                  {selected.is_active ? "Pause" : "Resume"}
                </button>
                <button
                  onClick={handleDelete}
                  className="px-3 py-1.5 rounded-lg border border-red-300 text-red-600 text-sm hover:bg-red-50"
                >
                  ✕
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Digest history */}
        <div className="flex-1 flex flex-col overflow-hidden">

          {selected && (
            <div className="bg-white border-b border-gray-200 px-6 py-3 flex items-center gap-3">
              <h2 className="font-semibold text-gray-800">{selected.name}</h2>
              <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${selected.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                {selected.is_active ? "Active" : "Paused"}
              </span>
              <span className="text-xs text-gray-400">{FREQUENCY_LABELS[selected.frequency]}</span>
              {selected.last_run && (
                <span className="text-xs text-gray-400 ml-auto">
                  Last run: {new Date(selected.last_run).toLocaleString()}
                </span>
              )}
            </div>
          )}

          <div className="flex-1 flex overflow-hidden">

            {/* Digest list */}
            <div className="w-80 flex-shrink-0 border-r border-gray-200 overflow-y-auto bg-white">
              {!selected && (
                <div className="flex flex-col items-center justify-center h-full text-gray-400 p-8 text-center">
                  <span className="text-4xl mb-3">📬</span>
                  <p className="text-sm font-medium">Select a topic to see its digest history</p>
                </div>
              )}
              {selected && digests.length === 0 && (
                <div className="flex flex-col items-center justify-center h-full text-gray-400 p-8 text-center">
                  <span className="text-4xl mb-3">⏳</span>
                  <p className="text-sm font-medium">No digests yet</p>
                  <p className="text-xs mt-1">Click "Run Now" to generate the first one</p>
                </div>
              )}
              {digests.map(d => (
                <button
                  key={d.id}
                  onClick={() => setPreviewDigest(d)}
                  className={`w-full text-left px-4 py-3 border-b border-gray-100 hover:bg-gray-50 transition-colors
                    ${previewDigest?.id === d.id ? "bg-indigo-50" : ""}`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_STYLE[d.status]}`}>
                      {d.status}
                    </span>
                    <span className="text-xs text-gray-400">{new Date(d.created_at).toLocaleDateString()}</span>
                  </div>
                  <p className="text-sm font-medium text-gray-800 truncate">{d.subject}</p>
                  <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{d.summary}</p>
                </button>
              ))}
            </div>

            {/* Digest HTML preview */}
            <div className="flex-1 overflow-auto bg-gray-100 p-4">
              {previewDigest ? (
                <div className="bg-white rounded-xl shadow-sm overflow-hidden">
                  <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
                    <div>
                      <p className="text-xs text-gray-500">Subject</p>
                      <p className="font-medium text-gray-800 text-sm">{previewDigest.subject}</p>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="text-right">
                        <p className="text-xs text-gray-500">Sent to</p>
                        <p className="text-xs text-gray-600">{previewDigest.sent_to.join(", ") || "—"}</p>
                      </div>
                      <a
                        href={`/digest/${previewDigest.id}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="px-3 py-1.5 rounded-lg border border-indigo-300 text-indigo-600 text-xs hover:bg-indigo-50 flex-shrink-0"
                      >
                        ↗ Share
                      </a>
                    </div>
                  </div>
                  <iframe
                    srcDoc={previewDigest.html_content}
                    className="w-full border-0"
                    style={{ height: "600px" }}
                    title="Digest preview"
                  />
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-full text-gray-400">
                  <span className="text-4xl mb-3">📄</span>
                  <p className="text-sm">Select a digest to preview the email</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
