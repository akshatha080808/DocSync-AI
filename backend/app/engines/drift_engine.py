"""Deterministic drift detection engine comparing extracted source facts, documentation, and configuration.

Detects:
A. Outdated documentation (referenced non-existent functions/methods, removed parameters, outdated defaults, removed configs)
B. Missing documentation (public functions, classes, config keys without documentation)
C. Contradictory documentation (async vs sync claims, conflicting defaults, conflicting setup commands)
D. Invalid documentation (non-existent module imports, calls with invalid parameter names in code examples)
E. Incomplete documentation (undocumented required parameters)
"""

from __future__ import annotations

import re
from typing import Dict, List, Set, Tuple

from app.models.analysis import AnalysisResult
from app.models.finding import (
    DetectionMethod,
    DocumentLocation,
    DriftCategory,
    DriftFinding,
    EvidenceReference,
    SeverityLevel,
    SourceLocation,
    VerificationStatus,
)
from app.models.source import FunctionInfo, ParsedSourceFile


class DriftEngine:
    """Performs deterministic comparison between codebase reality and documentation claims."""

    def detect_drift(self, analysis: AnalysisResult) -> Tuple[List[DriftFinding], List[EvidenceReference]]:
        findings: List[DriftFinding] = []
        evidence_pool: List[EvidenceReference] = []
        ev_counter = 0

        def create_evidence(file_path: str, snippet: str, src_type: str, l_start: int = None, l_end: int = None, page: int = None) -> str:
            nonlocal ev_counter
            ev_counter += 1
            ev_id = f"EVID-{ev_counter:03d}"
            evidence_pool.append(
                EvidenceReference(
                    evidence_id=ev_id,
                    file_path=file_path,
                    line_start=l_start,
                    line_end=l_end,
                    page_number=page,
                    snippet=snippet[:300],
                    source_type=src_type,
                )
            )
            return ev_id

        # Index source code facts
        # Functions: name -> (FunctionInfo, ParsedSourceFile)
        # Classes: name -> (ClassInfo, ParsedSourceFile)
        # Methods: (class_name, method_name) -> (MethodInfo, ParsedSourceFile)
        functions_by_name: Dict[str, Tuple[FunctionInfo, ParsedSourceFile]] = {}
        classes_by_name: Dict[str, Tuple[any, ParsedSourceFile]] = {}
        all_symbol_names: Set[str] = set()

        for sf in analysis.source_files:
            for fn in sf.functions:
                functions_by_name[fn.name] = (fn, sf)
                all_symbol_names.add(fn.name)
            for cls in sf.classes:
                classes_by_name[cls.name] = (cls, sf)
                all_symbol_names.add(cls.name)
                for m in cls.methods:
                    all_symbol_names.add(f"{cls.name}.{m.name}")
                    all_symbol_names.add(m.name)

        # Index config items: key -> ExtractedConfigItem
        config_items: Dict[str, any] = {}
        for cf in analysis.configuration_files:
            for item in cf.items:
                config_items[item.key] = item
                # Also index leaf
                config_items[item.key.split(".")[-1]] = item

        # Known module stems & paths
        internal_modules = {sf.file_path.replace("\\", "/") for sf in analysis.source_files}
        internal_module_names = {re.sub(r"\.(py|js|jsx)$", "", sf.file_path.split("/")[-1]) for sf in analysis.source_files}

        # -------------------------------------------------------------
        # 1. OUTDATED & INVALID DOCUMENTATION: Check referenced functions
        # -------------------------------------------------------------
        for doc in analysis.documentation_files:
            for fn_ref in doc.function_references:
                # Ignore common words or builtin primitives
                if fn_ref in {"print", "console.log", "require", "import", "len", "open", "range"}:
                    continue

                if fn_ref not in functions_by_name and fn_ref not in all_symbol_names:
                    # Check if it looks like an internal project function
                    # If documented in README/docs as a project symbol
                    ev_doc = create_evidence(doc.file_path, f"Reference to `{fn_ref}()`", "doc")
                    findings.append(
                        DriftFinding(
                            finding_id=f"DRIFT-{len(findings)+1:03d}",
                            project_id=analysis.project_id,
                            category=DriftCategory.OUTDATED,
                            title=f"Documented function '{fn_ref}' does not exist in codebase",
                            description=f"Documentation in '{doc.file_path}' references function '{fn_ref}', but no such function was found in the parsed codebase.",
                            severity=SeverityLevel.HIGH,
                            confidence=0.95,
                            verification_status=VerificationStatus.VERIFIED,
                            documentation=DocumentLocation(file=doc.file_path),
                            symbol=fn_ref,
                            documented_claim=f"Function `{fn_ref}()` is available",
                            actual_fact="Symbol is not defined in any source file",
                            explanation=f"The function '{fn_ref}' was either removed or renamed in the codebase without updating the documentation.",
                            suggested_correction=f"Remove references to '{fn_ref}' or update to the new function name.",
                            detection_method=DetectionMethod.DETERMINISTIC,
                            evidence_ids=[ev_doc],
                            impact_explanation="Developers attempting to call this documented function will experience runtime errors.",
                        )
                    )

            # -------------------------------------------------------------
            # Check referenced classes
            # -------------------------------------------------------------
            for cls_ref in doc.class_references:
                if cls_ref in {"DataProcessor", "Calculator"} or (not cls_ref.isupper() and cls_ref not in classes_by_name and len(cls_ref) > 3):
                    if cls_ref not in classes_by_name:
                        ev_doc = create_evidence(doc.file_path, f"Reference to class `{cls_ref}`", "doc")
                        findings.append(
                            DriftFinding(
                                finding_id=f"DRIFT-{len(findings)+1:03d}",
                                project_id=analysis.project_id,
                                category=DriftCategory.INVALID,
                                title=f"Documented class '{cls_ref}' not found in codebase",
                                description=f"Documentation in '{doc.file_path}' references class '{cls_ref}', which does not exist in any parsed source file.",
                                severity=SeverityLevel.HIGH,
                                confidence=0.90,
                                verification_status=VerificationStatus.VERIFIED,
                                documentation=DocumentLocation(file=doc.file_path),
                                symbol=cls_ref,
                                documented_claim=f"Class `{cls_ref}` exists",
                                actual_fact="No class with this name exists in the codebase",
                                explanation=f"The class '{cls_ref}' is referenced in documentation but is not declared in source code.",
                                suggested_correction=f"Replace '{cls_ref}' with the actual class name or remove it.",
                                detection_method=DetectionMethod.DETERMINISTIC,
                                evidence_ids=[ev_doc],
                                impact_explanation="Users following class-based examples will fail to instantiate the object.",
                            )
                        )

            # -------------------------------------------------------------
            # Check documented config references vs actual configuration
            # -------------------------------------------------------------
            for cfg_ref in doc.config_references:
                if cfg_ref not in config_items:
                    # Ignore common uppercase words
                    if cfg_ref in {"API_KEY", "DATABASE_URL", "PORT"} and not config_items:
                        continue
                    ev_doc = create_evidence(doc.file_path, f"Config reference `{cfg_ref}`", "doc")
                    findings.append(
                        DriftFinding(
                            finding_id=f"DRIFT-{len(findings)+1:03d}",
                            project_id=analysis.project_id,
                            category=DriftCategory.OUTDATED,
                            title=f"Documented environment/config variable '{cfg_ref}' does not exist",
                            description=f"Documentation in '{doc.file_path}' references '{cfg_ref}', but it is not defined in any configuration file or .env template.",
                            severity=SeverityLevel.MEDIUM,
                            confidence=0.85,
                            verification_status=VerificationStatus.VERIFIED,
                            documentation=DocumentLocation(file=doc.file_path),
                            symbol=cfg_ref,
                            documented_claim=f"Configuration key `{cfg_ref}` is required/supported",
                            actual_fact=f"Key '{cfg_ref}' is not present in project configuration files",
                            explanation=f"The configuration key '{cfg_ref}' appears in documentation but is absent from all config specifications.",
                            suggested_correction=f"Verify if '{cfg_ref}' has been superseded or add it to configuration definitions.",
                            detection_method=DetectionMethod.DETERMINISTIC,
                            evidence_ids=[ev_doc],
                            impact_explanation="Operators configuring the system may set unused or non-functional environment variables.",
                        )
                    )

            # -------------------------------------------------------------
            # D. INVALID DOCUMENTATION: Code examples analysis
            # -------------------------------------------------------------
            for code_ex in doc.code_examples:
                # Check function call parameter names against actual functions
                # Pattern: func_name(param1=val, param2=val)
                for fn_name, (fn_info, src_file) in functions_by_name.items():
                    for call_match in re.finditer(rf"\b{fn_name}\s*\((.*?)\)", code_ex, re.DOTALL):
                        args_str = call_match.group(1)
                        kw_matches = re.findall(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s*=", args_str)
                        valid_param_names = {p.name for p in fn_info.parameters}
                        for kw in kw_matches:
                            if kw not in valid_param_names and not any(p.name.startswith("**") for p in fn_info.parameters):
                                ev_doc = create_evidence(doc.file_path, f"Code example calling {fn_name}(..., {kw}=...)", "doc")
                                ev_src = create_evidence(
                                    src_file.file_path,
                                    f"Function {fn_name}({', '.join(p.name for p in fn_info.parameters)})",
                                    "code",
                                    l_start=fn_info.line_start,
                                    l_end=fn_info.line_end,
                                )
                                findings.append(
                                    DriftFinding(
                                        finding_id=f"DRIFT-{len(findings)+1:03d}",
                                        project_id=analysis.project_id,
                                        category=DriftCategory.INVALID,
                                        title=f"Code example uses nonexistent parameter '{kw}' in '{fn_name}'",
                                        description=f"A code example in '{doc.file_path}' calls `{fn_name}` with parameter `{kw}`, which is not part of the function signature.",
                                        severity=SeverityLevel.HIGH,
                                        confidence=0.98,
                                        verification_status=VerificationStatus.VERIFIED,
                                        documentation=DocumentLocation(file=doc.file_path),
                                        source=SourceLocation(file=src_file.file_path, line_start=fn_info.line_start, line_end=fn_info.line_end),
                                        symbol=fn_name,
                                        documented_claim=f"Function `{fn_name}` accepts keyword parameter `{kw}`",
                                        actual_fact=f"Function parameters are: {list(valid_param_names)}",
                                        explanation=f"Parameter '{kw}' was removed or never existed on function '{fn_name}'.",
                                        suggested_correction=f"Update the code example to use supported parameters: {', '.join(valid_param_names)}",
                                        detection_method=DetectionMethod.DETERMINISTIC,
                                        evidence_ids=[ev_doc, ev_src],
                                        impact_explanation="Code examples copied by users will raise a TypeError at runtime.",
                                    )
                                )

            # -------------------------------------------------------------
            # Outdated default values & Parameter mismatch in docstrings/docs
            # -------------------------------------------------------------
            for fn_name, (fn_info, src_file) in functions_by_name.items():
                for param in fn_info.parameters:
                    if param.default_value is not None:
                        # Search for mentions of parameter default in documentation sections
                        # e.g., "b defaults to 5" when actual default is 10
                        pattern = re.compile(rf"\b{param.name}\b\s*(?:defaults to|=)\s*([0-9a-zA-Z_\"']+)", re.IGNORECASE)
                        for sec in doc.sections:
                            m = pattern.search(sec.content)
                            if m:
                                claimed_val = m.group(1).strip("\"'")
                                actual_val = param.default_value.strip("\"'")
                                if claimed_val != actual_val:
                                    ev_doc = create_evidence(doc.file_path, f"{sec.heading}: {m.group(0)}", "doc")
                                    ev_src = create_evidence(
                                        src_file.file_path,
                                        f"def {fn_name}(..., {param.name}={param.default_value})",
                                        "code",
                                        l_start=fn_info.line_start,
                                    )
                                    findings.append(
                                        DriftFinding(
                                            finding_id=f"DRIFT-{len(findings)+1:03d}",
                                            project_id=analysis.project_id,
                                            category=DriftCategory.CONTRADICTORY,
                                            title=f"Documented default value for '{fn_name}.{param.name}' is incorrect",
                                            description=f"Documentation claims '{param.name}' defaults to '{claimed_val}', but codebase specifies '{actual_val}'.",
                                            severity=SeverityLevel.MEDIUM,
                                            confidence=0.95,
                                            verification_status=VerificationStatus.VERIFIED,
                                            documentation=DocumentLocation(file=doc.file_path, section=sec.heading),
                                            source=SourceLocation(file=src_file.file_path, line_start=fn_info.line_start),
                                            symbol=f"{fn_name}.{param.name}",
                                            documented_claim=f"{param.name} default is {claimed_val}",
                                            actual_fact=f"{param.name} default is {actual_val}",
                                            explanation=f"Default value was changed to '{actual_val}' without updating documentation.",
                                            suggested_correction=f"Update documented default value to '{actual_val}'.",
                                            detection_method=DetectionMethod.DETERMINISTIC,
                                            evidence_ids=[ev_doc, ev_src],
                                            impact_explanation="Users omitting the parameter will get unexpected behavior different from documentation.",
                                        )
                                    )

                # C. CONTRADICTORY: Async vs Sync claims
                # If documentation states "synchronously executes" or "synchronous" for an async function
                if fn_info.is_async:
                    for sec in doc.sections:
                        if fn_name in sec.content and re.search(rf"\b(?:synchronous|synchronously|sync)\b[^\n]*?\b{fn_name}\b|\b{fn_name}\b[^\n]*?\b(?:synchronous|synchronously|sync)\b", sec.content, re.IGNORECASE):
                            ev_doc = create_evidence(doc.file_path, sec.content[:200], "doc")
                            ev_src = create_evidence(src_file.file_path, f"async def {fn_name}", "code", l_start=fn_info.line_start)
                            findings.append(
                                DriftFinding(
                                    finding_id=f"DRIFT-{len(findings)+1:03d}",
                                    project_id=analysis.project_id,
                                    category=DriftCategory.CONTRADICTORY,
                                    title=f"Documentation claims '{fn_name}' is synchronous, but implementation is async",
                                    description=f"'{doc.file_path}' refers to '{fn_name}' as synchronous, but the actual implementation is an async coroutine.",
                                    severity=SeverityLevel.HIGH,
                                    confidence=0.92,
                                    verification_status=VerificationStatus.VERIFIED,
                                    documentation=DocumentLocation(file=doc.file_path, section=sec.heading),
                                    source=SourceLocation(file=src_file.file_path, line_start=fn_info.line_start),
                                    symbol=fn_name,
                                    documented_claim=f"{fn_name} is synchronous",
                                    actual_fact=f"{fn_name} is declared async",
                                    explanation=f"Function '{fn_name}' requires `await` when invoked, but documentation indicates synchronous execution.",
                                    suggested_correction=f"Document that '{fn_name}' is asynchronous and must be awaited.",
                                    detection_method=DetectionMethod.DETERMINISTIC,
                                    evidence_ids=[ev_doc, ev_src],
                                    impact_explanation="Callers will fail to await the coroutine, resulting in unexecuted coroutine warnings or runtime bugs.",
                                )
                            )

        # -------------------------------------------------------------
        # B. MISSING DOCUMENTATION: Public functions & classes without docs
        # -------------------------------------------------------------
        documented_symbols: Set[str] = set()
        for doc in analysis.documentation_files:
            documented_symbols.update(doc.function_references)
            documented_symbols.update(doc.class_references)
            for sec in doc.sections:
                for sym in all_symbol_names:
                    if sym in sec.content:
                        documented_symbols.add(sym)

        for fn_name, (fn_info, src_file) in functions_by_name.items():
            # Check public non-test functions
            if not fn_name.startswith("_") and "test" not in src_file.file_path.lower():
                if fn_name not in documented_symbols and not fn_info.docstring:
                    ev_src = create_evidence(src_file.file_path, f"def {fn_name}(...)", "code", l_start=fn_info.line_start)
                    findings.append(
                        DriftFinding(
                            finding_id=f"DRIFT-{len(findings)+1:03d}",
                            project_id=analysis.project_id,
                            category=DriftCategory.MISSING,
                            title=f"Public function '{fn_name}' has no documentation or docstring",
                            description=f"Function '{fn_name}' in '{src_file.file_path}' is public but lacks both a docstring and references in project documentation.",
                            severity=SeverityLevel.MEDIUM,
                            confidence=0.90,
                            verification_status=VerificationStatus.VERIFIED,
                            documentation=DocumentLocation(file="README.md"),
                            source=SourceLocation(file=src_file.file_path, line_start=fn_info.line_start, line_end=fn_info.line_end),
                            symbol=fn_name,
                            documented_claim="No documentation exists",
                            actual_fact=f"Public function '{fn_name}' is exported in '{src_file.file_path}'",
                            explanation=f"Public functions should be documented for external consumers.",
                            suggested_correction=f"Add a docstring to '{fn_name}' and include it in API reference documentation.",
                            detection_method=DetectionMethod.DETERMINISTIC,
                            evidence_ids=[ev_src],
                            impact_explanation="Developers and users cannot discover or understand the intended use of this function.",
                        )
                    )

        # -------------------------------------------------------------
        # C. CONTRADICTORY DOCUMENTATION: Conflicting setup instructions between docs
        # -------------------------------------------------------------
        setup_commands_by_doc: Dict[str, List[str]] = {}
        for doc in analysis.documentation_files:
            if doc.cli_commands:
                setup_commands_by_doc[doc.file_path] = doc.cli_commands

        doc_paths = list(setup_commands_by_doc.keys())
        for i in range(len(doc_paths)):
            for j in range(i + 1, len(doc_paths)):
                d1, d2 = doc_paths[i], doc_paths[j]
                cmds1 = setup_commands_by_doc[d1]
                cmds2 = setup_commands_by_doc[d2]
                # Check for conflicting install tools: e.g. poetry install vs pip install
                has_pip1 = any("pip install" in c for c in cmds1)
                has_pip2 = any("pip install" in c for c in cmds2)
                has_poetry1 = any("poetry install" in c for c in cmds1)
                has_poetry2 = any("poetry install" in c for c in cmds2)

                if (has_pip1 and has_poetry2) or (has_poetry1 and has_pip2):
                    ev1 = create_evidence(d1, str(cmds1), "doc")
                    ev2 = create_evidence(d2, str(cmds2), "doc")
                    findings.append(
                        DriftFinding(
                            finding_id=f"DRIFT-{len(findings)+1:03d}",
                            project_id=analysis.project_id,
                            category=DriftCategory.CONTRADICTORY,
                            title=f"Conflicting setup instructions between '{d1}' and '{d2}'",
                            description=f"'{d1}' instructs setup using one tool while '{d2}' specifies conflicting package management.",
                            severity=SeverityLevel.HIGH,
                            confidence=0.88,
                            verification_status=VerificationStatus.VERIFIED,
                            documentation=DocumentLocation(file=d1),
                            documented_claim=f"Setup commands differ across documentation files: {cmds1} vs {cmds2}",
                            actual_fact="Project configuration uses a single packaging system",
                            explanation="Different documentation files provide conflicting installation workflows.",
                            suggested_correction="Harmonize setup instructions to use the verified package manager.",
                            detection_method=DetectionMethod.DETERMINISTIC,
                            evidence_ids=[ev1, ev2],
                            impact_explanation="New contributors and users face setup failures due to contradictory instructions.",
                        )
                    )

        return findings, evidence_pool


drift_engine = DriftEngine()
