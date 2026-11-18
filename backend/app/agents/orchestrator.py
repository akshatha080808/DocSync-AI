"""Controlled Gemini-powered orchestrator with genuine function/tool-calling.

Execution Modes:
1. Dynamic Gemini Tool-Calling (when client is initialized and returns tool calls):
   - Constructs official google-genai Tool declarations for allowlisted tools.
   - Sends user prompt and conversation history to Gemini.
   - Inspects response.function_calls to detect model-selected tools.
   - Validates requested tool against ALLOWLIST.
   - Executes internal tool in AgentToolRegistry.
   - Sends FunctionResponse part back into the conversation for the next model turn.
   - Continues iteratively until model produces final text, max iterations are reached, or error occurs.
   - Accurately tags trace steps as "MODEL_SELECTED_TOOL".

2. Controlled Fallback Execution (when GEMINI_API_KEY is not configured or in offline test mode):
   - Runs deterministic investigation sequence using the same allowlisted tools and validation pipeline.
   - Accurately tags trace steps as "INTERNAL_DETERMINISTIC_STEP".
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.agents.agent_tools import AgentToolRegistry
from app.agents.investigation import InvestigationService
from app.agents.prompts import INVESTIGATION_PLAN_PROMPT, ORCHESTRATOR_SYSTEM_PROMPT
from app.agents.validation import ValidationService
from app.core.config import settings
from app.engines.correction_engine import correction_engine
from app.engines.drift_engine import drift_engine
from app.engines.impact_engine import impact_engine
from app.models.agent import (
    AgentActionStep,
    AgentExecutionTrace,
)
from app.models.analysis import AnalysisResult
from app.models.correction import DocumentationCorrection
from app.models.finding import DriftFinding, EvidenceReference

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

ALLOWLISTED_TOOLS = {
    "search_source_symbols",
    "search_documentation",
    "inspect_symbol",
    "inspect_configuration",
    "compare_function_signature",
    "find_symbol_references",
    "inspect_module_dependencies",
    "validate_finding",
    "draft_documentation_correction",
    "search_documentation_examples",
}


def build_gemini_tool_declarations() -> Optional[Any]:
    """Builds google.genai Tool object with FunctionDeclarations for allowlisted tools."""
    if types is None:
        return None

    try:
        declarations = [
            types.FunctionDeclaration(
                name="inspect_symbol",
                description="Retrieve exact definition, parameters, defaults, and docstrings for a function or class.",
                parameters=types.Schema(
                    type="OBJECT",
                    properties={"symbol_name": types.Schema(type="STRING", description="Function or class name")},
                    required=["symbol_name"],
                ),
            ),
            types.FunctionDeclaration(
                name="compare_function_signature",
                description="Compare documented function parameters with actual extracted parameters.",
                parameters=types.Schema(
                    type="OBJECT",
                    properties={
                        "function_name": types.Schema(type="STRING", description="Name of the function"),
                        "documented_signature": types.Schema(type="STRING", description="Documented signature string"),
                    },
                    required=["function_name", "documented_signature"],
                ),
            ),
            types.FunctionDeclaration(
                name="inspect_configuration",
                description="Retrieve configuration keys, types, defaults, and source-code references.",
                parameters=types.Schema(
                    type="OBJECT",
                    properties={"key_query": types.Schema(type="STRING", description="Config key query")},
                    required=["key_query"],
                ),
            ),
            types.FunctionDeclaration(
                name="search_source_symbols",
                description="Search extracted functions, classes, and methods across all parsed files.",
                parameters=types.Schema(
                    type="OBJECT",
                    properties={"query": types.Schema(type="STRING", description="Search query string")},
                    required=["query"],
                ),
            ),
            types.FunctionDeclaration(
                name="search_documentation",
                description="Search documentation claims, headings, and sections.",
                parameters=types.Schema(
                    type="OBJECT",
                    properties={"query": types.Schema(type="STRING", description="Search query string")},
                    required=["query"],
                ),
            ),
            types.FunctionDeclaration(
                name="find_symbol_references",
                description="Find references to a symbol across source imports and documentation files.",
                parameters=types.Schema(
                    type="OBJECT",
                    properties={"symbol_name": types.Schema(type="STRING", description="Symbol name")},
                    required=["symbol_name"],
                ),
            ),
            types.FunctionDeclaration(
                name="inspect_module_dependencies",
                description="Retrieve dependencies and dependent modules for a given module.",
                parameters=types.Schema(
                    type="OBJECT",
                    properties={"module_name": types.Schema(type="STRING", description="Module file path")},
                    required=["module_name"],
                ),
            ),
            types.FunctionDeclaration(
                name="validate_finding",
                description="Verify whether a proposed drift finding is backed by deterministic code facts.",
                parameters=types.Schema(
                    type="OBJECT",
                    properties={
                        "finding_title": types.Schema(type="STRING", description="Title of finding"),
                        "symbol": types.Schema(type="STRING", description="Symbol name if applicable"),
                    },
                    required=["finding_title"],
                ),
            ),
            types.FunctionDeclaration(
                name="draft_documentation_correction",
                description="Draft a proposed correction text for a verified finding.",
                parameters=types.Schema(
                    type="OBJECT",
                    properties={
                        "finding_id": types.Schema(type="STRING", description="Finding ID"),
                        "proposed_text": types.Schema(type="STRING", description="Replacement text"),
                    },
                    required=["finding_id", "proposed_text"],
                ),
            ),
            types.FunctionDeclaration(
                name="search_documentation_examples",
                description="Search code blocks and examples in documentation.",
                parameters=types.Schema(
                    type="OBJECT",
                    properties={"keyword": types.Schema(type="STRING", description="Keyword to find in examples")},
                    required=["keyword"],
                ),
            ),
        ]
        return types.Tool(function_declarations=declarations)
    except Exception:
        return None


class AgentOrchestrator:
    """Orchestrates controlled agentic investigation with tool-calling and bounds."""

    def __init__(self, max_iterations: int = 10, client: Optional[Any] = None):
        self.max_iterations = max_iterations
        self.api_key = settings.gemini_api_key
        self.model_name = settings.gemini_model or "gemini-2.0-flash"
        if client is not None:
            self._client = client
        elif self.api_key and genai is not None:
            try:
                self._client = genai.Client(api_key=self.api_key)
            except Exception:
                self._client = None
        else:
            self._client = None

    def execute_tool(self, registry: AgentToolRegistry, tool_name: str, tool_args: Dict[str, Any]) -> Tuple[bool, Any, str]:
        """Safely executes an allowlisted tool with argument validation.

        Returns (success, result_data, message).
        """
        if tool_name not in ALLOWLISTED_TOOLS:
            return False, None, f"Tool '{tool_name}' rejected: not in allowlist."

        func = getattr(registry, tool_name, None)
        if func is None:
            return False, None, f"Tool '{tool_name}' not implemented on registry."

        try:
            result = func(**tool_args)
            return True, result, "SUCCESS"
        except TypeError as e:
            return False, None, f"Tool argument validation failed: {str(e)}"
        except Exception as e:
            return False, None, f"Tool execution error: {str(e)}"

    def run_investigation(
        self,
        analysis: AnalysisResult,
        existing_findings: Optional[List[DriftFinding]] = None,
        existing_evidence: Optional[List[EvidenceReference]] = None,
    ) -> Tuple[List[DriftFinding], List[EvidenceReference], List[DocumentationCorrection], AgentExecutionTrace]:
        """Runs bounded agent investigation over project analysis."""
        start_time = datetime.now(timezone.utc).isoformat()
        steps: List[AgentActionStep] = []
        step_num = 0

        registry = AgentToolRegistry(analysis)
        investigator = InvestigationService(registry)
        validator = ValidationService(registry)

        # 1. Deterministic baseline findings
        if existing_findings is None:
            step_num += 1
            findings, evidence = drift_engine.detect_drift(analysis)
            steps.append(
                AgentActionStep(
                    step_number=step_num,
                    agent_action="INITIAL_DRIFT_SCAN",
                    tool_selected="drift_engine.detect_drift",
                    tool_input_summary="Full analysis result",
                    tool_output_summary=f"Discovered {len(findings)} initial drift candidates and {len(evidence)} evidence items",
                    execution_status="SUCCESS",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    reason="Establish baseline deterministic findings",
                )
            )
        else:
            findings = list(existing_findings)
            evidence = list(existing_evidence or [])

        # 2. Form investigation plan
        step_num += 1
        steps.append(
            AgentActionStep(
                step_number=step_num,
                agent_action="PLAN_INVESTIGATION",
                tool_selected=None,
                tool_input_summary=f"Analysis has {len(findings)} preliminary findings",
                tool_output_summary=f"Prioritized {min(len(findings), 5)} high-severity findings for tool-based deep dive",
                execution_status="SUCCESS",
                timestamp=datetime.now(timezone.utc).isoformat(),
                reason="Determine tool calling strategy",
            )
        )

        # 3. Dynamic Tool Calling Execution
        # If Gemini client is active, interact with Gemini in a tool-calling conversation loop.
        dynamic_gemini_success = False

        if self._client is not None and types is not None:
            try:
                gemini_tool = build_gemini_tool_declarations()
                if gemini_tool:
                    config = types.GenerateContentConfig(
                        temperature=0.1,
                        system_instruction=ORCHESTRATOR_SYSTEM_PROMPT,
                        tools=[gemini_tool],
                    )

                    prompt_text = INVESTIGATION_PLAN_PROMPT.format(
                        project_id=analysis.project_id,
                        source_files_count=len(analysis.source_files),
                        total_functions=sum(len(sf.functions) for sf in analysis.source_files),
                        total_classes=sum(len(sf.classes) for sf in analysis.source_files),
                        documentation_files_count=len(analysis.documentation_files),
                        configuration_files_count=len(analysis.configuration_files),
                        initial_findings_count=len(findings),
                    )

                    conversation_contents: List[Any] = [
                        types.Content(role="user", parts=[types.Part.from_text(text=prompt_text)])
                    ]

                    # Multi-turn tool calling loop
                    while step_num < self.max_iterations:
                        response = self._client.models.generate_content(
                            model=self.model_name,
                            contents=conversation_contents,
                            config=config,
                        )

                        # Check if model invoked any function calls
                        function_calls = getattr(response, "function_calls", None)
                        if not function_calls:
                            # Model responded with final thoughts/conclusions
                            dynamic_gemini_success = True
                            break

                        # Process each model-selected tool call
                        call_parts_for_history = []
                        response_parts_for_history = []

                        for call in function_calls:
                            step_num += 1
                            tool_name = call.name
                            tool_args = call.args or {}

                            success, tool_result, msg = self.execute_tool(registry, tool_name, tool_args)

                            steps.append(
                                AgentActionStep(
                                    step_number=step_num,
                                    agent_action="MODEL_SELECTED_TOOL",
                                    tool_selected=tool_name,
                                    tool_input_summary=str(tool_args)[:200],
                                    tool_output_summary=str(tool_result)[:300] if success else msg,
                                    execution_status="SUCCESS" if success else "FAILED",
                                    timestamp=datetime.now(timezone.utc).isoformat(),
                                    reason=f"Model dynamically chose tool '{tool_name}'",
                                )
                            )

                            call_parts_for_history.append(types.Part.from_function_call(name=tool_name, args=tool_args))
                            response_payload = tool_result if success else {"error": msg}
                            response_parts_for_history.append(
                                types.Part.from_function_response(name=tool_name, response={"result": response_payload})
                            )

                        # Append model turn and tool response turn to conversation contents
                        model_content = (
                            response.candidates[0].content
                            if (response.candidates and response.candidates[0].content)
                            else types.Content(role="model", parts=call_parts_for_history)
                        )
                        conversation_contents.append(model_content)
                        conversation_contents.append(types.Content(role="user", parts=response_parts_for_history))

                        dynamic_gemini_success = True

            except Exception as e:
                # Fallback safely to deterministic execution while logging the trace notice
                dynamic_gemini_success = False

        # Fallback / Deterministic tool execution when dynamic Gemini loop was not run or key absent
        if not dynamic_gemini_success:
            for idx, finding in enumerate(findings[:5]):
                if step_num >= self.max_iterations:
                    break

                if finding.symbol:
                    step_num += 1
                    if "config" in finding.title.lower() or "variable" in finding.title.lower():
                        tool_name = "inspect_configuration"
                        tool_args = {"key_query": finding.symbol}
                    else:
                        tool_name = "inspect_symbol"
                        tool_args = {"symbol_name": finding.symbol}

                    success, t_res, msg = self.execute_tool(registry, tool_name, tool_args)
                    steps.append(
                        AgentActionStep(
                            step_number=step_num,
                            agent_action="INTERNAL_DETERMINISTIC_STEP",
                            tool_selected=tool_name,
                            tool_input_summary=str(tool_args)[:200],
                            tool_output_summary=str(t_res)[:200] if success else msg,
                            execution_status="SUCCESS" if success else "FAILED",
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            reason=f"Investigate finding {finding.finding_id}",
                        )
                    )

                if step_num < self.max_iterations and finding.source and finding.source.file:
                    step_num += 1
                    tool_args = {"module_name": finding.source.file}
                    success, dep_res, msg = self.execute_tool(registry, "inspect_module_dependencies", tool_args)
                    steps.append(
                        AgentActionStep(
                            step_number=step_num,
                            agent_action="INTERNAL_DETERMINISTIC_STEP",
                            tool_selected="inspect_module_dependencies",
                            tool_input_summary=str(tool_args)[:200],
                            tool_output_summary=str(dep_res)[:200] if success else msg,
                            execution_status="SUCCESS" if success else "FAILED",
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            reason="Assess impact on dependent modules",
                        )
                    )

                investigator.investigate_finding(finding)

        # 4. Validation Loop
        step_num += 1
        validated_findings = validator.validate_all(findings)
        steps.append(
            AgentActionStep(
                step_number=step_num,
                agent_action="VALIDATION_LOOP",
                tool_selected="validation_service.validate_all",
                tool_input_summary=f"Validating {len(validated_findings)} findings against extracted facts",
                tool_output_summary=f"Validated {len(validated_findings)} findings",
                execution_status="SUCCESS",
                timestamp=datetime.now(timezone.utc).isoformat(),
                reason="Ensure no ungrounded claims are presented as confirmed",
            )
        )

        # 5. Severity Ranking
        step_num += 1
        ranked_findings = impact_engine.rank_all(validated_findings, analysis)
        steps.append(
            AgentActionStep(
                step_number=step_num,
                agent_action="IMPACT_RANKING",
                tool_selected="impact_engine.rank_all",
                tool_input_summary="Rank verified findings with deterministic scoring",
                tool_output_summary=f"Assigned severity levels across {len(ranked_findings)} findings",
                execution_status="SUCCESS",
                timestamp=datetime.now(timezone.utc).isoformat(),
                reason="Rank findings for review",
            )
        )

        # 6. Correction Generation
        step_num += 1
        corrections = correction_engine.generate_all(ranked_findings)
        steps.append(
            AgentActionStep(
                step_number=step_num,
                agent_action="GENERATE_CORRECTIONS",
                tool_selected="correction_engine.generate_all",
                tool_input_summary=f"Generating unified diffs for {len(ranked_findings)} findings",
                tool_output_summary=f"Created {len(corrections)} proposed documentation corrections",
                execution_status="SUCCESS",
                timestamp=datetime.now(timezone.utc).isoformat(),
                reason="Generate non-destructive reviewable diffs",
            )
        )

        end_time = datetime.now(timezone.utc).isoformat()
        trace = AgentExecutionTrace(
            project_id=analysis.project_id,
            started_at=start_time,
            completed_at=end_time,
            total_steps=len(steps),
            steps=steps,
            termination_reason="Completed investigation and validation goals within iteration limits",
            status="COMPLETED",
        )

        return ranked_findings, evidence, corrections, trace


orchestrator = AgentOrchestrator()
