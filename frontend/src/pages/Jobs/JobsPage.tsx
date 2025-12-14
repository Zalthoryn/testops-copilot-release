import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { listAllJobs } from "../../services/api/jobs";
import GlassCard from "../../components/common/GlassCard";
import GradientButton from "../../components/common/GradientButton";
import { Link } from "react-router-dom";

// Маппинг типов задач на читаемые названия
const jobTypeMapping: Record<string, string> = {
  "manual_ui": "UI тест-кейсы",
  "manual_api": "API тест-кейсы", 
  "autotest_ui": "UI автотесты",
  "autotest_api": "API автотесты",
  "standards_check": "Проверка стандартов",
  "optimization": "Оптимизация"
};

// Маппинг статусов на русский
const statusMapping: Record<string, string> = {
  "pending": "В ожидании",
  "processing": "В процессе",
  "completed": "Завершено",
  "failed": "Ошибка",
  "cancelled": "Отменено"
};

const JobsPage = () => {
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [limit, setLimit] = useState<number>(20);

  const { data: jobs, isLoading, refetch } = useQuery({
    queryKey: ["all-jobs", typeFilter, statusFilter, limit],
    queryFn: () => listAllJobs({
      job_type: typeFilter !== "all" ? typeFilter : undefined,
      status: statusFilter !== "all" ? statusFilter : undefined,
      limit
    }),
    refetchInterval: 3000,
  });

  // Подсчет статистики
  const getStats = () => {
    if (!jobs) return {};
    
    const stats: Record<string, number> = {
      all: jobs.length,
      pending: 0,
      processing: 0,
      completed: 0,
      failed: 0
    };
    
    const typeStats: Record<string, number> = {};
    
    jobs.forEach(job => {
      // Статистика по статусам
      if (job.status in stats) {
        stats[job.status]++;
      }
      
      // Статистика по типам
      const type = job.type || "unknown";
      typeStats[type] = (typeStats[type] || 0) + 1;
    });
    
    return { statusStats: stats, typeStats };
  };

  const { statusStats = {}, typeStats = {} } = getStats();

  return (
    <div className="grid" style={{ gap: 20 }}>
      <GlassCard padding="24px">
        <div style={{ display: "flex", flexWrap: "wrap", gap: 16, alignItems: "center", justifyContent: "space-between" }}>
          <div>
            <div className="panelTitle">Все задачи</div>
            <div className="panelHint">Мониторинг всех типов задач: тест-кейсы, автотесты, проверки, оптимизация</div>
          </div>
          <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
            <GradientButton variant="ghost" onClick={() => refetch()}>
              Обновить
            </GradientButton>
          </div>
        </div>

        {/* Фильтры */}
        <div className="grid three" style={{ gap: 12, marginTop: 20 }}>
          <div className="subCard">
            <div className="fieldLabel">Тип задачи</div>
            <select 
              className="select" 
              value={typeFilter} 
              onChange={(e) => setTypeFilter(e.target.value)}
            >
              <option value="all">Все типы ({jobs?.length || 0})</option>
              {Object.entries(typeStats).map(([type, count]) => (
                <option key={type} value={type}>
                  {jobTypeMapping[type] || type} ({count})
                </option>
              ))}
            </select>
          </div>
          
          <div className="subCard">
            <div className="fieldLabel">Статус</div>
            <select 
              className="select" 
              value={statusFilter} 
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="all">Все статусы ({statusStats.all || 0})</option>
              <option value="pending">В ожидании ({statusStats.pending || 0})</option>
              <option value="processing">В процессе ({statusStats.processing || 0})</option>
              <option value="completed">Завершено ({statusStats.completed || 0})</option>
              <option value="failed">Ошибка ({statusStats.failed || 0})</option>
            </select>
          </div>
          
          <div className="subCard">
            <div className="fieldLabel">Показать</div>
            <select 
              className="select" 
              value={limit} 
              onChange={(e) => setLimit(Number(e.target.value))}
            >
              <option value={10}>10 задач</option>
              <option value={20}>20 задач</option>
              <option value={50}>50 задач</option>
              <option value={100}>100 задач</option>
            </select>
          </div>
        </div>

        {isLoading ? (
          <div className="muted" style={{ textAlign: "center", padding: 40 }}>
            Загрузка задач...
          </div>
        ) : !jobs?.length ? (
          <div className="muted" style={{ textAlign: "center", padding: 40 }}>
            Нет задач
          </div>
        ) : (
          <div className="table-wrapper" style={{ marginTop: 20, overflowX: "auto" }}>
            <table className="table">
              <thead>
                <tr>
                  <th>ID задачи</th>
                  <th>Тип</th>
                  <th>Статус</th>
                  <th>Прогресс</th>
                  <th>Создано</th>
                  <th>Обновлено</th>
                  <th>Действия</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <tr key={job.job_id}>
                    <td>
                      <code style={{ fontSize: 12 }}>{job.job_id.slice(0, 8)}...</code>
                    </td>
                    <td>
                      <span className="pillSoft">
                        {jobTypeMapping[job.type as string] || job.type || "Неизвестно"}
                      </span>
                    </td>
                    <td>
                      <span className={`pillBadge status ${job.status}`}>
                        {statusMapping[job.status] || job.status}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <div style={{
                          width: 60,
                          height: 6,
                          background: "rgba(255,255,255,0.1)",
                          borderRadius: 3,
                          overflow: "hidden"
                        }}>
                          <div style={{
                            width: `${job.progress || 0}%`,
                            height: "100%",
                            background: job.status === "completed" 
                              ? "linear-gradient(90deg, #22c55e, #16a34a)" 
                              : job.status === "failed" 
                                ? "linear-gradient(90deg, #ef4444, #dc2626)"
                                : "linear-gradient(90deg, #3b82f6, #1d4ed8)",
                          }} />
                        </div>
                        <span style={{ fontSize: 12 }}>{job.progress || 0}%</span>
                      </div>
                    </td>
                    <td className="muted">
                      {new Date(job.created_at).toLocaleString("ru-RU")}
                    </td>
                    <td className="muted">
                      {job.updated_at ? new Date(job.updated_at).toLocaleString("ru-RU") : "-"}
                    </td>
                    <td>
                      <Link to={`/jobs/${job.job_id}`}>
                        <GradientButton variant="ghost" style={{ padding: "6px 12px", fontSize: 12 }}>
                          Детали
                        </GradientButton>
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 20 }}>
          <div className="muted">
            Показано {Math.min(jobs?.length || 0, limit)} из {jobs?.length || 0} задач
          </div>
        </div>
      </GlassCard>
    </div>
  );
};

export default JobsPage;