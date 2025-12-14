import { api } from "./client";
import { z } from "zod";
import { jobResponse } from "../../types/api";

export async function listAllJobs(params?: { 
  job_type?: string; 
  status?: string; 
  limit?: number; 
  offset?: number 
}) {
  const res = await api.get("/jobs/", { params });
  return z.array(jobResponse).parse(res.data);
}