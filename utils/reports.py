"""
Report generator - produces printable PDF previews.
"""
import tkinter as tk
from tkinter import messagebox
import tempfile, os
from datetime import datetime

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                    Paragraph, Spacer)
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    HAS_RL = True
except ImportError:
    HAS_RL = False


def _get_font():
    candidates = [
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\calibri.ttf",
        r"C:\Windows\Fonts\times.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                pdfmetrics.registerFont(TTFont("UniFont", p))
                return "UniFont"
            except Exception:
                pass
    return "Helvetica"


def generate_report(title: str, columns: list[str], rows: list,
                    parent=None, extra_info: str = ""):

    if not HAS_RL:
        messagebox.showerror("Помилка",
                             "Бібліотека reportlab не встановлена.\n"
                             "pip install reportlab", parent=parent)
        return

    font = _get_font()

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False,
                                     prefix="zlagoda_report_") as f:
        path = f.name

    doc = SimpleDocTemplate(path, pagesize=A4,
                            leftMargin=1.5*cm, rightMargin=1.5*cm,
                            topMargin=2*cm, bottomMargin=2*cm)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("ZTitle",
                                  fontName=font, fontSize=14,
                                  spaceAfter=6, textColor=colors.HexColor("#2B6CB0"),
                                  alignment=1)
    info_style  = ParagraphStyle("ZInfo",
                                  fontName=font, fontSize=9,
                                  textColor=colors.grey, alignment=1)
    cell_style  = ParagraphStyle("ZCell",
                                  fontName=font, fontSize=8)

    story = []
    story.append(Paragraph("АІС «ZLAGODA»", title_style))
    story.append(Paragraph(title, title_style))

    ts = datetime.now().strftime("%d.%m.%Y %H:%M")
    info = f"Дата формування: {ts}"
    if extra_info:
        info += f"  |  {extra_info}"
    story.append(Paragraph(info, info_style))
    story.append(Spacer(1, 0.4*cm))

    #Build table data
    def to_str(v):
        if v is None:
            return ""
        return str(v)

    header = [Paragraph(c, ParagraphStyle("H", fontName=font, fontSize=8,
                                           textColor=colors.white,
                                           fontWeight="BOLD"))
              for c in columns]
    data = [header]
    for r in rows:
        if hasattr(r, "keys"):
            vals = [Paragraph(to_str(r[k]), cell_style) for k in r.keys()]
        else:
            vals = [Paragraph(to_str(v), cell_style) for v in r]
        data.append(vals)

    n_cols = len(columns)
    page_w = A4[0] - 3*cm
    col_w  = page_w / n_cols

    tbl = Table(data, colWidths=[col_w]*n_cols, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,0),  colors.HexColor("#1A4F8C")),
        ("TEXTCOLOR",   (0,0), (-1,0),  colors.white),
        ("ALIGN",       (0,0), (-1,-1), "LEFT"),
        ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
        ("FONTNAME",    (0,0), (-1,-1), font),
        ("FONTSIZE",    (0,0), (-1,-1), 8),
        ("ROWBACKGROUNDS", (0,1), (-1,-1),
         [colors.HexColor("#EBF8FF"), colors.white]),
        ("GRID",        (0,0), (-1,-1), 0.4, colors.HexColor("#90CDF4")),
        ("BOTTOMPADDING",(0,0),(-1,-1), 4),
        ("TOPPADDING",  (0,0), (-1,-1), 4),
    ]))
    story.append(tbl)

    #Footer via onLaterPages
    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont(font, 7)
        canvas.setFillColor(colors.grey)
        canvas.drawString(1.5*cm, 1.2*cm,
                          f"АІС «ZLAGODA» | {ts}")
        canvas.drawRightString(A4[0]-1.5*cm, 1.2*cm,
                               f"Стор. {doc.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)

    #Open with system viewer
    _open_pdf(path, parent)


def _open_pdf(path: str, parent=None):
    try:
        os.startfile(path)
    except Exception as e:
        messagebox.showinfo("Звіт збережено",
                            f"PDF збережено:\n{path}\n({e})", parent=parent)
