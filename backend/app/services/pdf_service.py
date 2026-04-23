"""
PDF receipt generation — matches Medical Receipt Template (Style 1).
Uses ReportLab with BaseDocTemplate + Frame for accurate band rendering.

Key design decisions:
- Rs. currency: ReportLab built-in fonts cannot render the ₹ Unicode glyph (U+20B9).
- Logo: Stored as a base64 data-URL in the DB (no file-system dependency).
- No square brackets around data values.
"""

from __future__ import annotations

import base64
import os
import re
from datetime import datetime
from io import BytesIO
from typing import Optional

from reportlab.lib import colors, utils
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame,
    Table, TableStyle, Paragraph, Spacer, Image, HRFlowable, KeepTogether,
)

from app.core.config import get_settings

settings = get_settings()

# ── Brand colours ────────────────────────────────────────────────────────
BLUE_DARK = colors.HexColor("#1A4882")
BLUE_MID  = colors.HexColor("#5B9BD5")
GREY_ROW  = colors.HexColor("#F2F2F2")
GREY_BAL  = colors.HexColor("#C0C0C0")
LOGO_BG   = colors.HexColor("#DEEAF1")
TEXT_DARK = colors.HexColor("#1A1A2E")
TEXT_MID  = colors.HexColor("#444444")
TEXT_GREY = colors.HexColor("#666666")

PW, PH   = A4          # 595.27 × 841.89 pts
BAND_H   = 25 * mm     # top / bottom blue band
MARGIN   = 20 * mm     # left / right page margin
CONTENT_W = PW - 2 * MARGIN


# ── Canvas callback: paint blue bands behind content ─────────────────────
def _draw_bands(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(BLUE_DARK)
    canvas.rect(0, PH - BAND_H, PW, BAND_H, fill=1, stroke=0)  # top
    canvas.rect(0, 0,           PW, BAND_H, fill=1, stroke=0)   # bottom
    canvas.restoreState()


# ── Style factory ────────────────────────────────────────────────────────
def _s(name: str, **kw) -> ParagraphStyle:
    """Create a named ParagraphStyle inheriting from Normal."""
    base = getSampleStyleSheet()["Normal"]
    return ParagraphStyle(name, parent=base, **kw)


# ── XML sanitiser — prevents ReportLab Paragraph injection ──────────────
def _strip_xml(text) -> str:
    """Remove all XML/HTML tags from user-supplied text before PDF rendering."""
    if not text:
        return "\u2014"
    return re.sub(r'<[^>]+>', '', str(text)).strip() or "\u2014"


# ── Rupee helper ─────────────────────────────────────────────────────────
def _rs(amount: float) -> str:
    """Format as Indian currency — uses 'Rs.' because ReportLab built-in
    fonts cannot render the ₹ Unicode glyph (U+20B9)."""
    return f"Rs. {amount:,.2f}"


# ── Logo loader ───────────────────────────────────────────────────────────
def _load_logo(logo_url: Optional[str], w=18 * mm, h=18 * mm) -> Optional[Image]:
    """
    Load the clinic logo from either:
    - A base64 data-URL (data:image/png;base64,...) — stored in DB
    - An absolute filesystem path
    - A relative path from UPLOAD_DIR or CWD
    """
    if not logo_url:
        return None

    # ── 1. Base64 data-URL (preferred — no filesystem needed)
    if logo_url.startswith("data:"):
        try:
            header, b64data = logo_url.split(",", 1)
            raw = base64.b64decode(b64data)
            buf = BytesIO(raw)
            # Use ImageReader for robust format detection from buffer
            img_reader = ImageReader(buf)
            return Image(img_reader, width=w, height=h)
        except Exception:
            return None

    # ── 2. Absolute path on disk
    if os.path.isabs(logo_url) and os.path.exists(logo_url):
        try:
            return Image(logo_url, width=w, height=h)
        except Exception:
            return None

    # ── 3. Relative path — try several roots
    for base_dir in [
        os.path.dirname(os.path.abspath(settings.UPLOAD_DIR)),
        os.getcwd(),
    ]:
        candidate = os.path.join(base_dir, logo_url)
        if os.path.exists(candidate):
            try:
                return Image(candidate, width=w, height=h)
            except Exception:
                return None

    return None


# ── Logo placeholder ─────────────────────────────────────────────────────
def _logo_placeholder(w=18 * mm, h=18 * mm) -> Table:
    cell = Table(
        [[Paragraph("<b>YOUR<br/>LOGO</b>",
                    _s("_LP", fontSize=7, alignment=TA_CENTER, textColor=TEXT_MID))]],
        colWidths=[w], rowHeights=[h],
    )
    cell.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LOGO_BG),
        ("BOX",        (0, 0), (-1, -1), 0.8, colors.HexColor("#90A8BE")),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
    ]))
    return cell


# ── Section header helper ─────────────────────────────────────────────────
def _section_hdr(title: str) -> list:
    return [
        Paragraph(title, _s("_SH", fontSize=8, fontName="Helvetica-Bold",
                             textColor=BLUE_DARK)),
        HRFlowable(width="100%", thickness=1, color=BLUE_MID,
                   spaceBefore=1, spaceAfter=3),
    ]


# ── Main generator ────────────────────────────────────────────────────────
def generate_receipt_pdf(
    bill_data: dict,
    tenant_data: dict,
    patient_data: dict,
    doctor_data: Optional[dict],
    items_data: list[dict],
    output_path: Optional[str] = None,
) -> bytes:
    """
    Generate a professional PDF receipt matching the provided Word template.
    Returns raw PDF bytes. Optionally persists to *output_path*.
    """
    buffer = BytesIO()

    # Leave room for coloured bands
    frame = Frame(
        MARGIN,
        BAND_H + 6 * mm,
        CONTENT_W,
        PH - 2 * BAND_H - 12 * mm,
        leftPadding=0, rightPadding=0,
        topPadding=0, bottomPadding=0,
    )
    tpl = PageTemplate(id="receipt", frames=[frame], onPage=_draw_bands)
    doc = BaseDocTemplate(buffer, pagesize=A4, pageTemplates=[tpl])

    els = []

    # ── 1. HEADER ────────────────────────────────────────────────────────
    LOGO_W = 20 * mm
    LOGO_H = 20 * mm

    logo_img = _load_logo(tenant_data.get("logo_url"), LOGO_W, LOGO_H)
    logo_cell = logo_img if logo_img else _logo_placeholder(LOGO_W, LOGO_H)

    inst_name  = _strip_xml(tenant_data.get("name"))    if tenant_data.get("name")    else "Medical Institution Name"
    inst_addr  = _strip_xml(tenant_data.get("address")) if tenant_data.get("address") else "Medical Institution Address"
    inst_email = _strip_xml(tenant_data.get("email"))   if tenant_data.get("email")   else "Medical Institution Email"
    inst_phone = _strip_xml(tenant_data.get("phone"))   if tenant_data.get("phone")   else "Medical Institution Contact No."

    sv_grey = _s("_IG", fontSize=8, textColor=TEXT_GREY, leading=11)

    left_col = [
        logo_cell,
        Spacer(1, 2 * mm),
        Paragraph(inst_name,  _s("_IN", fontSize=10, fontName="Helvetica-Bold",
                                  textColor=TEXT_DARK)),
        Paragraph(inst_addr,  sv_grey),
        Paragraph(inst_email, sv_grey),
        Paragraph(inst_phone, sv_grey),
    ]

    # Date
    raw_dt = bill_data.get("created_at", "")
    date_str = (raw_dt.strftime("%d %B %Y")
                if isinstance(raw_dt, datetime) else str(raw_dt)[:10])

    bill_no = bill_data.get("bill_number", "")

    s_lbl = _s("_HL", fontSize=7, fontName="Helvetica-Bold",
                textColor=BLUE_DARK, alignment=TA_RIGHT)
    s_val = _s("_HV", fontSize=9, textColor=TEXT_DARK, alignment=TA_RIGHT)

    right_col = [
        Paragraph("RECEIPT", _s("_RT", fontSize=22, fontName="Helvetica-Bold",
                                  textColor=colors.HexColor("#AAAAAA"),
                                  alignment=TA_RIGHT)),
        Spacer(1, 3 * mm),
        Paragraph("DATE",        s_lbl),
        HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey,
                   spaceBefore=1, spaceAfter=1),
        Paragraph(date_str,      s_val),
        Spacer(1, 2 * mm),
        Paragraph("RECEIPT NO.", s_lbl),
        HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey,
                   spaceBefore=1, spaceAfter=1),
        Paragraph(bill_no,       s_val),
    ]

    hdr_tbl = Table([[left_col, right_col]],
                    colWidths=[CONTENT_W * 0.52, CONTENT_W * 0.48])
    hdr_tbl.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    els.append(hdr_tbl)
    els.append(Spacer(1, 4 * mm))
    els.append(HRFlowable(width="100%", thickness=0.6,
                           color=colors.HexColor("#CCCCCC"), spaceAfter=4 * mm))

    # ── 2. PATIENT / PRACTITIONER ────────────────────────────────────────
    sv = _s("_SV", fontSize=8, textColor=TEXT_MID, leading=12)

    p_name  = _strip_xml(patient_data.get("name"))    if patient_data.get("name")    else "Customer Name"
    p_addr  = _strip_xml(patient_data.get("address")) if patient_data.get("address") else "Customer Address"
    p_email = _strip_xml(patient_data.get("email"))   if patient_data.get("email")   else "Customer Email"
    p_phone = _strip_xml(patient_data.get("phone"))   if patient_data.get("phone")   else "Customer Contact No."

    patient_blk = _section_hdr("Patient Information") + [
        Paragraph(p_name,  sv),
        Paragraph(p_addr,  sv),
        Paragraph(p_email, sv),
        Paragraph(p_phone, sv),
    ]

    d_name  = f"Dr. {_strip_xml(doctor_data['name'])}"              if doctor_data else "Practitioner Name"
    d_lic   = _strip_xml(doctor_data.get("license_number")) or "\u2014"  if doctor_data else "Practitioner License"
    d_title = _strip_xml(doctor_data.get("specialization")) or "\u2014"  if doctor_data else "Practitioner Title"

    prac_blk = _section_hdr("Practitioner Information") + [
        Paragraph(d_name,  sv),
        Paragraph(d_lic,   sv),
        Paragraph(d_title, sv),
    ]

    COL = CONTENT_W * 0.47
    GAP = CONTENT_W * 0.06
    pp_tbl = Table([[patient_blk, Spacer(GAP, 1), prac_blk]],
                   colWidths=[COL, GAP, COL])
    pp_tbl.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    els.append(pp_tbl)
    els.append(Spacer(1, 5 * mm))

    # ── 3. SERVICES TABLE ─────────────────────────────────────────────────
    th  = _s("_TH",  fontSize=8, fontName="Helvetica-Bold",
              textColor=colors.white, alignment=TA_CENTER)
    thl = _s("_THL", fontSize=8, fontName="Helvetica-Bold",
              textColor=colors.white, alignment=TA_LEFT)
    tbc = _s("_TBC", fontSize=8, textColor=TEXT_MID, alignment=TA_CENTER)
    tbl_l = _s("_TBL", fontSize=8, textColor=TEXT_MID, alignment=TA_LEFT)

    BLANK_ROWS = max(6, len(items_data) + 2)

    svc_data = [[
        Paragraph("Code",                                             th),
        Paragraph("Description of Service / Treatment / Medicine",   thl),
        Paragraph("Rate / Charge",                                    th),
        Paragraph("Line Total",                                       th),
    ]]

    for i in range(BLANK_ROWS):
        if i < len(items_data):
            it   = items_data[i]
            # Use stored code directly; fall back to CST-### if none
            code = _strip_xml(it.get("code")) if it.get("code") else f"CST-{i + 1:03d}"
            svc_data.append([
                Paragraph(code,                                          tbc),
                Paragraph(_strip_xml(it.get("description", "")),        tbl_l),
                Paragraph(_rs(float(it.get("unit_price", 0))),           tbc),
                Paragraph(_rs(float(it.get("total", 0))),                tbc),
            ])
        else:
            svc_data.append([Paragraph("", tbc), Paragraph("", tbl_l),
                              Paragraph("", tbc), Paragraph("", tbc)])

    C1 = CONTENT_W * 0.14
    C2 = CONTENT_W * 0.46
    C3 = CONTENT_W * 0.20
    C4 = CONTENT_W * 0.20

    svc_ts = [
        ("BACKGROUND", (0, 0), (-1, 0), BLUE_DARK),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("GRID",       (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    for r in range(2, len(svc_data), 2):
        svc_ts.append(("BACKGROUND", (0, r), (-1, r), GREY_ROW))

    svc_tbl = Table(svc_data, colWidths=[C1, C2, C3, C4],
                    rowHeights=[8 * mm] + [6 * mm] * BLANK_ROWS)
    svc_tbl.setStyle(TableStyle(svc_ts))
    els.append(svc_tbl)
    els.append(Spacer(1, 5 * mm))

    # ── 4. FOOTER: NOTES + PAYMENT  |  FINANCIALS ───────────────────────
    pmode = str(bill_data.get("payment_mode", "")).lower()
    tick = lambda b: "[X]" if b else "[ ]"

    is_cash = pmode == "cash"
    is_cheq = "cheque" in pmode or pmode == "cheque"
    is_card = "card" in pmode
    is_ins  = "insurance" in pmode
    is_upi  = pmode in ("upi", "online")

    nsv = _s("_NSV", fontSize=8, textColor=TEXT_MID, leading=13)
    nbv = _s("_NBV", fontSize=8, fontName="Helvetica-Bold", textColor=TEXT_DARK)

    notes_txt = _strip_xml(bill_data.get("notes"))

    notes_blk = [
        Paragraph("Notes", _s("_NL", fontSize=9, fontName="Helvetica-Bold",
                               textColor=TEXT_DARK)),
        HRFlowable(width="75%", thickness=0.5, color=colors.lightgrey,
                   spaceBefore=1, spaceAfter=3),
        Paragraph(notes_txt, nsv),
        Spacer(1, 4 * mm),
        Paragraph("Payment by:", nbv),
        Spacer(1, 2 * mm),
        Paragraph(f"{tick(is_cash)}  Cash",                                    nsv),
        Paragraph(f"{tick(is_cheq)}  Cheque   No: ______________",             nsv),
        Paragraph(f"{tick(is_card)}  Credit Card",                             nsv),
        Paragraph(f"{tick(is_ins)}   Insurance   Carrier: ______________",     nsv),
        Paragraph(
            f"{tick(is_upi)}  Others: {'UPI / Online' if is_upi else '______________'}",
            nsv),
    ]

    # Financial rows
    subt  = float(bill_data.get("subtotal", 0))
    disc  = float(bill_data.get("discount_amount", 0))
    tax_p = float(bill_data.get("tax_percent", 0))
    tax_v = float(bill_data.get("tax_amount", 0))
    total = float(bill_data.get("total", 0))

    fl = _s("_FL", fontSize=7, fontName="Helvetica-Bold",
             textColor=BLUE_DARK, alignment=TA_RIGHT)
    fv = _s("_FV", fontSize=8, textColor=TEXT_DARK, alignment=TA_RIGHT)

    fin_rows = [
        [Paragraph("SUBTOTAL",               fl), Paragraph(_rs(subt),         fv)],
        [Paragraph("DISCOUNT",               fl), Paragraph(_rs(disc),         fv)],
        [Paragraph("SUBTOTAL LESS DISCOUNT", fl), Paragraph(_rs(subt - disc),  fv)],
        [Paragraph("TAX RATE",               fl), Paragraph(f"{tax_p:.2f}%",   fv)],
        [Paragraph("TOTAL TAX",              fl), Paragraph(_rs(tax_v),        fv)],
    ]

    fin_tbl = Table(fin_rows, colWidths=["60%", "40%"])
    fin_tbl.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW",     (1, 0), (1, -1), 0.5, colors.lightgrey),
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))

    bl = _s("_BL", fontSize=10, fontName="Helvetica-Bold", textColor=TEXT_DARK)
    bv = _s("_BV", fontSize=11, fontName="Helvetica-Bold",
             textColor=TEXT_DARK, alignment=TA_RIGHT)

    bal_tbl = Table(
        [[Paragraph("Total Bill", bl), Paragraph(_rs(total), bv)]],
        colWidths=["55%", "45%"],
        rowHeights=[10 * mm],
    )
    bal_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), GREY_BAL),
        ("BOX",           (0, 0), (-1, -1), 0.8, colors.darkgrey),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",   (0, 0), (0,  -1), 4),
        ("RIGHTPADDING",  (1, 0), (1,  -1), 4),
    ]))

    right_fin = [fin_tbl, Spacer(1, 4 * mm), bal_tbl]

    NW = CONTENT_W * 0.52
    GW = CONTENT_W * 0.04
    FW = CONTENT_W * 0.44

    ftr_tbl = Table([[notes_blk, Spacer(GW, 1), right_fin]],
                    colWidths=[NW, GW, FW])
    ftr_tbl.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    els.append(KeepTogether(ftr_tbl))

    # ── BUILD ─────────────────────────────────────────────────────────────
    doc.build(els)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    if output_path:
        parent = os.path.dirname(output_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(pdf_bytes)

    return pdf_bytes
