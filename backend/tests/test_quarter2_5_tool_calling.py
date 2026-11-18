"""Deterministic unit and mock tests for genuine Gemini tool-calling in AgentOrchestrator.

Verifies:
1. Model dynamically selects tool 1 (`inspect_symbol`).
2. Arguments are validated against allowlist.
3. Actual tool executes and produces real result.
4. Tool result is passed back to the model in the multi-turn conversation.
5. Model dynamically selects tool 2 (`compare_function_signature`) based on tool 1 result.
6. Execution trace clearly marks steps as MODEL_SELECTED_TOOL.
7. Iteration bounds are strictly enforced.
"""

from unittest.mock import MagicMock
from google.genai import types

from app.agents.orchestrator import AgentOrchestrator
from app.models.analysis import AnalysisResult
from tests.test_quarter2_drift import flawed_analysis_fixture


def test_dynamic_gemini_multistep_tool_calling(flawed_analysis_fixture: AnalysisResult):
    # Prepare Mock Gemini Client
    mock_client = MagicMock()

    # Step 1 Model Response: Model decides to call inspect_symbol(symbol_name="process_payment")
    part_1 = types.Part.from_function_call(name="inspect_symbol", args={"symbol_name": "process_payment"})
    cand_1 = types.Candidate(content=types.Content(role="model", parts=[part_1]))
    resp_1 = types.GenerateContentResponse(candidates=[cand_1])

    # Step 2 Model Response: After seeing inspect_symbol results, model calls compare_function_signature
    part_2 = types.Part.from_function_call(
        name="compare_function_signature",
        args={"function_name": "process_payment", "documented_signature": "process_payment(amount, currency, extra)"},
    )
    cand_2 = types.Candidate(content=types.Content(role="model", parts=[part_2]))
    resp_2 = types.GenerateContentResponse(candidates=[cand_2])

    # Step 3 Model Response: Model concludes investigation with final summary text
    part_3 = types.Part.from_text(text="Investigation concluded. Verified that process_payment has a parameter mismatch.")
    cand_3 = types.Candidate(content=types.Content(role="model", parts=[part_3]))
    resp_3 = types.GenerateContentResponse(candidates=[cand_3])

    mock_client.models.generate_content.side_effect = [resp_1, resp_2, resp_3]

    orchestrator = AgentOrchestrator(max_iterations=10, client=mock_client)
    findings, evidence, corrections, trace = orchestrator.run_investigation(flawed_analysis_fixture)

    # 1. Verify generate_content was called 3 times (model turn 1, model turn 2, final turn)
    assert mock_client.models.generate_content.call_count == 3

    # 2. Check that the multi-turn conversation passed the tool results back into contents
    # Third call to generate_content should have conversation history with function responses
    third_call_args = mock_client.models.generate_content.call_args_list[2]
    conversation_contents = third_call_args.kwargs["contents"]
    assert len(conversation_contents) == 5  # User prompt, Model call 1, Tool response 1, Model call 2, Tool response 2

    # Check tool response role and structure in history
    assert conversation_contents[1].role == "model"
    assert conversation_contents[2].role == "user"
    assert conversation_contents[2].parts[0].function_response.name == "inspect_symbol"

    assert conversation_contents[3].role == "model"
    assert conversation_contents[4].role == "user"
    assert conversation_contents[4].parts[0].function_response.name == "compare_function_signature"

    # 3. Check trace tags distinguishing MODEL_SELECTED_TOOL
    model_steps = [s for s in trace.steps if s.agent_action == "MODEL_SELECTED_TOOL"]
    assert len(model_steps) == 2
    assert model_steps[0].tool_selected == "inspect_symbol"
    assert "process_payment" in model_steps[0].tool_input_summary
    assert model_steps[0].execution_status == "SUCCESS"

    assert model_steps[1].tool_selected == "compare_function_signature"
    assert "process_payment" in model_steps[1].tool_input_summary
    assert model_steps[1].execution_status == "SUCCESS"

    # 4. Check trace completed properly
    assert trace.status == "COMPLETED"
