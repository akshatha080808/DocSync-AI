"""Report generation engine producing PDF (via ReportLab) and comprehensive JSON audit artifacts."""

from __future__ import annotations

import io
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.models.agent import AgentExecutionTrace
from app.models.analysis import AnalysisResult
from app.models.correction import DocumentationCorrection
from app.models.finding import DriftFinding
from app.models.project import ProjectDetail


class ReportEngine:
    """Generates structured JSON exports and printable executive PDF summaries."""

    def generate_json_report(
        self,
        project: ProjectDetail,
        analysis: Optional[AnalysisResult],
        findings: List[DriftFinding],
        corrections: List[DocumentationCorrection],
        trace: Optional[AgentExecutionTrace],
    ) -> Dict[str, Any]:
        """Assembles a full-fidelity audit snapshot."""
        # Calculate severity distribution
        severity_dist = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
        category_dist = {}
        for f in findings:
            sev = f.severity.value if hasattr(f.severity, "value") else str(f.severity)
            severity_dist[sev] = severity_dist.get(sev, 0) + 1

            cat = f.category.value if hasattr(f.category, "value") else str(f.category)
            category_dist[cat] = category_dist.get(cat, 0) + 1

        return {
            "report_version": "1.0.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "project": {
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "created_at": project.created_at,
                "updated_at": project.updated_at,
                "file_count": project.file_count,
                "total_size_bytes": project.total_size_bytes,
                "audit_mode": getattr(project, "audit_mode", "zip"),
                "github_repo": getattr(project, "github_repo", None),
                "github_branch": getattr(project, "github_branch", None),
                "latest_commit_sha": getattr(project, "latest_commit_sha", None),
                "drift_status": getattr(project, "drift_status", None),
                "last_drift_detected_at": getattr(project, "last_drift_detected_at", None),
            },
            "summary": {
                "total_findings": len(findings),
                "severity_distribution": severity_dist,
                "category_distribution": category_dist,
                "total_corrections": len(corrections),
                "has_analysis": analysis is not None,
                "agent_trace_steps": trace.total_steps if trace else 0,
            },
            "findings": [f.model_dump() for f in findings],
            "corrections": [c.model_dump() for c in corrections],
            "analysis_summary": analysis.summary.model_dump() if analysis else None,
            "agent_trace": trace.model_dump() if trace else None,
        }

    def generate_pdf_report(
        self,
        project: ProjectDetail,
        analysis: Optional[AnalysisResult],
        findings: List[DriftFinding],
        corrections: List[DocumentationCorrection],
        trace: Optional[AgentExecutionTrace],
    ) -> bytes:
        """Generates an executive PDF report using ReportLab."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "DocSyncTitle",
            parent=styles["Heading1"],
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=12,
        )
        subtitle_style = ParagraphStyle(
            "DocSyncSubtitle",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#64748b"),
            spaceAfter=20,
        )
        heading_style = ParagraphStyle(
            "DocSyncHeading",
            parent=styles["Heading2"],
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#1e293b"),
            spaceBefore=14,
            spaceAfter=8,
        )
        normal_style = ParagraphStyle(
            "DocSyncNormal",
            parent=styles["Normal"],
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#334155"),
        )
        code_style = ParagraphStyle(
            "DocSyncCode",
            parent=styles["Normal"],
            fontSize=8,
            leading=11,
            fontName="Courier",
            textColor=colors.HexColor("#0f172a"),
        )

        story = []

        # 1. Header
        story.append(Paragraph("DocSync AI — Documentation Drift Audit Report", title_style))
        gen_time = datetime.now(timezone.utc).strftime("%B %d, %Y - %H:%M:%S UTC")
        
        mode_label = "GitHub Connected" if getattr(project, "audit_mode", "zip") == "github" else "ZIP Archive Audit"
        repo_info = f" &nbsp;|&nbsp; <b>Repo:</b> {project.github_repo} ({project.github_branch})" if getattr(project, "audit_mode", "zip") == "github" and getattr(project, "github_repo", None) else ""
        commit_info = f" &nbsp;|&nbsp; <b>Commit:</b> {project.latest_commit_sha[:8]}" if getattr(project, "latest_commit_sha", None) else ""

        story.append(
            Paragraph(
                f"<b>Project:</b> {project.name} &nbsp;|&nbsp; <b>ID:</b> {project.id}<br/>"
                f"<b>Mode:</b> {mode_label}{repo_info}{commit_info}<br/>"
                f"<b>Generated:</b> {gen_time} &nbsp;|&nbsp; <b>Files Analyzed:</b> {project.file_count}",
                subtitle_style,
            )
        )
        story.append(Spacer(1, 10))

        # 2. Executive Metrics Summary Table
        severity_dist = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
        for f in findings:
            sev = f.severity.value if hasattr(f.severity, "value") else str(f.severity)
            severity_dist[sev] = severity_dist.get(sev, 0) + 1

        summary_data = [
            ["Metric", "Value", "Metric", "Value"],
            ["Total Findings", str(len(findings)), "Proposed Corrections", str(len(corrections))],
            ["Critical Drift", str(severity_dist["CRITICAL"]), "High Drift", str(severity_dist["HIGH"])],
            ["Medium Drift", str(severity_dist["MEDIUM"]), "Low / Info Drift", str(severity_dist["LOW"] + severity_dist["INFO"])],
        ]
        if analysis:
            summary_data.append([
                "Functions Analyzed", str(analysis.summary.total_functions),
                "Classes Analyzed", str(analysis.summary.total_classes)
            ])
            summary_data.append([
                "Total LOC", str(analysis.summary.total_loc),
                "Dependency Cycles", str(analysis.summary.circular_dependency_count)
            ])

        summary_table = Table(summary_data, colWidths=[130, 130, 130, 130])
        summary_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
            ])
        )
        story.append(summary_table)
        story.append(Spacer(1, 15))

        # 3. Findings Section
        story.append(Paragraph("Key Drift Findings", heading_style))

        if not findings:
            story.append(Paragraph("No documentation drift detected in this codebase.", normal_style))
        else:
            findings_data = [["ID / Severity", "Category", "Affected Symbol & File", "Description"]]
            for f in findings[:25]:  # include up to 25 primary findings in PDF
                sev_color = {
                    "CRITICAL": "#dc2626",
                    "HIGH": "#ea580c",
                    "MEDIUM": "#ca8a04",
                    "LOW": "#2563eb",
                    "INFO": "#64748b",
                }.get(f.severity.value, "#334155")

                id_sev = f"<b>{f.finding_id}</b><br/><font color='{sev_color}'><b>{f.severity.value}</b></font>"
                sym_file = f"<b>{f.symbol or 'N/A'}</b><br/>Doc: {f.documentation.file}"
                if f.source:
                    sym_file += f"<br/>Src: {f.source.file}"

                findings_data.append([
                    Paragraph(id_sev, normal_style),
                    Paragraph(f.category.value, normal_style),
                    Paragraph(sym_file, normal_style),
                    Paragraph(f"<b>{f.title}</b><br/>{f.explanation[:160]}", normal_style),
                ])

            findings_table = Table(findings_data, colWidths=[80, 85, 155, 200])
            findings_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ])
            )
            story.append(findings_table)

        # 4. Agent Trace Summary
        if trace and trace.steps:
            story.append(Spacer(1, 15))
            story.append(Paragraph(f"Agent Investigation Trace ({trace.status})", heading_style))
            trace_data = [["Step", "Action", "Tool Selected", "Summary / Status"]]
            for step in trace.steps[:10]:
                trace_data.append([
                    str(step.step_number),
                    step.agent_action,
                    step.tool_selected or "None",
                    Paragraph(f"{step.tool_output_summary or step.reason}", normal_style),
                ])

            trace_table = Table(trace_data, colWidths=[35, 125, 130, 230])
            trace_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ])
            )
            story.append(trace_table)

        # 5. Proposed Corrections Summary
        if corrections:
            story.append(Spacer(1, 15))
            story.append(Paragraph(f"Proposed Documentation Corrections ({len(corrections)} generated)", heading_style))
            for c in corrections[:5]:
                story.append(
                    Paragraph(
                        f"<b>{c.correction_id}</b> — Target File: <i>{c.file_path}</i><br/>"
                        f"<b>Reason:</b> {c.reason}",
                        normal_style,
                    )
                )
                story.append(Spacer(1, 4))
                diff_snip = "<br/>".join(c.unified_diff.splitlines()[:6])
                story.append(Paragraph(f"<font face='Courier' size=7>{diff_snip}</font>", code_style))
                story.append(Spacer(1, 6))

        doc.build(story)
        return buffer.getvalue()


report_engine = ReportEngine()
