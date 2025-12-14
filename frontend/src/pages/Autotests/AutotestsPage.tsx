import { useState, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import {
  generateUIAutotests,
  generateAPIAutotests,
  getAutotestJob,
  downloadAutotests,
} from "../../services/api/autotests";
import { useJobWatcher } from "../../hooks/useJobWatcher";
import { downloadBlob } from "../../utils/download";
import GlassCard from "../../components/common/GlassCard";
import GradientButton from "../../components/common/GradientButton";

// Типы для задач автотестов
interface AutotestJobInfo {
  job_id: string;
  type: "ui" | "api";
  title: string;
  status: "pending" | "processing" | "completed" | "failed" | "cancelled";
  progress?: number;
  message?: string;
  created_at: string;
  result?: any[]; // Добавляем поле для результатов
}

const AutotestsPage = () => {
  const [activeTab, setActiveTab] = useState<"ui" | "api">("ui");
  const [allJobs, setAllJobs] = useState<AutotestJobInfo[]>([]);

  // Загружаем сохраненные задачи при монтировании
  useEffect(() => {
    const savedJobs = localStorage.getItem("testops_autotest_jobs");
    if (savedJobs) {
      try {
        setAllJobs(JSON.parse(savedJobs));
      } catch (e) {
        console.error("Ошибка загрузки задач автотестов:", e);
      }
    }
  }, []);

  // Сохраняем задачи в localStorage
  useEffect(() => {
    localStorage.setItem("testops_autotest_jobs", JSON.stringify(allJobs));
  }, [allJobs]);

  const uiMutation = useMutation({
    mutationFn: generateUIAutotests,
    onSuccess: (res) => {
      const newJob: AutotestJobInfo = {
        job_id: res.job_id,
        type: "ui",
        title: "UI автотесты (Playwright)",
        status: "pending",
        progress: 10,
        created_at: new Date().toISOString(),
      };
      setAllJobs(prev => [newJob, ...prev]);
    },
  });

  const apiMutation = useMutation({
    mutationFn: generateAPIAutotests,
    onSuccess: (res) => {
      const newJob: AutotestJobInfo = {
        job_id: res.job_id,
        type: "api",
        title: "API автотесты (pytest)",
        status: "pending",
        progress: 10,
        created_at: new Date().toISOString(),
      };
      setAllJobs(prev => [newJob, ...prev]);
    },
  });

  // Функция для обновления статуса задачи
  const updateJobStatus = (jobId: string, updates: Partial<AutotestJobInfo>) => {
    setAllJobs(prev => 
      prev.map(job => 
        job.job_id === jobId ? { ...job, ...updates } : job
      )
    );
  };

  // Функция для скачивания
  const handleDownload = async (jobId: string, type: "ui" | "api") => {
    try {
      const blob = await downloadAutotests(jobId);
      downloadBlob(blob, `${type}_autotests.zip`);
    } catch (error) {
      console.error("Ошибка скачивания автотестов:", error);
    }
  };

  // Функция для удаления задачи
  const removeJob = (jobId: string) => {
    setAllJobs(prev => prev.filter(job => job.job_id !== jobId));
  };

  // Фильтруем задачи по активной вкладке
  const filteredJobs = allJobs.filter(job => job.type === activeTab);

  return (
    <div className="grid" style={{ gap: 18 }}>
      {/* Существующая форма генерации автотестов (не трогаем) */}
      <GlassCard padding="22px">
        <div style={{ display: "flex", flexWrap: "wrap", gap: 16, alignItems: "flex-start", justifyContent: "space-between" }}>
          <div style={{ display: "grid", gap: 6 }}>
            <div className="panelTitle">Генерация автотестов</div>
            <div className="panelHint">UI e2e (Playwright) и API (pytest/httpx) в одном месте.</div>
            <div className="chipRow tight">
              <span className="pillSoft">Headless ready</span>
              <span className="pillSoft">Priority filter</span>
              <span className="pillSoft">LLM prompts tuned</span>
            </div>
          </div>
          <div className="pillTabs">
            <button className={`pill ${activeTab === "ui" ? "active" : ""}`} type="button" onClick={() => setActiveTab("ui")}>
              UI e2e
            </button>
            <button className={`pill ${activeTab === "api" ? "active" : ""}`} type="button" onClick={() => setActiveTab("api")}>
              API
            </button>
          </div>
        </div>
        <div className="divider" style={{ margin: "16px 0" }} />
        <div className="grid two" style={{ gap: 16 }}>
          <GlassCard glow={false}>
            {activeTab === "ui" ? (
              <UiAutotestForm onSubmit={(d) => uiMutation.mutate(d)} loading={uiMutation.isPending} />
            ) : (
              <ApiAutotestForm onSubmit={(d) => apiMutation.mutate(d)} loading={apiMutation.isPending} />
            )}
          </GlassCard>

          <GlassCard glow={false}>
            <div className="panelTitle">Тактика генерации</div>
            <div className="panelHint">Минимум шагов — максимум готовности.</div>
            <div className="stack" style={{ marginTop: 10 }}>
              <div className="metricRow">
                <span className="metricLabel">UI</span>
                <span className="metricValue">IDs + base URL + browsers</span>
              </div>
              <div className="metricRow">
                <span className="metricLabel">API</span>
                <span className="metricValue">IDs + OpenAPI + sections</span>
              </div>
              <div className="metricRow">
                <span className="metricLabel">Выход</span>
                <span className="metricValue">Zip с готовыми тестами</span>
              </div>
            </div>
            <div className="divider" style={{ margin: "12px 0" }} />
            <div className="panelHint">Советы</div>
            <ul className="muted" style={{ margin: "6px 0 0", paddingLeft: 16, display: "grid", gap: 6 }}>
              <li>UI: передавайте ID только критичных кейсов.</li>
              <li>API: уточняйте секции через запятую.</li>
              <li>Token опционален — но ускоряет доступ к приватке.</li>
            </ul>
          </GlassCard>
        </div>
      </GlassCard>

      {/* Список задач автотестов */}
      {filteredJobs.length > 0 && (
        <GlassCard glow={false} style={{ border: "1px solid rgba(255,255,255,0.08)" }}>
          <div className="panelTitle">
            {activeTab === "ui" ? "Задачи UI автотестов" : "Задачи API автотестов"} 
            <span style={{ marginLeft: 8, fontSize: 14, color: "var(--text-secondary)" }}>
              ({filteredJobs.length})
            </span>
          </div>
          <div className="panelHint">Отслеживание статуса генерации автотестов</div>
          
          <div style={{ marginTop: 16, display: "grid", gap: 12 }}>
            {filteredJobs.map((job) => (
              <AutotestJobItem
                key={job.job_id}
                job={job}
                onUpdate={(updates) => updateJobStatus(job.job_id, updates)}
                onDownload={() => handleDownload(job.job_id, job.type)}
                onRemove={() => removeJob(job.job_id)}
              />
            ))}
          </div>
        </GlassCard>
      )}

      {/* Существующие JobPanel для текущих задач (оставляем для обратной совместимости) */}
      <div className="grid two" style={{ gap: 16 }}>
        <JobPanel
          title="UI автотесты"
          job={null} // Будем использовать отдельные компоненты
          onDownload={() => {}}
        />
        <JobPanel
          title="API автотесты"
          job={null}
          onDownload={() => {}}
        />
      </div>
    </div>
  );
};

// Компонент для отображения одной задачи автотестов
const AutotestJobItem = ({ 
  job, 
  onUpdate, 
  onDownload, 
  onRemove 
}: { 
  job: AutotestJobInfo; 
  onUpdate: (updates: Partial<AutotestJobInfo>) => void;
  onDownload: () => void;
  onRemove: () => void;
}) => {
  const { job: liveJob } = useJobWatcher(
    job.status !== "completed" && job.status !== "failed" ? job.job_id : null,
    getAutotestJob,
    () => {
      // Когда задача завершена
      if (liveJob) {
        onUpdate({
          status: liveJob.status,
          progress: 100,
          result: (liveJob as any).result || []  // Используем result из ответа
        });
      }
    }
  );

  // Используем liveJob если есть, иначе локальные данные
  const displayJob = liveJob || job;
  const progress = displayJob.progress || 
    (displayJob.status === "completed" ? 100 : 
     displayJob.status === "processing" ? 50 : 
     displayJob.status === "pending" ? 10 : 0);

  // Получаем результат из job или liveJob
  const jobResult = (liveJob as any)?.result || job.result || [];

  return (
    <div style={{
      padding: 16,
      borderRadius: 12,
      background: "rgba(255,255,255,0.02)",
      border: "1px solid rgba(255,255,255,0.06)",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{ fontSize: 15, fontWeight: 600 }}>{job.title}</div>
          <span className={`pillBadge status ${displayJob.status}`} style={{ textTransform: "uppercase", fontSize: 11 }}>
            {displayJob.status}
          </span>
        </div>
        <button 
          onClick={onRemove}
          style={{ 
            background: "none", 
            border: "none", 
            color: "var(--text-secondary)", 
            cursor: "pointer",
            fontSize: 12,
            padding: "4px 8px"
          }}
        >
          × Удалить
        </button>
      </div>

      <div className="muted" style={{ fontSize: 12, marginBottom: 8 }}>
        Job ID: {job.job_id.slice(0, 8)}...
      </div>

      {/* Прогресс бар */}
      <div style={{ marginBottom: 12 }}>
        <div style={{ 
          display: "flex", 
          justifyContent: "space-between", 
          fontSize: 12,
          marginBottom: 4 
        }}>
          <span className="muted">Прогресс</span>
          <span>{progress}%</span>
        </div>
        <div style={{
          height: 8,
          background: "rgba(255,255,255,0.08)",
          borderRadius: 4,
          overflow: "hidden"
        }}>
          <div style={{
            width: `${progress}%`,
            height: "100%",
            background: displayJob.status === "completed" 
              ? "linear-gradient(90deg, #22c55e, #16a34a)" 
              : displayJob.status === "failed" 
                ? "linear-gradient(90deg, #ef4444, #dc2626)"
                : displayJob.status === "processing"
                ? "linear-gradient(90deg, #3b82f6, #1d4ed8)"
                : "linear-gradient(90deg, #94a3b8, #64748b)",
            transition: "width 0.3s ease"
          }} />
        </div>
      </div>

      {/* Информация о сгенерированных тестах */}
      {displayJob.status === "completed" && jobResult.length > 0 && (
        <div style={{ 
          fontSize: 13, 
          padding: 8,
          background: "rgba(34,197,94,0.1)",
          borderRadius: 6,
          border: "1px solid rgba(34,197,94,0.3)",
          marginBottom: 12
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <span style={{ color: "#22c55e", fontWeight: 600 }}>
              ✅ Сгенерировано автотестов: {jobResult.length}
            </span>
          </div>
        </div>
      )}

      {/* Кнопки действий */}
      <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
        {displayJob.status === "completed" && (
          <GradientButton 
            onClick={onDownload} 
            style={{ padding: "6px 12px", fontSize: 12 }}
          >
            ⬇️ Скачать ZIP
          </GradientButton>
        )}
        
        {displayJob.status === "failed" && (
          <div style={{ 
            fontSize: 12, 
            padding: 6,
            background: "rgba(239,68,68,0.1)",
            borderRadius: 6,
            border: "1px solid rgba(239,68,68,0.3)",
            flex: 1
          }}>
            <strong style={{ color: "#ef4444" }}>Ошибка генерации</strong>
          </div>
        )}
      </div>
    </div>
  );
};

const UiAutotestForm = ({ onSubmit, loading }: { onSubmit: (d: any) => void; loading: boolean }) => {
  const [ids, setIds] = useState("");
  const [baseUrl, setBaseUrl] = useState("https://cloud.ru/calculator");
  const [browsers, setBrowsers] = useState("chromium");

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit({
          manual_testcases_ids: ids.split(",").map((s) => s.trim()).filter(Boolean),
          framework: "playwright",
          browsers: browsers.split(",").map((s) => s.trim()).filter(Boolean),
          base_url: baseUrl,
          headless: true,
          priority_filter: ["CRITICAL", "NORMAL"],
        });
      }}
    >
      <div className="grid two" style={{ gap: 14, marginTop: 14 }}>
        <div className="subCard" style={{ display: "grid", gap: 10 }}>
          <div className="fieldLabel">UUID ручных кейсов (через запятую)</div>
          <input className="input" value={ids} onChange={(e) => setIds(e.target.value)} required placeholder="uuid-1, uuid-2, uuid-3" />
        </div>
        <div className="subCard" style={{ display: "grid", gap: 10 }}>
          <div className="fieldLabel">Браузеры</div>
          <input className="input" value={browsers} onChange={(e) => setBrowsers(e.target.value)} placeholder="chromium,webkit" />
          <div className="fieldLabel" style={{ marginTop: 6 }}>Base URL</div>
          <input className="input" value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} />
        </div>
      </div>
      <GradientButton type="submit" disabled={loading} style={{ marginTop: 14 }}>
        {loading ? "Генерация..." : "Сгенерировать UI автотесты"}
      </GradientButton>
    </form>
  );
};

const ApiAutotestForm = ({ onSubmit, loading }: { onSubmit: (d: any) => void; loading: boolean }) => {
  const [ids, setIds] = useState("");
  const [openapiUrl, setUrl] = useState("https://cloud.ru/docs/api/cdn/virtual-machines/ug/_specs/openapi-v3.yaml");
  const [sections, setSections] = useState("vms,disks,flavors");
  const [token, setToken] = useState("");

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit({
          manual_testcases_ids: ids.split(",").map((s) => s.trim()).filter(Boolean),
          openapi_url: openapiUrl,
          sections: sections.split(",").map((s) => s.trim()).filter(Boolean),
          base_url: "https://compute.api.cloud.ru",
          auth_token: token || null,
          test_framework: "pytest",
          http_client: "httpx",
        });
      }}
    >
      <div className="grid two" style={{ gap: 14, marginTop: 14 }}>
        <div className="subCard" style={{ display: "grid", gap: 10 }}>
          <div className="fieldLabel">UUID ручных кейсов (через запятую)</div>
          <input className="input" value={ids} onChange={(e) => setIds(e.target.value)} required />
          <div className="subLabel">Только завершённые кейсы попадут в отбор.</div>
        </div>
        <div className="subCard" style={{ display: "grid", gap: 10 }}>
          <div className="fieldLabel">OpenAPI URL</div>
          <input className="input" value={openapiUrl} onChange={(e) => setUrl(e.target.value)} required />
          <div className="fieldLabel">Секции</div>
          <input className="input" value={sections} onChange={(e) => setSections(e.target.value)} placeholder="vms,disks,flavors" />
          <div className="fieldLabel">Bearer token</div>
          <input className="input" value={token} onChange={(e) => setToken(e.target.value)} placeholder="опционально" />
        </div>
      </div>
      <GradientButton type="submit" disabled={loading} style={{ marginTop: 14 }}>
        {loading ? "Генерация..." : "Сгенерировать API автотесты"}
      </GradientButton>
    </form>
  );
};

const JobPanel = ({
  title,
  job,
  onDownload,
}: {
  title: string;
  job: any;
  onDownload: () => void;
}) => {
  if (!job) return null;
  return (
    <GlassCard
      glow={false}
      style={{
        border: "1px solid rgba(255,255,255,0.08)",
        boxShadow: "0 18px 50px rgba(0,0,0,0.5)",
      }}
    >
      <div className="section-title" style={{ alignItems: "center", gap: 10 }}>
        {title}
        <span className={`pillBadge status ${job.status}`} style={{ textTransform: "uppercase" }}>
          {job.status}
        </span>
      </div>
      <div className="muted" style={{ marginTop: 4, fontSize: 13 }}>Job ID: {job.job_id}</div>
      {job.status === "completed" && (
        <GradientButton variant="ghost" onClick={onDownload} style={{ marginTop: 10 }}>
          Скачать zip
        </GradientButton>
      )}
    </GlassCard>
  );
};

export default AutotestsPage;

