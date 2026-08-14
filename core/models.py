from enum import Enum
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field
import time

class ActionType(str, Enum):
    GOTO = "goto"
    CLICK = "click"
    FILL = "fill"
    SELECT_OPTION = "select_option"
    WAIT_FOR = "wait_for"
    ASSERT_TEXT = "assert_text"
    ASSERT_URL = "assert_url"
    HOVER = "hover"
    SCREENSHOT = "screenshot"
    SCROLL = "scroll"

class StepConfig(BaseModel):
    id: str = Field(default_factory=lambda: str(int(time.time() * 1000)))
    name: str
    action: ActionType
    selector: Optional[str] = None
    value: Optional[str] = None
    timeout: int = 10000  # milliseconds
    description: Optional[str] = None

class ScenarioConfig(BaseModel):
    id: str = Field(default_factory=lambda: f"scenario_{int(time.time())}")
    title: str
    target_url: str
    headless: bool = True
    browser_type: str = "chromium"  # chromium, firefox, webkit
    steps: List[StepConfig]

class LogEntry(BaseModel):
    timestamp: float = Field(default_factory=time.time)
    level: str  # "info", "warning", "error", "console_err", "network_err"
    message: str
    details: Optional[Dict[str, Any]] = None

class StepResult(BaseModel):
    step_id: str
    step_name: str
    action: str
    success: bool
    duration_ms: float
    error_message: Optional[str] = None
    screenshot_path: Optional[str] = None
    log_entries: List[LogEntry] = []

class ScenarioResult(BaseModel):
    scenario_id: str
    scenario_title: str
    target_url: str
    start_time: float
    end_time: float
    duration_ms: float
    passed: bool
    total_steps: int
    passed_steps: int
    failed_steps: int
    step_results: List[StepResult]
    console_errors: List[LogEntry] = []
    network_errors: List[LogEntry] = []
    performance_metrics: Dict[str, Any] = {}
