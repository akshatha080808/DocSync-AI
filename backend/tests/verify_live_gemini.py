"""Manual and optional live Gemini integration verification script.

Usage:
    # 1. Set GEMINI_API_KEY environment variable:
    #    $env:GEMINI_API_KEY="your-actual-api-key"
    # 2. Run script:
    #    python backend/tests/verify_live_gemini.py

This script:
1. Inspects GEMINI_API_KEY (never prints or logs the secret).
2. If key is missing, informs user how to configure it and exits cleanly without failure.
3. If key is configured, initializes live google-genai Client.
4. Sends an analysis and tool declarations to Gemini (gemini-2.0-flash).
5. Observes genuine model-selected function calls.
6. Validates against allowlisted tools and executes.
7. Passes tool result back and completes the turn.
8. Displays the resulting execution trace with MODEL_SELECTED_TOOL actions.
"""

import os
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

from app.agents.orchestrator import AgentOrchestrator
from app.core.config import settings
from tests.test_quarter2_drift import flawed_analysis_fixture


def main():
    api_key = os.getenv("GEMINI_API_KEY", "").strip() or settings.gemini_api_key

    print("=" * 70)
    print("DOCSYNC AI — LIVE GEMINI AGENT VERIFICATION")
    print("=" * 70)

    if not api_key:
        print("[INFO] GEMINI_API_KEY is not configured in environment or .env.")
        print("[INFO] Offline deterministic analysis and mock tool calling remain active.")
        print("[INFO] To run live Gemini verification, configure GEMINI_API_KEY and re-run:")
        print("       PowerShell: $env:GEMINI_API_KEY=\"AIzaSy...\"")
        print("       python backend/tests/verify_live_gemini.py")
        print("=" * 70)
        return

    print("[SUCCESS] GEMINI_API_KEY detected (redacted for security).")
    print(f"[INFO] Using model: {settings.gemini_model or 'gemini-2.0-flash'}")
    print("[INFO] Initializing live AgentOrchestrator with google-genai Client...")

    fixture = flawed_analysis_fixture()
    orchestrator = AgentOrchestrator(max_iterations=6)

    print("[INFO] Invoking orchestrator.run_investigation()...")
    findings, evidence, corrections, trace = orchestrator.run_investigation(fixture)

    print("\n--- AGENT EXECUTION TRACE ---")
    print(f"Project ID: {trace.project_id}")
    print(f"Status: {trace.status}")
    print(f"Total Steps: {trace.total_steps}")
    print(f"Termination Reason: {trace.termination_reason}")

    model_tool_calls = [s for s in trace.steps if s.agent_action == "MODEL_SELECTED_TOOL"]
    print(f"\nModel-Selected Dynamic Tool Calls Count: {len(model_tool_calls)}")

    for step in trace.steps:
        print(f"\nStep #{step.step_number}: [{step.agent_action}]")
        print(f"  Tool: {step.tool_selected}")
        print(f"  Input: {step.tool_input_summary}")
        print(f"  Output: {step.tool_output_summary}")
        print(f"  Status: {step.execution_status}")
        print(f"  Reason: {step.reason}")

    print("\n" + "=" * 70)
    if model_tool_calls:
        print("[VERIFIED] Live Gemini dynamically invoked registered tools!")
    else:
        print("[NOTICE] Model completed investigation without invoking additional tool calls.")
    print("=" * 70)


if __name__ == "__main__":
    main()
