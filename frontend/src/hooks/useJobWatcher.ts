import { useState, useCallback } from "react";
import { usePolling } from "./usePolling";
import { JobStatus } from "../types/api";

type BaseJob = {
  job_id: string;
  status: JobStatus;
  message?: string | null;
  estimated_time?: number | null;
  progress?: number | null; // Добавляем прогресс
  created_at?: string;
  updated_at?: string | null;
  testcases?: any[]; // Добавляем тест-кейсы
  violations_count?: number; // Для стандартов
  recommendations_count?: number; // Для оптимизации
  type?: string; // Тип задачи
};
type Fetcher<T extends BaseJob> = (jobId: string) => Promise<T>;

export const useJobWatcher = <T extends BaseJob = BaseJob>(
  jobId: string | null,
  fetcher: Fetcher<T>,
  onDone?: () => void
) => {
  const [job, setJob] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);

  const poll = useCallback(async () => {
    if (!jobId) return;
    try {
      const result = await fetcher(jobId);
      setJob(result);
      setError(null);
      
      if (["completed", "failed"].includes(result.status) && onDone) {
        onDone();
      }
    } catch (error: any) {
      console.error("Failed to fetch job:", error);
      setError(error.message || "Failed to fetch job");
    }
  }, [fetcher, jobId, onDone]);

  usePolling(poll, 2000, Boolean(jobId) && (!job || (job.status === "processing" || job.status === "pending")));

  return { job, setJob, error };
};