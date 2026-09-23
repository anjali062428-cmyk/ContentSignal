"""
Evidence Center Export Router.
Generates executive-ready PDF, Word (DOCX), and Excel (XLSX) reports
grounded strictly in real dataset-backed analytics.
"""
import io
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from backend.database import get_db
from backend.models import Page, PageMetric, Opportunity, WatchlistItem, ImpactAction
from backend.auth import get_optional_current_user

# ReportLab (PDF)
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

# python-docx (Word)
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

# openpyxl (Excel)
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

router = APIRouter(prefix="/api/export", tags=["Export & Evidence Center"])


def get_dataset_summary(db: Session, target_ds: str) -> Dict[str, Any]:
    total_pages = db.query(Page).filter(Page.dataset_id == target_ds).count()
    critical = db.query(Opportunity).filter(Opportunity.dataset_id == target_ds, Opportunity.priority == "CRITICAL").count()
    high = db.query(Opportunity).filter(Opportunity.dataset_id == target_ds, Opportunity.priority == "HIGH").count()
    refresh_count = db.query(Opportunity).filter(Opportunity.dataset_id == target_ds, Opportunity.action == "REFRESH").count()
    optimize_count = db.query(Opportunity).filter(Opportunity.dataset_id == target_ds, Opportunity.action == "OPTIMIZE").count()
    protect_count = db.query(Opportunity).filter(Opportunity.dataset_id == target_ds, Opportunity.action == "PROTECT").count()
    
    return {
        "dataset_id": target_ds,
        "total_pages": total_pages,
        "critical": critical,
        "high": high,
        "refresh_count": refresh_count,
        "optimize_count": optimize_count,
        "protect_count": protect_count,
        "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    }


def get_top_opportunities_data(db: Session, target_ds: str, limit: int = 50) -> List[Dict[str, Any]]:
    results = (
        db.query(Opportunity, Page, PageMetric)
        .join(Page, Opportunity.page_id == Page.page_id)
        .join(PageMetric, Page.page_id == PageMetric.page_id)
        .filter(Opportunity.dataset_id == target_ds)
        .order_by(desc(Opportunity.opportunity_score))
        .limit(limit)
        .all()
    )
    rows = []
    for opp, p, m in results:
        rows.append({
            "rank": opp.queue_rank or 0,
            "page_id": opp.page_id,
            "title": p.page_title or opp.page_id,
            "url": p.url or f"/{opp.page_id}",
            "score": round(float(opp.opportunity_score or 0), 1),
            "priority": opp.priority,
            "action": opp.action,
            "primary_reason": opp.primary_reason or "",
            "visibility": int(m.impressions_90d or 0),
            "clicks": int(m.clicks_90d or 0),
            "ctr": f"{float(m.ctr or 0):.1f}%",
            "position": round(float(m.avg_position or 0), 1),
            "freshness_days": int(p.days_since_last_update or 0),
            "content_type": p.content_type or "article",
        })
    return rows


@router.get("/evidence/pdf")
def export_evidence_pdf(
    dataset_id: Optional[str] = Query("starter-flyrank"),
    limit: int = Query(35, ge=5, le=200),
    db: Session = Depends(get_db),
):
    target_ds = dataset_id or "starter-flyrank"
    summary = get_dataset_summary(db, target_ds)
    opps = get_top_opportunities_data(db, target_ds, limit)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()
    primary_color = colors.HexColor("#1E293B")
    accent_color = colors.HexColor("#3B82F6")
    critical_color = colors.HexColor("#DC2626")
    high_color = colors.HexColor("#D97706")
    muted_color = colors.HexColor("#64748B")

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontSize=20,
        leading=24,
        textColor=primary_color,
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontSize=10,
        textColor=muted_color,
        spaceAfter=14,
    )
    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontSize=13,
        leading=16,
        textColor=primary_color,
        spaceBefore=12,
        spaceAfter=6,
    )
    cell_style = ParagraphStyle(
        "CellText",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#0F172A"),
    )
    cell_bold = ParagraphStyle(
        "CellBold",
        parent=cell_style,
        fontName="Helvetica-Bold",
    )

    elements = []

    # Title & Metadata
    elements.append(Paragraph("ContentSignal — Executive Intelligence Report", title_style))
    elements.append(Paragraph(
        f"Dataset: <b>{summary['dataset_id']}</b> &nbsp;|&nbsp; Generated: {summary['generated_at']} &nbsp;|&nbsp; Scope: Top {len(opps)} Priority Directives",
        subtitle_style
    ))
    elements.append(Spacer(1, 8))

    # Executive KPI Summary Table
    kpi_data = [
        [
            Paragraph("<b>Total Pages</b>", cell_bold),
            Paragraph("<b>Critical Priority</b>", cell_bold),
            Paragraph("<b>High Priority</b>", cell_bold),
            Paragraph("<b>Refresh Queue</b>", cell_bold),
            Paragraph("<b>Optimize (CTR)</b>", cell_bold),
        ],
        [
            Paragraph(f"{summary['total_pages']:,}", cell_style),
            Paragraph(f"<font color='{critical_color.hexval()}'>{summary['critical']:,}</font>", cell_bold),
            Paragraph(f"<font color='{high_color.hexval()}'>{summary['high']:,}</font>", cell_bold),
            Paragraph(f"{summary['refresh_count']:,}", cell_style),
            Paragraph(f"{summary['optimize_count']:,}", cell_style),
        ]
    ]
    t_kpi = Table(kpi_data, colWidths=[108, 108, 108, 108, 108])
    t_kpi.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
    ]))
    elements.append(t_kpi)
    elements.append(Spacer(1, 14))

    # Opportunities Table
    elements.append(Paragraph("Priority Action Queue & Supporting Evidence", section_heading))
    table_data = [[
        Paragraph("<b>#</b>", cell_bold),
        Paragraph("<b>Page / Target URL</b>", cell_bold),
        Paragraph("<b>Score</b>", cell_bold),
        Paragraph("<b>Priority</b>", cell_bold),
        Paragraph("<b>Action</b>", cell_bold),
        Paragraph("<b>Visibility</b>", cell_bold),
        Paragraph("<b>CTR</b>", cell_bold),
        Paragraph("<b>Pos</b>", cell_bold),
    ]]

    for it in opps:
        p_color = critical_color if it["priority"] == "CRITICAL" else (high_color if it["priority"] == "HIGH" else muted_color)
        table_data.append([
            Paragraph(str(it["rank"]), cell_style),
            Paragraph(f"<b>{it['title'][:36]}</b><br/><font color='#64748B'>{it['url'][:42]}</font>", cell_style),
            Paragraph(f"<b>{it['score']}</b>", cell_bold),
            Paragraph(f"<font color='{p_color.hexval()}'><b>{it['priority']}</b></font>", cell_style),
            Paragraph(it["action"], cell_style),
            Paragraph(f"{it['visibility']:,}", cell_style),
            Paragraph(it["ctr"], cell_style),
            Paragraph(str(it["position"]), cell_style),
        ])

    opp_table = Table(table_data, colWidths=[24, 210, 42, 58, 64, 54, 44, 44], repeatRows=1)
    opp_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E293B")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#94A3B8")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
    ]))
    for i in range(1, len(table_data)):
        if i % 2 == 0:
            opp_table.setStyle(TableStyle([('BACKGROUND', (0, i), (-1, i), colors.HexColor("#F8FAFC"))]))

    elements.append(opp_table)

    # Build PDF
    doc.build(elements)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=contentsignal_report_{target_ds}.pdf"}
    )


@router.get("/evidence/docx")
def export_evidence_docx(
    dataset_id: Optional[str] = Query("starter-flyrank"),
    limit: int = Query(50, ge=5, le=200),
    db: Session = Depends(get_db),
):
    target_ds = dataset_id or "starter-flyrank"
    summary = get_dataset_summary(db, target_ds)
    opps = get_top_opportunities_data(db, target_ds, limit)

    doc = docx.Document()

    # Set document margins
    for section in doc.sections:
        section.top_margin = Inches(0.75)
        section.bottom_margin = Inches(0.75)
        section.left_margin = Inches(0.75)
        section.right_margin = Inches(0.75)

    # Title
    title = doc.add_heading(level=0)
    run_title = title.add_run("ContentSignal — Executive Intelligence Report")
    run_title.font.name = 'Calibri'
    run_title.font.size = Pt(22)
    run_title.font.bold = True
    run_title.font.color.rgb = RGBColor(30, 41, 59)

    # Subtitle
    meta_p = doc.add_paragraph()
    meta_p.add_run(f"Dataset: {summary['dataset_id']}  |  Generated: {summary['generated_at']}  |  Scope: Top {len(opps)} Priority Pages").italic = True

    # Executive Overview
    doc.add_heading("1. Executive Summary & KPIs", level=1)
    kpi_p = doc.add_paragraph()
    kpi_p.add_run(
        f"The ContentSignal Engine evaluated {summary['total_pages']:,} pages across this snapshot. "
        f"A total of {summary['critical']:,} pages have reached CRITICAL status with imminent decay signals, "
        f"and {summary['high']:,} pages represent HIGH priority opportunities. "
        f"Recommended editorial interventions include {summary['refresh_count']:,} content refreshes and "
        f"{summary['optimize_count']:,} search snippet optimizations."
    )

    # Table of KPIs
    kpi_table = doc.add_table(rows=2, cols=5)
    kpi_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers = ["Total Pages", "Critical Pages", "High Priority", "Refresh Queue", "Optimize (CTR)"]
    for col_idx, header in enumerate(headers):
        cell = kpi_table.cell(0, col_idx)
        cell.text = header
        cell.paragraphs[0].runs[0].font.bold = True

    vals = [
        f"{summary['total_pages']:,}",
        f"{summary['critical']:,}",
        f"{summary['high']:,}",
        f"{summary['refresh_count']:,}",
        f"{summary['optimize_count']:,}",
    ]
    for col_idx, val in enumerate(vals):
        kpi_table.cell(1, col_idx).text = val

    # Opportunities
    doc.add_heading("2. High-Impact Action Queue", level=1)
    opp_table = doc.add_table(rows=1, cols=7)
    opp_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    col_names = ["Rank", "Page / Title", "Score", "Priority", "Action", "Visibility", "CTR"]
    for c_idx, name in enumerate(col_names):
        cell = opp_table.cell(0, c_idx)
        cell.text = name
        cell.paragraphs[0].runs[0].font.bold = True

    for item in opps:
        row = opp_table.add_row()
        row.cells[0].text = str(item["rank"])
        row.cells[1].text = item["title"][:40]
        row.cells[2].text = str(item["score"])
        row.cells[3].text = item["priority"]
        row.cells[4].text = item["action"]
        row.cells[5].text = f"{item['visibility']:,}"
        row.cells[6].text = item["ctr"]

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename=contentsignal_report_{target_ds}.docx"}
    )


@router.get("/evidence/xlsx")
def export_evidence_xlsx(
    dataset_id: Optional[str] = Query("starter-flyrank"),
    limit: int = Query(250, ge=10, le=1000),
    db: Session = Depends(get_db),
):
    target_ds = dataset_id or "starter-flyrank"
    summary = get_dataset_summary(db, target_ds)
    opps = get_top_opportunities_data(db, target_ds, limit)

    wb = openpyxl.Workbook()

    # Sheet 1: Executive Summary
    ws_summary = wb.active
    ws_summary.title = "Executive Summary"
    
    header_font = Font(name="Segoe UI", size=14, bold=True, color="1E293B")
    sub_font = Font(name="Segoe UI", size=10, italic=True, color="64748B")
    bold_font = Font(name="Segoe UI", size=10, bold=True)
    regular_font = Font(name="Segoe UI", size=10)

    ws_summary["A1"] = "ContentSignal — Executive Intelligence Summary"
    ws_summary["A1"].font = header_font
    ws_summary["A2"] = f"Dataset: {summary['dataset_id']} | Generated: {summary['generated_at']}"
    ws_summary["A2"].font = sub_font

    ws_summary["A4"] = "Metric"
    ws_summary["B4"] = "Value"
    ws_summary["A4"].font = bold_font
    ws_summary["B4"].font = bold_font

    kpi_rows = [
        ("Total Pages Analyzed", summary["total_pages"]),
        ("Critical Priority Pages", summary["critical"]),
        ("High Priority Opportunities", summary["high"]),
        ("Recommended Refreshes", summary["refresh_count"]),
        ("Recommended CTR Optimizations", summary["optimize_count"]),
        ("Recommended Content Protections", summary["protect_count"]),
    ]
    for idx, (lbl, val) in enumerate(kpi_rows, start=5):
        ws_summary[f"A{idx}"] = lbl
        ws_summary[f"B{idx}"] = val
        ws_summary[f"A{idx}"].font = regular_font
        ws_summary[f"B{idx}"].font = bold_font

    ws_summary.column_dimensions["A"].width = 32
    ws_summary.column_dimensions["B"].width = 16

    # Sheet 2: Opportunities
    ws_opps = wb.create_sheet(title="Opportunities Queue")
    headers = [
        "Rank", "Page ID", "Title", "URL", "Score", "Priority", "Action",
        "Primary Reason", "Visibility (90d)", "Clicks (90d)", "CTR", "Position", "Days Since Update"
    ]
    ws_opps.append(headers)

    header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    header_font_white = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")

    for col_idx in range(1, len(headers) + 1):
        cell = ws_opps.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font_white
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for item in opps:
        ws_opps.append([
            item["rank"],
            item["page_id"],
            item["title"],
            item["url"],
            item["score"],
            item["priority"],
            item["action"],
            item["primary_reason"],
            item["visibility"],
            item["clicks"],
            item["ctr"],
            item["position"],
            item["freshness_days"],
        ])

    # Auto-size columns
    for col in ws_opps.columns:
        col_letter = get_column_letter(col[0].column)
        max_len = max(len(str(cell.value or '')) for cell in col)
        ws_opps.column_dimensions[col_letter].width = min(max(max_len + 3, 10), 45)

    # Sheet 3: Starred Watchlist & Marked Actions
    ws_watch = wb.create_sheet(title="Watchlist & Actions")
    watch_headers = ["Action ID", "Page ID", "Action Type", "Status", "Marked Date", "Notes"]
    ws_watch.append(watch_headers)
    for col_idx in range(1, len(watch_headers) + 1):
        cell = ws_watch.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font_white

    actions = (
        db.query(ImpactAction)
        .filter(ImpactAction.dataset_id == target_ds)
        .order_by(ImpactAction.marked_at.desc())
        .all()
    )
    for act in actions:
        ws_watch.append([
            act.id,
            act.page_id,
            act.action_type,
            act.status,
            act.marked_at.strftime("%Y-%m-%d %H:%M") if act.marked_at else "",
            act.notes or "",
        ])

    for col in ws_watch.columns:
        col_letter = get_column_letter(col[0].column)
        max_len = max(len(str(cell.value or '')) for cell in col)
        ws_watch.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 40)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=contentsignal_evidence_{target_ds}.xlsx"}
    )
