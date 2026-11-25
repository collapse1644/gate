"use client";

import { Eye, EyeOff, Save } from "lucide-react";
import { Suspense, useEffect, useState } from "react";

import { Card, ErrorNotice, Loading, Notice, PageHeader, SectionTitle } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import type { AppSettings, AIStatus } from "@/lib/types";

export default function SettingsPage() {
  return (
    <Suspense fallback={<Loading rows={3} />}>
      <SettingsInner />
    </Suspense>
  );
}

function SettingsInner() {
  const { data, loading, error, refresh } = useApi<{ settings: AppSettings; notes?: any }>("/settings");
  const { data: status } = useApi<AIStatus>("/ai/status");
  const [form, setForm] = useState<Partial<AppSettings>>({});
  const [apiKey, setApiKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveNotice, setSaveNotice] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<string | null>(null);
  const [testing, setTesting] = useState(false);

  useEffect(() => {
    if (data?.settings) setForm(data.settings);
  }, [data]);

  function set<K extends keyof AppSettings>(key: K, value: AppSettings[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function save() {
    setSaving(true);
    setSaveError(null);
    setSaveNotice(null);
    try {
      const values: Record<string, unknown> = { ...form };
      // Never send the masked gemini_api_key back from form state.
      delete (values as any).gemini_api_key;
      delete (values as any).gemini_api_key_set;
      if (apiKey.trim()) values.gemini_api_key = apiKey.trim();
      await api.put("/settings", { values });
      setApiKey("");
      setSaveNotice("Settings saved.");
      refresh();
    } catch (err) {
      setSaveError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  async function testGemini() {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await api.post<{ response: string; model: string; latency_ms: number }>("/ai/gemini/test", {
        prompt: "Reply with: Gemini connection OK",
      });
      setTestResult(`${res.model} (${res.latency_ms} ms): ${res.response}`);
    } catch (err) {
      setTestResult(`Error: ${errorMessage(err)}`);
    } finally {
      setTesting(false);
    }
  }

  if (loading) return <Loading rows={3} />;
  if (error) return <ErrorNotice message={error} onRetry={refresh} />;

  const s = form as AppSettings;

  return (
    <>
      <PageHeader
        eyebrow="Configuration"
        title="Settings"
        description="API keys are stored encrypted on this machine and never leave it. Local-only mode never contacts the cloud."
      />

      {saveError ? <div className="mb-4"><ErrorNotice message={saveError} onRetry={() => setSaveError(null)} /></div> : null}
      {saveNotice ? <div className="mb-4"><Notice tone="accent">{saveNotice}</Notice></div> : null}

      <div className="grid gap-5 xl:grid-cols-2">
        <Card>
          <SectionTitle title="AI routing" />
          <div className="space-y-3">
            <label className="block">
              <span className="label">AI mode</span>
              <select className="input" value={s.ai_mode ?? "auto"} onChange={(e) => set("ai_mode", e.target.value)}>
                <option value="auto">auto</option>
                <option value="gemini">gemini</option>
                <option value="local">local</option>
                <option value="local_only">local_only</option>
              </select>
              <span className="mt-1 block text-[11px] text-muted">local_only never contacts cloud providers.</span>
            </label>
            <label className="block">
              <span className="label">Preferred provider</span>
              <select className="input" value={s.preferred_provider ?? "gemini"} onChange={(e) => set("preferred_provider", e.target.value)}>
                <option value="gemini">gemini</option>
                <option value="local">local</option>
              </select>
            </label>
            <label className="inline-flex items-center gap-2 text-xs">
              <input type="checkbox" checked={Boolean(s.allow_auto_fallback)} onChange={(e) => set("allow_auto_fallback", e.target.checked)} className="h-3.5 w-3.5 accent-[var(--brand)]" />
              Allow auto fallback between providers
            </label>
            <label className="inline-flex items-center gap-2 text-xs">
              <input type="checkbox" checked={Boolean(s.cloud_consent)} onChange={(e) => set("cloud_consent", e.target.checked)} className="h-3.5 w-3.5 accent-[var(--brand)]" />
              Cloud consent (required for Gemini calls)
            </label>
          </div>
        </Card>

        <Card>
          <SectionTitle title="Gemini (cloud)" />
          <div className="space-y-3">
            <label className="block">
              <span className="label">Model</span>
              <input className="input" value={s.gemini_model ?? ""} onChange={(e) => set("gemini_model", e.target.value)} />
              <span className="mt-1 block text-[11px] text-muted">Default gemini-3.8-flash. Verify free-tier eligibility in Google AI Studio.</span>
            </label>
            <label className="block">
              <span className="label">API key {s.gemini_api_key_set ? "(set)" : "(not set)"}</span>
              <div className="relative">
                <input
                  type={showKey ? "text" : "password"}
                  className="input pr-9"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder={s.gemini_api_key_set ? "Leave blank to keep existing key" : "Paste Gemini API key"}
                />
                <button type="button" className="absolute right-2 top-1/2 -translate-y-1/2 text-muted" onClick={() => setShowKey((v) => !v)}>
                  {showKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              <span className="mt-1 block text-[11px] text-muted">Stored encrypted locally; never returned in full.</span>
            </label>
            <button type="button" className="btn-secondary btn-sm" onClick={testGemini} disabled={testing}>
              {testing ? "Testing…" : "Test Gemini connection"}
            </button>
            {testResult ? <p className="mt-2 text-[11px] text-muted">{testResult}</p> : null}
          </div>
        </Card>

        <Card>
          <SectionTitle title="Local model (llama.cpp CUDA)" />
          <div className="space-y-3">
            <label className="block">
              <span className="label">Base URL</span>
              <input className="input" value={s.local_base_url ?? ""} onChange={(e) => set("local_base_url", e.target.value)} />
            </label>
            <label className="block">
              <span className="label">Model path</span>
              <input className="input" value={s.local_model_path ?? ""} onChange={(e) => set("local_model_path", e.target.value)} />
            </label>
            <label className="block">
              <span className="label">mmproj path (vision)</span>
              <input className="input" value={s.local_mmproj_path ?? ""} onChange={(e) => set("local_mmproj_path", e.target.value)} />
            </label>
            <label className="block">
              <span className="label">Model label</span>
              <input className="input" value={s.local_model_label ?? ""} onChange={(e) => set("local_model_label", e.target.value)} />
            </label>
            <label className="block">
              <span className="label">Vision model label</span>
              <input className="input" value={s.local_vision_model_label ?? ""} onChange={(e) => set("local_vision_model_label", e.target.value)} />
            </label>
            <div className="grid grid-cols-2 gap-3">
              <label className="block">
                <span className="label">Context</span>
                <input className="input" type="number" value={s.local_context ?? 0} onChange={(e) => set("local_context", Number(e.target.value))} />
              </label>
              <label className="block">
                <span className="label">GPU layers</span>
                <input className="input" type="number" value={s.local_gpu_layers ?? 0} onChange={(e) => set("local_gpu_layers", Number(e.target.value))} />
              </label>
            </div>
            <label className="inline-flex items-center gap-2 text-xs">
              <input type="checkbox" checked={Boolean(s.local_auto_start)} onChange={(e) => set("local_auto_start", e.target.checked)} className="h-3.5 w-3.5 accent-[var(--brand)]" />
              Auto-start local server
            </label>
            <p className="text-[11px] text-muted">Status: {status?.local?.ready ? "ready" : "stopped"} · {status?.local?.health ? JSON.stringify(status.local.health) : ""}</p>
          </div>
        </Card>

        <Card>
          <SectionTitle title="Classification & mastery thresholds" />
          <div className="space-y-3">
            <label className="block">
              <span className="label">Review threshold</span>
              <input className="input" type="number" step="0.01" value={s.classification_review_threshold ?? 0.55} onChange={(e) => set("classification_review_threshold", Number(e.target.value))} />
            </label>
            <label className="block">
              <span className="label">Accept threshold</span>
              <input className="input" type="number" step="0.01" value={s.classification_accept_threshold ?? 0.72} onChange={(e) => set("classification_accept_threshold", Number(e.target.value))} />
            </label>
            <label className="block">
              <span className="label">Attribution policy</span>
              <input className="input" value={s.attribution_policy ?? ""} onChange={(e) => set("attribution_policy", e.target.value)} />
            </label>
            <label className="block">
              <span className="label">Backup retention</span>
              <input className="input" type="number" value={s.backup_retention ?? 0} onChange={(e) => set("backup_retention", Number(e.target.value))} />
            </label>
          </div>
        </Card>
      </div>

      <div className="mt-5 flex justify-end">
        <button className="btn-primary" onClick={save} disabled={saving}>
          <Save className="h-4 w-4" /> {saving ? "Saving…" : "Save settings"}
        </button>
      </div>
    </>
  );
}