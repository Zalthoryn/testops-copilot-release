import { useRef, useState, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import { checkStandards, getStandardsJob, downloadStandardsReport } from "../../services/api/standards";
import { useJobWatcher } from "../../hooks/useJobWatcher";
import { downloadBlob } from "../../utils/download";
import GlassCard from "../../components/common/GlassCard";
import GradientButton from "../../components/common/GradientButton";

const availableChecks = ["aaa", "allure", "naming", "documentation", "structure"];

// Типы для задач проверки стандартов
interface StandardsJobInfo {
  job_id: string;
  title: string;
  status: "pending" | "processing" | "completed" | "failed" | "cancelled";
  progress?: number;
  message?: string;
  files_count: number;
  checks: string[];
  created_at: string;
  violations_count?: number;
  result?: any[]; // Добавляем поле для результатов
}

const StandardsPage = () => {
  const [files, setFiles] = useState<File[]>([]);
  const [checks, setChecks] = useState<string[]>(["aaa", "allure", "naming"]);
  const [allJobs, setAllJobs] = useState<StandardsJobInfo[]>([]);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Загружаем сохраненные задачи при монтировании
  useEffect(() => {
    const savedJobs = localStorage.getItem("testops_standards_jobs");
    if (savedJobs) {
      try {
        setAllJobs(JSON.parse(savedJobs));
      } catch (e) {
        console.error("Ошибка загрузки задач проверки стандартов:", e);
      }
    }
  }, []);

  // Сохраняем задачи в localStorage
  useEffect(() => {
    localStorage.setItem("testops_standards_jobs", JSON.stringify(allJobs));
  }, [allJobs]);

  const mutation = useMutation({
    mutationFn: () => checkStandards(files, checks),
    onSuccess: (res) => {
      const newJob: StandardsJobInfo = {
        job_id: res.job_id,
        title: `Проверка ${files.length} файлов`,
        status: "pending",
        progress: 10,
        files_count: files.length,
        checks: [...checks],
        created_at: new Date().toISOString(),
      };
      setAllJobs(prev => [newJob, ...prev]);
    },
  });

  // Функция для обновления статуса задачи
  const updateJobStatus = (jobId: string, updates: Partial<StandardsJobInfo>) => {
    setAllJobs(prev => 
      prev.map(job => 
        job.job_id === jobId ? { ...job, ...updates } : job
      )
    );
  };

  // Функция для скачивания отчета
  const handleDownload = async (jobId: string) => {
    try {
      const blob = await downloadStandardsReport(jobId);
      downloadBlob(blob, `standards_report_${jobId}.html`);
    } catch (error) {
      console.error("Ошибка скачивания отчета:", error);
    }
  };

  // Функция для удаления задачи
  const removeJob = (jobId: string) => {
    setAllJobs(prev => prev.filter(job => job.job_id !== jobId));
  };

  return (
    <div className="grid" style={{ gap: 18 }}>
      <GlassCard padding="22px">
        <div style={{ display: "flex", flexWrap: "wrap", gap: 14, alignItems: "flex-start", justifyContent: "space-between" }}>
          <div style={{ display: "grid", gap: 6 }}>
            <div className="panelTitle">Проверка стандартов</div>
            <div className="panelHint">AAA, Allure, naming, structure. Загрузи файлы — получи отчёт.</div>
            <div className="chipRow tight">
              <span className="pillSoft">Паттерны</span>
              <span className="pillSoft">Документация</span>
              <span className="pillSoft">CI report</span>
            </div>
          </div>
          <span className="badge-soft" style={{ borderColor: "rgba(168,85,247,0.28)", background: "rgba(168,85,247,0.12)", color: "#e9d5ff" }}>
            LLM-assisted review
          </span>
        </div>

        <div className="grid two" style={{ gap: 16, marginTop: 14 }}>
          <GlassCard glow={false}>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                mutation.mutate();
              }}
              className="stack"
            >
              <div className="subCard" style={{ display: "grid", gap: 10 }}>
                <div className="fieldLabel">Файлы</div>
                <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
                  <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    onChange={(e) => setFiles(Array.from(e.target.files || []))}
                    style={{ display: "none" }}
                  />
                  <button
                    type="button"
                    className="pillSoft"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    Выбрать файлы
                  </button>
                  <span className="muted">
                    {files.length
                      ? files.slice(0, 2).map((f) => f.name).join(", ") + (files.length > 2 ? ` и еще ${files.length - 2}` : "")
                      : "Файл не выбран"}
                  </span>
                </div>
                <div className="subLabel">Можно загрузить несколько файлов одновременно.</div>
              </div>

              <div className="subCard" style={{ display: "grid", gap: 10 }}>
                <div className="fieldLabel">Проверки</div>
                <div className="chipRow">
                  {availableChecks.map((c) => (
                    <label key={c} className="chip">
                      <input
                        type="checkbox"
                        checked={checks.includes(c)}
                        onChange={() =>
                          setChecks((prev) => (prev.includes(c) ? prev.filter((x) => x !== c) : [...prev, c]))
                        }
                      />
                      {c}
                    </label>
                  ))}
                </div>
              </div>

              <GradientButton type="submit" disabled={mutation.isPending} style={{ marginTop: 4 }}>
                {mutation.isPending ? "Проверка..." : "Запустить проверку"}
              </GradientButton>
            </form>
          </GlassCard>

          <GlassCard glow={false}>
            <div className="panelTitle">Справка</div>
            <div className="panelHint">Что влияет на результаты.</div>
            <ul className="muted" style={{ marginTop: 10, paddingLeft: 16, display: "grid", gap: 6 }}>
              <li>AAA: сигнатуры тестов, понятные шаги, без дублирующих assert.</li>
              <li>Allure: аннотации, теги, привязка к story/feature.</li>
              <li>Naming: консистентность названий файлов и тестов.</li>
              <li>Structure: дерево каталогов и фикстуры.</li>
            </ul>
            <div className="divider" style={{ margin: "12px 0" }} />
            <div className="panelHint">Формат отчёта</div>
            <div className="muted" style={{ marginTop: 6 }}>
              HTML-отчёт с деталями по каждому чекеру, статусами и рекомендациями. Доступен после завершения job.
            </div>
          </GlassCard>
        </div>
      </GlassCard>

      {/* Список задач проверки стандартов */}
      {allJobs.length > 0 && (
        <GlassCard glow={false} style={{ border: "1px solid rgba(255,255,255,0.08)" }}>
          <div className="panelTitle">
            История проверок стандартов
            <span style={{ marginLeft: 8, fontSize: 14, color: "var(--text-secondary)" }}>
              ({allJobs.length})
            </span>
          </div>
          <div className="panelHint">Отслеживание статуса проверок и доступ к отчетам</div>
          
          <div style={{ marginTop: 16, display: "grid", gap: 12 }}>
            {allJobs.map((job) => (
              <StandardsJobItem
                key={job.job_id}
                job={job}
                onUpdate={(updates) => updateJobStatus(job.job_id, updates)}
                onDownload={() => handleDownload(job.job_id)}
                onRemove={() => removeJob(job.job_id)}
              />
            ))}
          </div>
        </GlassCard>
      )}
    </div>
  );
};

// Компонент для отображения одной задачи проверки стандартов
const StandardsJobItem = ({ 
  job, 
  onUpdate, 
  onDownload, 
  onRemove 
}: { 
  job: StandardsJobInfo; 
  onUpdate: (updates: Partial<StandardsJobInfo>) => void;
  onDownload: () => void;
  onRemove: () => void;
}) => {
  const { job: liveJob } = useJobWatcher(
    job.status !== "completed" && job.status !== "failed" ? job.job_id : null,
    getStandardsJob,
    () => {
      // Когда задача завершена
      if (liveJob) {
        // Безопасное получение количества нарушений
        const getViolationsCount = (job: any): number => {
          if (job.violations_count !== undefined) return job.violations_count;
          if (job.result?.violations?.length) return job.result.violations.length;
          if (job.violations?.length) return job.violations.length;
          return 0;
        };
        
        const violationsCount = getViolationsCount(liveJob);
        onUpdate({
          status: liveJob.status,
          progress: 100,
          violations_count: violationsCount,
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

  // const violationsCount = displayJob.violations_count || 0;

  const getViolationsCount = (job: any): number => {
    if (job.violations_count !== undefined) return job.violations_count;
    if (job.result?.violations?.length) return job.result.violations.length;
    if (job.violations?.length) return job.violations.length;
    return 0;
  };

  const violationsCount = getViolationsCount(displayJob);
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
        Job ID: {job.job_id.slice(0, 8)}... • Файлов: {job.files_count} • Проверок: {job.checks.length}
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

      {/* Результаты проверки */}
      {displayJob.status === "completed" && (
        <div style={{ 
          fontSize: 13, 
          padding: 8,
          background: violationsCount === 0 
            ? "rgba(34,197,94,0.1)" 
            : "rgba(251,191,36,0.1)",  // ← Должно быть для warnings
          borderRadius: 6,
          border: violationsCount === 0 
            ? "1px solid rgba(34,197,94,0.3)" 
            : "1px solid rgba(251,191,36,0.3)",
          marginBottom: 12
        }}>
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span style={{ 
                color: violationsCount === 0 ? "#22c55e" : "#fbbf24",
                fontWeight: 600 
              }}>
                {violationsCount === 0 ? "✅ Все стандарты соблюдены" : `⚠️ Нарушений: ${violationsCount}`}
              </span>
            </div>
          {job.checks.length > 0 && (
            <div className="muted" style={{ fontSize: 11, marginTop: 4 }}>
              Проверки: {job.checks.join(", ")}
            </div>
          )}
        </div>
      )}

      {/* Кнопки действий */}
      <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
        {displayJob.status === "completed" && (
          <GradientButton 
            onClick={onDownload} 
            style={{ padding: "6px 12px", fontSize: 12 }}
          >
            ⬇️ Скачать отчет
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
            <strong style={{ color: "#ef4444" }}>Ошибка проверки</strong>
          </div>
        )}
      </div>
    </div>
  );
};

export default StandardsPage;