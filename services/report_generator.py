import csv
import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
)

# Brand colours
_NAVY = colors.HexColor('#274665')
_ORANGE = colors.HexColor('#FF6600')
_WHITE = colors.white
_LIGHT = colors.HexColor('#F0F4F8')


def generate_csv(records) -> str:
    """
    Return a CSV string built from a list of DetectionHistory records.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Article Snippet', 'Prediction', 'Confidence (%)', 'Detected At'])
    for r in records:
        writer.writerow([
            r.id,
            r.article_snippet or '',
            r.prediction or 'N/A',
            f'{round(r.confidence * 100, 1)}' if r.confidence is not None else 'N/A',
            r.detected_at.strftime('%Y-%m-%d %H:%M:%S') if r.detected_at else 'N/A',
        ])
    return output.getvalue()


def generate_pdf(records, title: str = 'Detection Report', date_range: str = '') -> bytes:
    """
    Return PDF bytes containing a branded report of the supplied detection records.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
    )
    styles = getSampleStyleSheet()
    elements = []

    # ----- Header -----
    title_style = ParagraphStyle(
        'BrandTitle',
        parent=styles['Title'],
        textColor=_NAVY,
        fontSize=20,
        spaceAfter=4,
    )
    sub_style = ParagraphStyle(
        'BrandSub',
        parent=styles['Normal'],
        textColor=_ORANGE,
        fontSize=10,
        spaceAfter=2,
    )
    elements.append(Paragraph(title, title_style))
    if date_range:
        elements.append(Paragraph(f'Period: {date_range}', sub_style))
    elements.append(
        Paragraph(
            f'Generated on: {datetime.now().strftime("%B %d, %Y at %H:%M")}',
            styles['Normal'],
        )
    )
    elements.append(Spacer(1, 0.25 * inch))

    # ----- Summary stats -----
    total = len(records)
    fake_count = sum(1 for r in records if r.prediction == 'Fake')
    real_count = sum(1 for r in records if r.prediction == 'Real')
    other_count = total - fake_count - real_count

    summary_data = [
        ['Total Detections', 'Fake News', 'Real News', 'Uncertain / Invalid'],
        [str(total), str(fake_count), str(real_count), str(other_count)],
    ]
    summary_table = Table(summary_data, colWidths=[1.7 * inch] * 4)
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), _NAVY),
        ('TEXTCOLOR', (0, 0), (-1, 0), _WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 1), (-1, -1), _LIGHT),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica-Bold'),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 0.25 * inch))

    # ----- Main detections table -----
    table_data = [['#', 'Article Snippet', 'Prediction', 'Confidence', 'Date']]
    for i, r in enumerate(records, start=1):
        snippet = r.article_snippet or ''
        if len(snippet) > 80:
            snippet = snippet[:77] + '...'
        conf_str = f'{round(r.confidence * 100, 1)}%' if r.confidence is not None else 'N/A'
        date_str = r.detected_at.strftime('%Y-%m-%d') if r.detected_at else 'N/A'
        table_data.append([str(i), snippet, r.prediction or 'N/A', conf_str, date_str])

    col_widths = [0.4 * inch, 3.2 * inch, 1.0 * inch, 1.0 * inch, 0.9 * inch]
    main_table = Table(table_data, colWidths=col_widths, repeatRows=1)

    row_count = len(table_data)
    row_bg = []
    for row_idx in range(1, row_count):
        bg = _LIGHT if row_idx % 2 == 0 else _WHITE
        row_bg.append(('BACKGROUND', (0, row_idx), (-1, row_idx), bg))

    main_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), _NAVY),
        ('TEXTCOLOR', (0, 0), (-1, 0), _WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.lightgrey),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ] + row_bg))

    elements.append(main_table)

    doc.build(elements)
    return buffer.getvalue()
