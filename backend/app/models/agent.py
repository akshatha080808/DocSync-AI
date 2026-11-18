"""Pydantic data models for agent execution traces and tool operations."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AgentActionStep(BaseModel):
    step_number: int
    agent_action: str
    tool_selected: Optional[str] = None
    tool_input_summary: Optional[str] = None
    tool_output_summary: Optional[str] = None
    execution_status: str  # "SUCCESS", "FAILED", "SKIPPED", "TERMINATED"
    timestamp: str
    reason: str


class AgentExecutionTrace(BaseModel):
    project_id: str
    started_at: str
    completed_at: str
    total_steps: int
    steps: List[AgentActionStep] = Field(default_factory=list)
    termination_reason: str
    status: str  # "COMPLETED", "FAILED", "PARTIAL"


class AgentRunResponse(BaseModel):
    project_id: str
    status: str
    message: str
    total_findings_generated: int
    total_corrections_generated: int
    trace: AgentExecutionTrace
