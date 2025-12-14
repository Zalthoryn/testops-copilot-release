from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from enum import Enum

class TestPriority(str, Enum):
    CRITICAL = "CRITICAL"
    NORMAL = "NORMAL"
    LOW = "LOW"

class TestType(str, Enum):
    MANUAL_UI = "manual_ui"
    MANUAL_API = "manual_api"
    AUTO_UI = "auto_ui"
    AUTO_API = "auto_api"

class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

# Модели для запросов
class LLMValidationRequest(BaseModel):
    api_key: str
    model: Optional[str] = "openai/gpt-oss-120b"
    base_url: Optional[str] = "https://foundation-models.api.cloud.ru/v1"

class ComputeValidationRequest(BaseModel):
    token: Optional[str] = None
    key_id: Optional[str] = None
    secret: Optional[str] = None

class GitLabValidationRequest(BaseModel):
    token: str
    project_id: str
    base_url: Optional[str] = "https://gitlab.com"

class UIGenerationRequest(BaseModel):
    requirements: str
    test_blocks: List[str]
    target_count: int = Field(ge=1, le=100, default=5)
    priority: TestPriority = TestPriority.NORMAL
    owner: Optional[str] = "qa_engineer"
    include_screenshots: Optional[bool] = False

class APIGenerationRequest(BaseModel):
    openapi_url: Optional[str] = None
    openapi_content: Optional[str] = None
    sections: List[str]
    auth_type: Optional[str] = "bearer"
    target_count: int = Field(ge=1, le=100, default=5)
    priority: Optional[TestPriority] = TestPriority.NORMAL

class UIAutotestsRequest(BaseModel):
    manual_testcases_ids: List[str]
    framework: Optional[str] = "playwright"
    browsers: Optional[List[str]] = ["chromium"]
    base_url: Optional[str] = "https://cloud.ru/calculator"
    headless: Optional[bool] = True
    priority_filter: Optional[List[str]] = ["CRITICAL", "NORMAL"]

class APIAutotestsRequest(BaseModel):
    manual_testcases_ids: List[str]
    openapi_url: Optional[str] = None
    sections: List[str]
    base_url: Optional[str] = "https://compute.api.cloud.ru"
    auth_token: Optional[str] = None
    test_framework: Optional[str] = "pytest"
    http_client: Optional[str] = "httpx"

class OptimizationRequest(BaseModel):
    repository_url: Optional[str] = None
    requirements: Optional[str] = None
    checks: List[str]
    optimization_level: Optional[str] = "moderate"

# Модели для ответов
class TestCaseDTO(BaseModel):
    id: str
    title: str
    feature: str
    story: str
    priority: TestPriority
    steps: List[str]
    expected_result: str
    python_code: str
    test_type: TestType
    owner: str
    created_at: str
    updated_at: Optional[str] = None

class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    message: Optional[str] = None
    estimated_time: Optional[int] = None
    created_at: str
    updated_at: Optional[str] = None

class JobStatusResponse(JobResponse):
    testcases: Optional[List[TestCaseDTO]] = []
    download_url: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[str] = None

class StandardsViolation(BaseModel):
    file: str
    line: int
    severity: str  # error, warning, info
    rule: str
    message: str
    suggested_fix: str
    code_snippet: Optional[str] = None

class StandardsReport(BaseModel):
    job_id: str
    status: JobStatus
    total_files: int
    total_violations: int
    violations_by_severity: Dict[str, int]
    violations: List[StandardsViolation]
    generated_at: str

class OptimizationResult(BaseModel):
    job_id: str
    status: JobStatus
    analysis: Dict[str, Any]
    recommendations: List[Dict[str, Any]]
    optimized_testcases: List[TestCaseDTO]
    generated_at: str

class ConfigResponse(BaseModel):
    llm_model: str
    llm_available: bool
    compute_endpoint: str
    compute_available: bool
    gitlab_configured: bool
    environment: str

class ComputeValidationResponse(BaseModel):
    valid: bool
    endpoint: str
    available_resources: List[str]
    error: Optional[str] = None

# ===== GitLab Integration Models =====

class GitLabInitRequest(BaseModel):
    token: str
    gitlab_url: Optional[str] = "https://gitlab.com"

class GitLabReposRequest(BaseModel):
    token: str
    search: Optional[str] = None

class GitLabCommitRequest(BaseModel):
    token: str
    project_id: str
    testcases: List[str]
    directory: Optional[str] = "tests/manual"
    branch: Optional[str] = "main"
    commit_message: Optional[str] = None

# ===== TestPlan Models =====

class TestPlanRequest(BaseModel):
    testcases: List[Dict[str, Any]]
    requirements: Optional[str] = None
    sprint_duration: Optional[int] = 14
    team_size: Optional[int] = 2