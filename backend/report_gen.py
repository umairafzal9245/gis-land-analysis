"""PDF report generator for GIS Land Analysis.

Generates professional PDF reports from selection summaries using
SUBTYPE-based LANDUSE_CATEGORY breakdowns.
"""
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


def generate_pdf_report(stats: dict, report_text: str = "") -> bytes:
    """Generate a PDF report from selection summary.
    
    Args:
        stats: Selection summary with breakdown by LANDUSE_CATEGORY
        report_text: LLM-generated report text to include
        
    Returns:
        PDF file as bytes
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.whitesmoke,
        backColor=colors.HexColor('#1a365d'),
        alignment=1,
        spaceAfter=20,
        spaceBefore=10,
        leftIndent=10,
        rightIndent=10,
        leading=30,
    )
    
    section_style = ParagraphStyle(
        'SectionStyle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#1a365d'),
        spaceAfter=10,
        spaceBefore=15,
    )
    
    body_style = ParagraphStyle(
        'BodyStyle',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        spaceAfter=6,
    )
    
    story = []
    
    # ==========================================================================
    # Title
    # ==========================================================================
    story.append(Paragraph("GIS Land Analysis Report", title_style))
    story.append(Spacer(1, 20))
    
    # ==========================================================================
    # Summary Statistics Table
    # ==========================================================================
    story.append(Paragraph("Summary Statistics", section_style))
    
    summary_data = [
        ["Metric", "Value"],
        ["Total Parcels", f"{stats.get('total_parcels', 0):,}"],
        ["Total Area", f"{stats.get('total_area_m2', 0):,.0f} m²"],
        ["Vacant Parcels", f"{stats.get('vacant_count', 0):,}"],
        ["Developed Parcels", f"{stats.get('developed_count', 0):,}"],
        ["Commercial Area", f"{stats.get('commercial_total_area_m2', 0):,.0f} m²"],
        ["Non-Commercial Area", f"{stats.get('non_commercial_total_area_m2', 0):,.0f} m²"],
        ["Religious Capacity", f"{stats.get('total_religious_capacity', 0):,} worshippers"],
        ["Estimated Shops", f"{stats.get('total_shops_estimated', 0):,} units"],
        ["Blocks Covered", f"{len(stats.get('block_ids_covered', [])):,}"],
    ]
    
    summary_table = Table(summary_data, colWidths=[250, 200])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a365d')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f7fafc')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e0')),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
    ]))
    
    story.append(summary_table)
    story.append(Spacer(1, 20))
    
    # ==========================================================================
    # Land Use Breakdown Table (SUBTYPE-based LANDUSE_CATEGORY)
    # ==========================================================================
    story.append(Paragraph("Land Use Breakdown by Category", section_style))
    
    breakdown = stats.get("breakdown", {})
    
    if breakdown:
        breakdown_data = [["Category", "Count", "Area (m²)", "Capacity Est."]]
        
        # Sort categories by count descending
        sorted_categories = sorted(
            breakdown.items(),
            key=lambda x: x[1].get("count", 0),
            reverse=True
        )
        
        for category, data in sorted_categories:
            count = data.get("count", 0)
            area = data.get("total_area_m2", 0)
            capacity = data.get("total_capacity_estimated", 0)
            shops = data.get("total_shops_estimated", 0)
            
            # Show capacity or shops depending on type
            if capacity > 0:
                cap_text = f"{capacity:,}"
            elif shops > 0:
                cap_text = f"{shops:,} shops"
            else:
                cap_text = "-"
            
            breakdown_data.append([
                category,
                f"{count:,}",
                f"{area:,.0f}",
                cap_text
            ])
        
        breakdown_table = Table(breakdown_data, colWidths=[150, 80, 120, 100])
        breakdown_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5282')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#edf2f7')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#a0aec0')),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#edf2f7'), colors.white]),
        ]))
        
        story.append(breakdown_table)
    else:
        story.append(Paragraph("No category breakdown available.", body_style))
    
    story.append(Spacer(1, 20))
    
    # ==========================================================================
    # LLM Report Text
    # ==========================================================================
    if report_text:
        story.append(PageBreak())
        story.append(Paragraph("Analysis Report", section_style))
        story.append(Spacer(1, 10))
        
        # Split report into paragraphs and format
        for line in report_text.split('\n'):
            line = line.strip()
            if not line:
                story.append(Spacer(1, 6))
            elif line.startswith('#') or line.isupper() or line.endswith(':'):
                # Treat as sub-heading
                clean_line = line.lstrip('#').strip()
                story.append(Spacer(1, 10))
                story.append(Paragraph(clean_line, section_style))
            else:
                # Regular paragraph - escape XML special chars
                safe_line = (
                    line.replace('&', '&amp;')
                    .replace('<', '&lt;')
                    .replace('>', '&gt;')
                )
                story.append(Paragraph(safe_line, body_style))
    
    # ==========================================================================
    # Footer note
    # ==========================================================================
    story.append(Spacer(1, 30))
    footer_style = ParagraphStyle(
        'FooterStyle',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.gray,
        alignment=1,
    )
    story.append(Paragraph(
        "Generated by GIS Land Analysis System | SUBTYPE-based Classification",
        footer_style
    ))
    
    doc.build(story)
    return buffer.getvalue()
