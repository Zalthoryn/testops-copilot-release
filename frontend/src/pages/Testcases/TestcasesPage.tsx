import { useState, useEffect } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  generateManualUI,
  generateManualAPI,
  getTestcaseJob,
  downloadTestcases,
} from "../../services/api/testcases";
import { useJobWatcher } from "../../hooks/useJobWatcher";
import { downloadBlob } from "../../utils/download";
import GlassCard from "../../components/common/GlassCard";
import GradientButton from "../../components/common/GradientButton";

const blocks = ["main_page", "product_catalog", "configuration", "management", "mobile"];
const sections = ["vms", "disks", "flavors", "other"];

// Типы для задач
interface JobInfo {
  job_id: string;
  type: "ui" | "api";
  title: string;
  status: "pending" | "processing" | "completed" | "failed" | "cancelled";
  progress?: number;
  testcases?: any[];
  message?: string; // Добавляем message
  created_at: string;
}

const TestcasesPage = () => {
  const [activeTab, setActiveTab] = useState<"ui" | "api">("ui");
  const [allJobs, setAllJobs] = useState<JobInfo[]>([]);
  const queryClient = useQueryClient();

  // Загружаем сохраненные задачи при монтировании
  useEffect(() => {
    const savedJobs = localStorage.getItem("testops_jobs");
    if (savedJobs) {
      try {
        setAllJobs(JSON.parse(savedJobs));
      } catch (e) {
        console.error("Ошибка загрузки задач:", e);
      }
    }
  }, []);

  // Сохраняем задачи в localStorage
  useEffect(() => {
    localStorage.setItem("testops_jobs", JSON.stringify(allJobs));
  }, [allJobs]);

  const uiMutation = useMutation({
    mutationFn: generateManualUI,
    onSuccess: (res) => {
      const newJob: JobInfo = {
        job_id: res.job_id,
        type: "ui",
        title: "UI кейсы",
        status: "pending",
        progress: 10,
        created_at: new Date().toISOString(),
      };
      setAllJobs(prev => [newJob, ...prev]);
    },
  });

  const apiMutation = useMutation({
    mutationFn: generateManualAPI,
    onSuccess: (res) => {
      const newJob: JobInfo = {
        job_id: res.job_id,
        type: "api",
        title: "API кейсы",
        status: "pending",
        progress: 10,
        created_at: new Date().toISOString(),
      };
      setAllJobs(prev => [newJob, ...prev]);
    },
  });

  // Функция для обновления статуса задачи
  const updateJobStatus = (jobId: string, updates: Partial<JobInfo>) => {
    setAllJobs(prev => 
      prev.map(job => 
        job.job_id === jobId ? { ...job, ...updates } : job
      )
    );
  };

  // Функция для скачивания
  const handleDownload = async (jobId: string, type: "ui" | "api") => {
    try {
      const blob = await downloadTestcases(jobId);
      downloadBlob(blob, `${type}_testcases_${jobId}.zip`);
    } catch (error) {
      console.error("Ошибка скачивания:", error);
    }
  };

  // Функция для удаления задачи из списка
  const removeJob = (jobId: string) => {
    setAllJobs(prev => prev.filter(job => job.job_id !== jobId));
  };

  // Фильтруем задачи по активной вкладке
  const filteredJobs = allJobs.filter(job => 
    activeTab === "ui" ? job.type === "ui" : job.type === "api"
  );

  return (
    <div className="grid" style={{ gap: 18 }}>
      <GlassCard padding="22px">
        <div style={{ display: "flex", flexWrap: "wrap", gap: 16, alignItems: "flex-start", justifyContent: "space-between" }}>
          <div style={{ display: "grid", gap: 6 }}>
            <div className="panelTitle">Генерация тест-кейсов</div>
            <div className="panelHint">Одним кликом — UI или API сценарии, готовые к скачиванию.</div>
            <div className="chipRow tight">
              <span className="pillSoft">LLM assist</span>
              <span className="pillSoft">Spec → Steps → Cases</span>
              <span className="pillSoft">Validation hints</span>
            </div>
          </div>
          <div className="pillTabs">
            <button className={`pill ${activeTab === "ui" ? "active" : ""}`} type="button" onClick={() => setActiveTab("ui")}>
              UI калькулятор
            </button>
            <button className={`pill ${activeTab === "api" ? "active" : ""}`} type="button" onClick={() => setActiveTab("api")}>
              API (OpenAPI)
            </button>
          </div>
        </div>
        <div className="divider" style={{ margin: "16px 0" }} />
        <div className="grid two" style={{ gap: 16 }}>
          <GlassCard glow={false}>
            {activeTab === "ui" ? (
              <UiForm onSubmit={(data) => uiMutation.mutate(data)} loading={uiMutation.isPending} />
            ) : (
              <ApiForm onSubmit={(data) => apiMutation.mutate(data)} loading={apiMutation.isPending} />
            )}
          </GlassCard>

          <GlassCard glow={false}>
            <div className="panelTitle">Шаги и критерии</div>
            <div className="panelHint">Быстрая сверка перед генерации.</div>
            <div className="stack" style={{ marginTop: 10 }}>
              <div className="metricRow">
                <span className="metricLabel">Шаг 1</span>
                <span className="metricValue">Опишите требования</span>
              </div>
              <div className="metricRow">
                <span className="metricLabel">Шаг 2</span>
                <span className="metricValue">Выберите блоки/секции</span>
              </div>
              <div className="metricRow">
                <span className="metricLabel">Шаг 3</span>
                <span className="metricValue">Задайте объём и приоритет</span>
              </div>
              <div className="metricRow">
                <span className="metricLabel">Готово</span>
                <span className="metricValue">Запустите генерацию</span>
              </div>
            </div>
            <div className="divider" style={{ margin: "12px 0" }} />
            <div className="panelHint">Советы</div>
            <ul className="muted" style={{ margin: "6px 0 0", paddingLeft: 16, display: "grid", gap: 6 }}>
              <li>Делите требования на краткие пункты — выше точность.</li>
              <li>Снимаете галки блоков — сокращаете объём.</li>
              <li>Для API используйте конкретный OpenAPI URL.</li>
            </ul>
          </GlassCard>
        </div>
      </GlassCard>

      {/* Список задач */}
      {filteredJobs.length > 0 && (
        <GlassCard glow={false} style={{ border: "1px solid rgba(255,255,255,0.08)" }}>
          <div className="panelTitle">
            {activeTab === "ui" ? "Задачи UI" : "Задачи API"} 
            <span style={{ marginLeft: 8, fontSize: 14, color: "var(--text-secondary)" }}>
              ({filteredJobs.length})
            </span>
          </div>
          <div className="panelHint">Отслеживание статуса генерации тест-кейсов</div>
          
          <div style={{ marginTop: 16, display: "grid", gap: 12 }}>
            {filteredJobs.map((job) => (
              <JobItem
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
    </div>
  );
};

// Компонент для отображения одной задачи
const JobItem = ({ 
  job, 
  onUpdate, 
  onDownload, 
  onRemove 
}: { 
  job: JobInfo; 
  onUpdate: (updates: Partial<JobInfo>) => void;
  onDownload: () => void;
  onRemove: () => void;
}) => {
  const { job: liveJob } = useJobWatcher(
    job.status !== "completed" && job.status !== "failed" ? job.job_id : null,
    getTestcaseJob,
    () => {
      // Когда задача завершена
      if (liveJob) {
        onUpdate({
          status: liveJob.status,
          progress: 100,
          testcases: liveJob.testcases || []
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

  // Получаем message безопасно
  const jobMessage = (liveJob as any)?.message || (job as any)?.message || 
    (displayJob.status === "processing" ? "Генерация тест-кейсов..." : "");

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

      {/* Сообщение и время */}
      {displayJob.status === "processing" && jobMessage && (
        <div className="muted" style={{ fontSize: 12, marginBottom: 8 }}>
          {jobMessage}
        </div>
      )}

      {/* Тест-кейсы */}
      {(displayJob as any).testcases?.length ? (
        <>
          <div className="muted" style={{ fontSize: 13, marginBottom: 8, color: "#22c55e" }}>
            ✅ Сгенерировано кейсов: {(displayJob as any).testcases.length}
          </div>
          <div style={{ maxHeight: 120, overflowY: "auto", marginBottom: 12 }}>
            {(displayJob as any).testcases.slice(0, 3).map((tc: any, index: number) => (
              <div key={tc.id || index} style={{ 
                fontSize: 11, 
                padding: "4px 6px", 
                background: "rgba(255,255,255,0.02)",
                borderRadius: 4,
                marginBottom: 4,
                borderLeft: "2px solid #3b82f6"
              }}>
                <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                  <span style={{ color: "#22c55e" }}>✓</span>
                  <span style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                    {tc.title}
                  </span>
                  <span className={`pillBadge ${tc.priority?.toLowerCase()}`} style={{ fontSize: 9 }}>
                    {tc.priority}
                  </span>
                </div>
              </div>
            ))}
            {(displayJob as any).testcases.length > 3 && (
              <div className="muted" style={{ fontSize: 10, textAlign: "center", padding: 4 }}>
                и еще {(displayJob as any).testcases.length - 3} кейсов...
              </div>
            )}
          </div>
        </>
      ) : displayJob.status === "completed" && (
        <div className="muted" style={{ fontSize: 13, marginBottom: 12, color: "#fbbf24" }}>
          ⚠️ Кейсы сгенерированы, но список недоступен
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
        
        {displayJob.status === "failed" && jobMessage && (
          <div style={{ 
            fontSize: 12, 
            padding: 6,
            background: "rgba(239,68,68,0.1)",
            borderRadius: 6,
            border: "1px solid rgba(239,68,68,0.3)",
            flex: 1
          }}>
            <strong style={{ color: "#ef4444" }}>Ошибка:</strong> {jobMessage}
          </div>
        )}
      </div>
    </div>
  );
};

type UiFormProps = {
  onSubmit: (data: any) => void;
  loading: boolean;
};

const UiForm = ({ onSubmit, loading }: UiFormProps) => {
  const [requirements, setReq] = useState("");
  const [selectedBlocks, setSelectedBlocks] = useState<string[]>(blocks);
  const [count, setCount] = useState(5);
  const [priority, setPriority] = useState("CRITICAL");

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit({
          requirements,
          test_blocks: selectedBlocks,
          target_count: count,
          priority,
        });
      }}
    >
      <div className="grid two" style={{ gap: 14, marginTop: 14 }}>
        <div className="subCard">
          <div className="fieldLabel">Требования</div>
          <textarea
            className="textarea"
            value={requirements}
            onChange={(e) => setReq(e.target.value)}
            required
            placeholder="Опишите цели, сценарии, крайние случаи..."
            style={{ minHeight: 150 }}
          />
        </div>
        <div className="subCard" style={{ display: "grid", gap: 12 }}>
          <div>
            <div className="fieldLabel">Блоки</div>
            <div className="chipRow">
              {blocks.map((b) => (
                <label key={b} className="chip">
                  <input
                    type="checkbox"
                    checked={selectedBlocks.includes(b)}
                    onChange={() =>
                      setSelectedBlocks((prev) =>
                        prev.includes(b) ? prev.filter((x) => x !== b) : [...prev, b],
                      )
                    }
                  />
                  {b}
                </label>
              ))}
            </div>
          </div>
          <div style={{ display: "grid", gap: 10, gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))" }}>
            <div>
              <div className="fieldLabel">Количество</div>
              <input
                className="input"
                type="number"
                value={count}
                onChange={(e) => setCount(Number(e.target.value))}
                min={1}
                max={100}
              />
            </div>
            <div>
              <div className="fieldLabel">Приоритет</div>
              <select className="select" value={priority} onChange={(e) => setPriority(e.target.value)}>
                <option value="CRITICAL">CRITICAL</option>
                <option value="NORMAL">NORMAL</option>
                <option value="LOW">LOW</option>
              </select>
            </div>
          </div>
        </div>
      </div>
      <GradientButton type="submit" disabled={loading} style={{ marginTop: 14 }}>
        {loading ? "Генерация..." : "Сгенерировать UI кейсы"}
      </GradientButton>
    </form>
  );
};

const ApiForm = ({
  onSubmit,
  loading,
}: {
  onSubmit: (data: any) => void;
  loading: boolean;
}) => {
  const [openapiUrl, setUrl] = useState("https://cloud.ru/docs/api/cdn/virtual-machines/ug/_specs/openapi-v3.yaml");
  const [selectedSections, setSections] = useState<string[]>(["vms", "disks", "flavors"]);
  const [count, setCount] = useState(5);

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit({
          openapi_url: openapiUrl,
          sections: selectedSections,
          target_count: count,
          auth_type: "bearer",
          priority: "NORMAL",
        });
      }}
    >
      <div className="grid two" style={{ gap: 14, marginTop: 14 }}>
        <div className="subCard" style={{ display: "grid", gap: 12 }}>
          <div>
            <div className="fieldLabel">OpenAPI URL</div>
            <input className="input" value={openapiUrl} onChange={(e) => setUrl(e.target.value)} required />
          </div>
          <div>
            <div className="fieldLabel">Количество</div>
            <input
              className="input"
              type="number"
              value={count}
              onChange={(e) => setCount(Number(e.target.value))}
              min={1}
              max={100}
            />
          </div>
        </div>
        <div className="subCard">
          <div className="fieldLabel">Секции</div>
          <div className="chipRow">
            {sections.map((s) => (
              <label key={s} className="chip">
                <input
                  type="checkbox"
                  checked={selectedSections.includes(s)}
                  onChange={() =>
                    setSections((prev) =>
                      prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s],
                    )
                  }
                />
                {s}
              </label>
            ))}
          </div>
        </div>
      </div>
      <GradientButton type="submit" disabled={loading} style={{ marginTop: 14 }}>
        {loading ? "Генерация..." : "Сгенерировать API кейсы"}
      </GradientButton>
    </form>
  );
};

export default TestcasesPage;