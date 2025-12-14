import { useState, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import { analyzeOptimization, getOptimizationJob, downloadOptimized } from "../../services/api/optimization";
import { useJobWatcher } from "../../hooks/useJobWatcher";
import { downloadBlob } from "../../utils/download";
import GlassCard from "../../components/common/GlassCard";
import GradientButton from "../../components/common/GradientButton";

// Типы для задач оптимизации
interface OptimizationJobInfo {
  job_id: string;
  title: string;
  status: "pending" | "processing" | "completed" | "failed" | "cancelled";
  progress?: number;
  message?: string;
  checks: string[];
  repository_url?: string;
  created_at: string;
  recommendations_count?: number;
  result?: any[]; // Добавляем поле для результатов
}

const OptimizationPage = () => {
  const [repo, setRepo] = useState("");
  const [requirements, setRequirements] = useState("");
  const [checks, setChecks] = useState<string[]>(["duplicates", "coverage", "outdated"]);
  const [allJobs, setAllJobs] = useState<OptimizationJobInfo[]>([]);

  // Загружаем сохраненные задачи при монтировании
  useEffect(() => {
    const savedJobs = localStorage.getItem("testops_optimization_jobs");
    if (savedJobs) {
      try {
        setAllJobs(JSON.parse(savedJobs));
      } catch (e) {
        console.error("Ошибка загрузки задач оптимизации:", e);
      }
    }
  }, []);

  // Сохраняем задачи в localStorage
  useEffect(() => {
    localStorage.setItem("testops_optimization_jobs", JSON.stringify(allJobs));
  }, [allJobs]);

  const mutation = useMutation({
    mutationFn: () =>
      analyzeOptimization({
        repository_url: repo || null,
        requirements: requirements || null,
        checks,
        optimization_level: "moderate",
      }),
    onSuccess: (res) => {
      const newJob: OptimizationJobInfo = {
        job_id: res.job_id,
        title: repo ? `Оптимизация репозитория` : "Локальная оптимизация",
        status: "pending",
        progress: 10,
        checks: [...checks],
        repository_url: repo || undefined,
        created_at: new Date().toISOString(),
      };
      setAllJobs(prev => [newJob, ...prev]);
    },
  });

  // Функция для обновления статуса задачи
  const updateJobStatus = (jobId: string, updates: Partial<OptimizationJobInfo>) => {
    setAllJobs(prev => 
      prev.map(job => 
        job.job_id === jobId ? { ...job, ...updates } : job
      )
    );
  };

  // Функция для скачивания результатов
  const handleDownload = async (jobId: string) => {
    try {
      const blob = await downloadOptimized(jobId);
      downloadBlob(blob, `optimization_results_${jobId}.zip`);
    } catch (error) {
      console.error("Ошибка скачивания результатов:", error);
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
            <div className="panelTitle">Оптимизация тестов</div>
            <div className="panelHint">Поиск дублей, coverage и устаревших кейсов. Настрой фильтры и получи zip.</div>
            <div className="chipRow tight">
              <span className="pillSoft">Duplicates</span>
              <span className="pillSoft">Coverage</span>
              <span className="pillSoft">Outdated</span>
            </div>
          </div>
          <span className="badge-soft" style={{ borderColor: "rgba(34,211,238,0.3)", background: "rgba(34,211,238,0.1)", color: "#a5f3fc" }}>
            Drift & coverage
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
              <div className="grid two" style={{ gap: 12 }}>
                <div className="subCard" style={{ display: "grid", gap: 8 }}>
                  <div className="fieldLabel">Repo URL (опционально)</div>
                  <input className="input" value={repo} onChange={(e) => setRepo(e.target.value)} placeholder="https://gitlab.com/your/repo" />
                  <div className="subLabel">Если пусто, анализируется локальный контекст.</div>
                </div>
                <div className="subCard" style={{ display: "grid", gap: 8 }}>
                  <div className="fieldLabel">Требования (опционально)</div>
                  <textarea
                    className="textarea"
                    value={requirements}
                    onChange={(e) => setRequirements(e.target.value)}
                    placeholder="Критерии оптимизации, риски, области покрытия..."
                    style={{ minHeight: 120 }}
                  />
                </div>
              </div>

              <div className="subCard" style={{ display: "grid", gap: 10 }}>
                <div className="fieldLabel">Проверки</div>
                <div className="chipRow">
                  {["duplicates", "coverage", "outdated"].map((c) => (
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
                {mutation.isPending ? "Анализ..." : "Запустить анализ"}
              </GradientButton>
            </form>
          </GlassCard>

          <GlassCard glow={false}>
            <div className="panelTitle">Гид по улучшению</div>
            <div className="panelHint">На что смотреть в отчёте.</div>
            <div className="stack" style={{ marginTop: 10 }}>
              <div className="metricRow">
                <span className="metricLabel">Duplicates</span>
                <span className="metricValue">Сократить до уникальных</span>
              </div>
              <div className="metricRow">
                <span className="metricLabel">Coverage</span>
                <span className="metricValue">Заполнить критичные пробелы</span>
              </div>
              <div className="metricRow">
                <span className="metricLabel">Outdated</span>
                <span className="metricValue">Удалить или переписать</span>
              </div>
            </div>
            <div className="divider" style={{ margin: "12px 0" }} />
            <div className="panelHint">Результат</div>
            <div className="muted" style={{ marginTop: 6 }}>
              Zip с рекомендациями и метаданными. Каждая группа снабжена ссылками на строки/файлы, где найдено расхождение.
            </div>
          </GlassCard>
        </div>
      </GlassCard>

      {/* Список задач оптимизации */}
      {allJobs.length > 0 && (
        <GlassCard glow={false} style={{ border: "1px solid rgba(255,255,255,0.08)" }}>
          <div className="panelTitle">
            История оптимизации
            <span style={{ marginLeft: 8, fontSize: 14, color: "var(--text-secondary)" }}>
              ({allJobs.length})
            </span>
          </div>
          <div className="panelHint">Отслеживание статуса анализа и доступ к результатам</div>
          
          <div style={{ marginTop: 16, display: "grid", gap: 12 }}>
            {allJobs.map((job) => (
              <OptimizationJobItem
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

// Компонент для отображения одной задачи оптимизации
const OptimizationJobItem = ({ 
  job, 
  onUpdate, 
  onDownload, 
  onRemove 
}: { 
  job: OptimizationJobInfo; 
  onUpdate: (updates: Partial<OptimizationJobInfo>) => void;
  onDownload: () => void;
  onRemove: () => void;
}) => {
  const { job: liveJob } = useJobWatcher(
    job.status !== "completed" && job.status !== "failed" ? job.job_id : null,
    getOptimizationJob,
    () => {
      // Когда задача завершена
      if (liveJob) {
        // Безопасное получение количества рекомендаций
        const getRecommendationsCount = (job: any): number => {
          if (job.recommendations_count !== undefined) return job.recommendations_count;
          if (job.result?.recommendations?.length) return job.result.recommendations.length;
          if (job.recommendations?.length) return job.recommendations.length;
          return 0;
        };
        
        const recommendationsCount = getRecommendationsCount(liveJob);
        onUpdate({
          status: liveJob.status,
          progress: 100,
          recommendations_count: recommendationsCount,
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

  // Безопасное получение количества рекомендаций
  const getRecommendationsCount = (job: any): number => {
    if (job.recommendations_count !== undefined) return job.recommendations_count;
    if (job.result?.recommendations?.length) return job.result.recommendations.length;
    if (job.recommendations?.length) return job.recommendations.length;
    return 0;
  };

  const recommendationsCount = getRecommendationsCount(displayJob);

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
        Job ID: {job.job_id.slice(0, 8)}... • Проверок: {job.checks.length}
        {job.repository_url && (
          <> • Репозиторий: <span style={{ color: "#3b82f6" }}>{job.repository_url.substring(0, 30)}...</span></>
        )}
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

      {/* Результаты анализа */}
      {displayJob.status === "completed" && (
        <div style={{ 
          fontSize: 13, 
          padding: 8,
          background: "rgba(59,130,246,0.1)",
          borderRadius: 6,
          border: "1px solid rgba(59,130,246,0.3)",
          marginBottom: 12
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <span style={{ color: "#3b82f6", fontWeight: 600 }}>
              ✅ Анализ завершен
            </span>
          </div>
          {recommendationsCount > 0 && (
            <div className="muted" style={{ fontSize: 11, marginTop: 4 }}>
              Рекомендаций: {recommendationsCount} • Проверки: {job.checks.join(", ")}
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
            ⬇️ Скачать результаты
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
            <strong style={{ color: "#ef4444" }}>Ошибка анализа</strong>
          </div>
        )}
      </div>
    </div>
  );
};

export default OptimizationPage;