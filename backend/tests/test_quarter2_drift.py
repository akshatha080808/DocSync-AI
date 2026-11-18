"""Unit and integration tests for Quarter 2:
- Deterministic drift detection across all 5 categories (outdated, missing, contradictory, invalid, incomplete)
- Deliberately flawed test project fixture (payment.py, users.py, config.py, README.md, docs/api.md)
- Impact and severity ranking
- Proposed correction generation with unified diffs
- Agent tool selection, investigation loop, and validation loop
- Trace persistence and bounded execution
- Missing Gemini key resilience
"""

import io
import zipfile
from pathlib import Path
import pytest

from app.agents.agent_tools import AgentToolRegistry
from app.agents.investigation import InvestigationService
from app.agents.orchestrator import AgentOrchestrator
from app.agents.validation import ValidationService
from app.engines.correction_engine import CorrectionEngine
from app.engines.drift_engine import DriftEngine
from app.engines.impact_engine import ImpactEngine
from app.engines.semantic_engine import SemanticEngine
from app.models.analysis import (
    AnalysisResult,
    AnalysisSummary,
    DependencyGraph,
    DependencyNode,
    DocSection,
    ExtractedConfigFile,
    ExtractedConfigItem,
    ExtractedDocFile,
)
from app.models.finding import (
    DriftCategory,
    DriftFinding,
    EvidenceReference,
    SeverityLevel,
    VerificationStatus,
)
from app.models.source import FunctionInfo, ParameterInfo, ParsedSourceFile


@pytest.fixture
def flawed_analysis_fixture() -> AnalysisResult:
    """Creates a deterministic analysis result simulating a project with intentional documentation drift."""
    # Source 1: src/payment.py
    # Function: process_payment(amount: float, currency: str = "USD")
    # Async Function: verify_transaction(tx_id: str)
    src_payment = ParsedSourceFile(
        file_path="src/payment.py",
        language="python",
        functions=[
            FunctionInfo(
                name="process_payment",
                parameters=[
                    ParameterInfo(name="amount", annotation="float"),
                    ParameterInfo(name="currency", default_value="'USD'", annotation="str"),
                ],
                return_annotation="bool",
                is_async=False,
                docstring="Process payment with currency.",
                line_start=10,
                line_end=15,
            ),
            FunctionInfo(
                name="verify_transaction",
                parameters=[ParameterInfo(name="tx_id", annotation="str")],
                return_annotation="dict",
                is_async=True,  # Implementation is async!
                docstring=None,
                line_start=20,
                line_end=25,
            ),
        ],
        loc=30,
    )

    # Source 2: src/users.py
    # Public function lacking docstring and lacking any docs: calculate_user_discount
    src_users = ParsedSourceFile(
        file_path="src/users.py",
        language="python",
        functions=[
            FunctionInfo(
                name="calculate_user_discount",
                parameters=[ParameterInfo(name="user_id", annotation="str")],
                is_async=False,
                docstring=None,  # Undocumented public function!
                line_start=5,
                line_end=10,
            )
        ],
        loc=20,
    )

    # Documentation: README.md
    # Contains:
    # 1. Reference to deleted function 'refund_payment()'
    # 2. Reference to deleted class 'LegacyProcessor'
    # 3. Code example calling process_payment with invalid param 'discount_code=10'
    # 4. Outdated claim: 'currency defaults to EUR' (code has 'USD')
    # 5. Claim that verify_transaction is synchronous
    # 6. Reference to nonexistent config 'PAYMENT_GATEWAY_SECRET'
    doc_readme = ExtractedDocFile(
        file_path="README.md",
        doc_type="markdown",
        title="Payment Service",
        function_references=["refund_payment", "process_payment", "verify_transaction"],
        class_references=["LegacyProcessor"],
        config_references=["PAYMENT_GATEWAY_SECRET"],
        code_examples=[
            "process_payment(amount=100.0, discount_code=10)",  # invalid param discount_code
        ],
        sections=[
            DocSection(
                heading="Usage",
                level=2,
                content="Call process_payment. The parameter currency defaults to EUR. To verify, synchronously execute verify_transaction.",
                page_number=None,
            ),
        ],
        cli_commands=["pip install -r requirements.txt"],
    )

    # Documentation: docs/api.md
    # Conflicting setup instructions: claims poetry install
    doc_api = ExtractedDocFile(
        file_path="docs/api.md",
        doc_type="markdown",
        title="API Reference",
        function_references=["process_payment"],
        class_references=[],
        config_references=[],
        code_examples=[],
        sections=[],
        cli_commands=["poetry install"],  # Contradicts pip install in README
    )

    # Config file: config.yaml
    cfg_file = ExtractedConfigFile(
        file_path="config.yaml",
        format="yaml",
        items=[
            ExtractedConfigItem(
                key="database.url",
                value_type="str",
                default_value="sqlite:///test.db",
                is_secret=False,
                file_path="config.yaml",
            )
        ],
    )

    return AnalysisResult(
        project_id="test-drift-proj",
        summary=AnalysisSummary(
            project_id="test-drift-proj",
            analyzed_at="2026-11-18T10:00:00Z",
            source_files_count=2,
            total_functions=3,
            total_classes=0,
            total_methods=0,
            total_loc=50,
            documentation_files_count=2,
            configuration_files_count=1,
            dependency_nodes_count=2,
            dependency_edges_count=0,
            circular_dependency_count=0,
            warnings=[],
        ),
        source_files=[src_payment, src_users],
        documentation_files=[doc_readme, doc_api],
        configuration_files=[cfg_file],
        dependency_graph=DependencyGraph(
            nodes=[
                DependencyNode(id="src/payment.py", label="payment.py", file_path="src/payment.py", language="python"),
                DependencyNode(id="src/users.py", label="users.py", file_path="src/users.py", language="python"),
            ],
            edges=[],
            cycles=[],
            external_dependencies=[],
            isolated_modules=["src/payment.py", "src/users.py"],
        ),
    )


def test_drift_engine_detects_all_categories(flawed_analysis_fixture: AnalysisResult):
    engine = DriftEngine()
    findings, evidence = engine.detect_drift(flawed_analysis_fixture)

    assert len(findings) >= 6
    assert len(evidence) >= 6

    titles = [f.title for f in findings]
    categories = [f.category for f in findings]

    # 1. OUTDATED: refund_payment does not exist
    assert any("refund_payment" in t for t in titles)
    assert DriftCategory.OUTDATED in categories

    # 2. INVALID: LegacyProcessor class not found
    assert any("LegacyProcessor" in t for t in titles)
    assert DriftCategory.INVALID in categories

    # 3. INVALID: Code example uses nonexistent parameter 'discount_code'
    assert any("discount_code" in t for t in titles)

    # 4. CONTRADICTORY: currency default is EUR vs USD
    assert any("currency" in t for t in titles)
    assert DriftCategory.CONTRADICTORY in categories

    # 5. CONTRADICTORY: verify_transaction is async vs synchronous
    assert any("verify_transaction" in t and "async" in t for t in titles)

    # 6. MISSING: calculate_user_discount is undocumented
    assert any("calculate_user_discount" in t for t in titles)
    assert DriftCategory.MISSING in categories

    # 7. CONTRADICTORY: pip install vs poetry install
    assert any("Conflicting setup" in t for t in titles)


def test_impact_engine_ranking(flawed_analysis_fixture: AnalysisResult):
    drift_eng = DriftEngine()
    findings, _ = drift_eng.detect_drift(flawed_analysis_fixture)

    impact_eng = ImpactEngine()
    ranked = impact_eng.rank_all(findings, flawed_analysis_fixture)

    # Top findings should have HIGH or CRITICAL severity
    assert ranked[0].severity in (SeverityLevel.CRITICAL, SeverityLevel.HIGH)
    assert ranked[0].impact_explanation is not None


def test_correction_engine_unified_diff(flawed_analysis_fixture: AnalysisResult):
    drift_eng = DriftEngine()
    findings, _ = drift_eng.detect_drift(flawed_analysis_fixture)

    corr_eng = CorrectionEngine()
    corrections = corr_eng.generate_all(findings)

    assert len(corrections) >= 3
    for c in corrections:
        assert c.unified_diff.startswith("---")
        assert "+++" in c.unified_diff
        assert c.validation_status == "VERIFIED"


def test_agent_tool_registry(flawed_analysis_fixture: AnalysisResult):
    registry = AgentToolRegistry(flawed_analysis_fixture)

    # 1. Search symbols
    syms = registry.search_source_symbols("payment")
    assert len(syms) >= 1
    assert syms[0]["name"] == "process_payment"

    # 2. Inspect symbol
    inspect_res = registry.inspect_symbol("process_payment")
    assert inspect_res["found"] is True
    assert len(inspect_res["parameters"]) == 2

    # 3. Compare signature
    comp_res = registry.compare_function_signature("process_payment", "process_payment(amount, currency, extra_param)")
    assert comp_res["match"] is False
    assert "extra_param" in comp_res["extraneous_in_documentation"]

    # 4. Search documentation
    doc_res = registry.search_documentation("currency")
    assert len(doc_res) >= 1

    # 5. Search code examples
    ex_res = registry.search_documentation_examples("discount_code")
    assert len(ex_res) >= 1


def test_agent_orchestrator_execution(flawed_analysis_fixture: AnalysisResult):
    orchestrator = AgentOrchestrator(max_iterations=8)
    findings, evidence, corrections, trace = orchestrator.run_investigation(flawed_analysis_fixture)

    assert len(findings) >= 5
    assert len(corrections) >= 3
    assert trace.status == "COMPLETED"
    assert trace.total_steps >= 4
    assert any(s.agent_action in ("INSPECT_FACTS", "INTERNAL_DETERMINISTIC_STEP", "MODEL_SELECTED_TOOL") for s in trace.steps)
    assert any(s.agent_action == "VALIDATION_LOOP" for s in trace.steps)


def test_semantic_engine_missing_key_graceful_handling():
    # When api key is missing, semantic engine reports unavailable and does not raise
    sem_engine = SemanticEngine()
    sem_engine._client = None  # simulate unconfigured/missing key
    # Should safely return None without throwing error
    res = sem_engine.analyze_semantic_drift(
        analysis=type("Analysis", (), {"source_files": [], "configuration_files": [], "project_id": "demo"})(),
        doc_claim="Projects are saved in Postgres database",
        doc_file="README.md",
    )
    assert res is None
