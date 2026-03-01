"""Presentation builder — compose slides with 1 or 2 chart panels + narrative, export to PPTX."""

import io

import pandas as pd
import streamlit as st

from analytics_app.modules.visualizations import build_figure

MAX_SECTIONS = 10

# pptx is imported lazily so the app can start without python-pptx installed.
_pptx_available = False
try:
    from pptx import Presentation as _Presentation
    from pptx.util import Inches, Pt, Emu
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
    _pptx_available = True
except ImportError:
    pass


def _check_pptx():
    """Raise a clear error if python-pptx is not installed."""
    if not _pptx_available:
        raise ImportError(
            "python-pptx is required for the Presentation Builder.\n"
            "Install it with:  pip install python-pptx"
        )


def _brand_colours():
    """Return MIFL brand colours (only call after _check_pptx)."""
    return {
        "BLUE": RGBColor(0x19, 0x2D, 0x6E),        # Deep Navy #192D6E
        "BLUE_BRIGHT": RGBColor(0x1E, 0x96, 0xD7),  # Curious Blue #1E96D7
        "DARK": RGBColor(0x12, 0x12, 0x12),          # Cod Gray #121212
        "WHITE": RGBColor(0xFF, 0xFF, 0xFF),
        "GREY": RGBColor(0x4A, 0x4F, 0x5C),
        "LIGHT_BG": RGBColor(0xE8, 0xF4, 0xFB),     # Light blue tint #E8F4FB
    }

_DEFAULT_SECTION = {
    "title": "",
    "layout": "1 panel",
    "panel_1": 0,
    "panel_2": 0,
    "narrative": "",
}


def _ensure_pres_state():
    """Initialise presentation session state if needed."""
    if "pres_sections" not in st.session_state:
        st.session_state["pres_sections"] = []


def _fig_to_png(fig, width=900, height=500):
    """Convert a Plotly figure to PNG bytes."""
    if fig is None:
        return None
    try:
        return fig.to_image(format="png", width=width, height=height, scale=2)
    except Exception as exc:
        if "kaleido" in str(exc).lower():
            raise RuntimeError(
                "Chart image export requires the kaleido package. "
                "Install it with: pip install 'kaleido>=0.2.1,<1.0.0'"
            ) from exc
        raise


def _add_title_slide(prs, title_text):
    """Add a branded title slide."""
    c = _brand_colours()
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank layout

    # Blue banner across top
    shp = slide.shapes.add_shape(
        1, Emu(0), Emu(0), prs.slide_width, Inches(2.5),  # MSO_SHAPE.RECTANGLE = 1
    )
    shp.fill.solid()
    shp.fill.fore_color.rgb = c["BLUE"]
    shp.line.fill.background()

    # Title text — vertically centred in banner
    txBox = slide.shapes.add_textbox(Inches(0.8), Inches(0.5), Inches(10.0), Inches(1.5))
    tf = txBox.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.text = title_text
    p.font.size = Pt(36)
    p.font.bold = True
    p.font.color.rgb = c["WHITE"]
    p.font.name = "Calibri"
    p.alignment = PP_ALIGN.LEFT

    # Subtitle
    sub = tf.add_paragraph()
    sub.text = "Analytics Report"
    sub.font.size = Pt(18)
    sub.font.color.rgb = c["BLUE_BRIGHT"]
    sub.font.name = "Calibri"
    sub.alignment = PP_ALIGN.LEFT


def _truncate_to_words(text, max_words=150):
    """Truncate text to approximately *max_words* words."""
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + "…"


def _to_bullets(text, max_words=150):
    """Convert narrative text into a list of concise bullet strings.

    Splits on newlines, sentence boundaries, and markdown bullets,
    strips markdown bold markers, then caps total length at *max_words*.
    """
    import re

    # Normalise: strip markdown bold/italic markers
    text = re.sub(r"\*{1,2}(.+?)\*{1,2}", r"\1", text)
    # Split on existing bullet markers, numbered lists, or double-newlines
    raw_lines = re.split(r"\n[\s\-\u2022\u2013*]*|\n{2,}|\.\s+(?=[A-Z])", text)
    bullets = []
    for line in raw_lines:
        line = line.strip(" \t\n\r-•–*.")
        if line:
            bullets.append(line)
    # Collapse into word-limited set
    result = []
    word_count = 0
    for b in bullets:
        words = b.split()
        if word_count + len(words) > max_words:
            remaining = max_words - word_count
            if remaining > 0:
                result.append(" ".join(words[:remaining]) + "…")
            break
        result.append(b)
        word_count += len(words)
    return result or [_truncate_to_words(text, max_words)]


def _add_ai_insights_slide(prs):
    """Add an AI-Powered Insights slide (appears right after the cover).

    Pulls the cached narrative from ``st.session_state["ai_narrative"]``.
    If no narrative has been generated yet the slide is silently skipped.
    """
    raw = st.session_state.get("ai_narrative", "")
    if not raw or raw.startswith("**Error:"):
        return

    c = _brand_colours()
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank
    slide_w = prs.slide_width
    slide_h = prs.slide_height
    margin_lr = 0.5
    content_w = 11.69 - 2 * margin_lr

    # ── Top bar ──────────────────────────────────────────────────────────────
    bar = slide.shapes.add_shape(1, Emu(0), Emu(0), slide_w, Inches(0.7))
    bar.fill.solid()
    bar.fill.fore_color.rgb = c["BLUE"]
    bar.line.fill.background()

    ttl = slide.shapes.add_textbox(
        Inches(margin_lr), Inches(0.0), Inches(content_w), Inches(0.7),
    )
    tf = ttl.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.text = "AI-Powered Insights"
    p.font.size = Pt(22)
    p.font.bold = True
    p.font.color.rgb = c["WHITE"]
    p.font.name = "Calibri"

    # ── Body ─────────────────────────────────────────────────────────────────
    body_top = Inches(0.9)
    body_h = slide_h - body_top - Inches(0.4)

    # Light background box
    nbox = slide.shapes.add_shape(
        1, Inches(margin_lr - 0.15), body_top,
        Inches(content_w + 0.3), body_h,
    )
    nbox.fill.solid()
    nbox.fill.fore_color.rgb = c["LIGHT_BG"]
    nbox.line.fill.background()

    # Text frame
    txBox = slide.shapes.add_textbox(
        Inches(margin_lr), body_top + Inches(0.1),
        Inches(content_w), body_h - Inches(0.2),
    )
    tf = txBox.text_frame
    tf.word_wrap = True
    tf.auto_size = None
    tf.vertical_anchor = MSO_ANCHOR.TOP

    bullets = _to_bullets(raw, max_words=350)
    for i, bullet_text in enumerate(bullets):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.text = f"\u2022  {bullet_text}"
        para.font.size = Pt(11)
        para.font.color.rgb = c["DARK"]
        para.font.name = "Calibri"
        para.line_spacing = Pt(16)
        para.space_after = Pt(4)


def _add_section_slide(prs, section, panels, df):
    """Add a content slide for one section."""
    c = _brand_colours()
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank
    slide_w = prs.slide_width
    slide_h = prs.slide_height

    # Usable content width (with margins)
    margin_lr = 0.5  # inches each side
    content_w = 11.69 - 2 * margin_lr  # ≈ 10.69″

    # ── Top bar ──────────────────────────────────────────────────────────────
    bar = slide.shapes.add_shape(1, Emu(0), Emu(0), slide_w, Inches(0.7))
    bar.fill.solid()
    bar.fill.fore_color.rgb = c["BLUE"]
    bar.line.fill.background()

    # Section title — vertically centred inside bar
    ttl = slide.shapes.add_textbox(
        Inches(margin_lr), Inches(0.0), Inches(content_w), Inches(0.7),
    )
    tf = ttl.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.text = section.get("title") or "Untitled Section"
    p.font.size = Pt(22)
    p.font.bold = True
    p.font.color.rgb = c["WHITE"]
    p.font.name = "Calibri"

    # ── Charts ───────────────────────────────────────────────────────────────
    layout = section.get("layout", "1 panel")

    panel_indices = [section.get("panel_1", 0)]
    if layout == "2 panels":
        panel_indices.append(section.get("panel_2", 0))

    # Collect AI panel insights (auto-pulled)
    ai_parts = []
    for pidx in panel_indices:
        ai_insight = st.session_state.get(f"panel_insight_{pidx}", "")
        if ai_insight and not ai_insight.startswith("**Error:"):
            ai_parts.append(ai_insight)
    ai_bullets = _to_bullets("\n\n".join(ai_parts), max_words=150) if ai_parts else []

    # Collect optional additional narrative (user-supplied)
    manual_narrative = section.get("narrative", "").strip()
    manual_bullets = _to_bullets(manual_narrative, max_words=100) if manual_narrative else []

    has_content = bool(ai_bullets or manual_bullets)

    # Chart sizing — 15 % smaller than full-bleed to leave room for commentary
    chart_top = Inches(0.9)
    chart_height_in = 3.2 if has_content else 4.7
    narrative_top = Inches(0.9 + chart_height_in + 0.15)
    narrative_h = slide_h - narrative_top - Inches(0.3)  # fill to bottom margin

    for i, pidx in enumerate(panel_indices):
        if pidx < 0 or pidx >= len(panels):
            continue
        panel = panels[pidx]
        fig = build_figure(
            df,
            panel["chart_type"],
            panel["metrics"],
            panel["dimensions"],
            agg_func=panel["agg_func"],
            color_dim=panel["color_dim"],
            title=panel.get("title", ""),
        )
        if fig is None:
            continue

        if layout == "1 panel":
            img_w, img_h = 1000, int(chart_height_in * 130)
            left = Inches(margin_lr)
            width = Inches(content_w)
        else:
            panel_w = (content_w - 0.3) / 2  # 0.3″ gap between panels
            img_w, img_h = 600, int(chart_height_in * 130)
            left = Inches(margin_lr + i * (panel_w + 0.3))
            width = Inches(panel_w)

        png_bytes = _fig_to_png(fig, width=img_w, height=img_h)
        if png_bytes:
            slide.shapes.add_picture(
                io.BytesIO(png_bytes), left, chart_top,
                width=width, height=Inches(chart_height_in),
            )

    # ── Insights / Additional Narrative ───────────────────────────────────────
    if has_content:
        box_left = Inches(margin_lr - 0.15)
        box_width = Inches(content_w + 0.3)

        # Light background box
        nbox = slide.shapes.add_shape(
            1, box_left, narrative_top, box_width, narrative_h,
        )
        nbox.fill.solid()
        nbox.fill.fore_color.rgb = c["LIGHT_BG"]
        nbox.line.fill.background()

        # Text frame — inset by padding so text aligns neatly
        txBox = slide.shapes.add_textbox(
            Inches(margin_lr), narrative_top + Inches(0.08),
            Inches(content_w), narrative_h - Inches(0.16),
        )
        tf = txBox.text_frame
        tf.word_wrap = True
        tf.auto_size = None
        tf.vertical_anchor = MSO_ANCHOR.TOP

        first_paragraph = True

        # AI-generated insights
        if ai_bullets:
            label = tf.paragraphs[0]
            label.text = "Key Insights"
            label.font.size = Pt(11)
            label.font.bold = True
            label.font.color.rgb = c["BLUE"]
            label.font.name = "Calibri"
            label.space_after = Pt(4)
            first_paragraph = False

            for bullet_text in ai_bullets:
                bp = tf.add_paragraph()
                bp.text = f"\u2022  {bullet_text}"
                bp.font.size = Pt(9)
                bp.font.color.rgb = c["DARK"]
                bp.font.name = "Calibri"
                bp.line_spacing = Pt(13)
                bp.space_after = Pt(2)

        # Optional additional narrative
        if manual_bullets:
            if first_paragraph:
                lbl = tf.paragraphs[0]
            else:
                lbl = tf.add_paragraph()
            lbl.text = "Additional Notes"
            lbl.font.size = Pt(11)
            lbl.font.bold = True
            lbl.font.color.rgb = c["GREY"]
            lbl.font.name = "Calibri"
            lbl.space_before = Pt(8) if not first_paragraph else Pt(0)
            lbl.space_after = Pt(4)

            for bullet_text in manual_bullets:
                bp = tf.add_paragraph()
                bp.text = f"\u2022  {bullet_text}"
                bp.font.size = Pt(9)
                bp.font.color.rgb = c["DARK"]
                bp.font.name = "Calibri"
                bp.line_spacing = Pt(13)
                bp.space_after = Pt(2)


def generate_pptx(sections, panels, df, report_title="Analytics Report"):
    """Generate a PowerPoint file and return bytes."""
    _check_pptx()
    prs = _Presentation()
    # Landscape A4: 297 mm × 210 mm ≈ 11.69″ × 8.27″
    prs.slide_width = Inches(11.69)
    prs.slide_height = Inches(8.27)

    _add_title_slide(prs, report_title)
    _add_ai_insights_slide(prs)

    for section in sections:
        _add_section_slide(prs, section, panels, df)

    buf = io.BytesIO()
    prs.save(buf)
    buf.seek(0)
    return buf.getvalue()


def render_presentation_builder(df: pd.DataFrame, panels: list):
    """Render the presentation builder UI."""
    if not _pptx_available:
        st.subheader("Presentation Builder")
        st.warning(
            "**python-pptx** is not installed. "
            "Install it to enable the Presentation Builder:\n\n"
            "```\npip install python-pptx kaleido\n```"
        )
        return

    _ensure_pres_state()

    st.subheader("Presentation Builder")
    st.markdown(
        "Compose a PowerPoint report by adding sections. AI-Powered Insights "
        "appear as the first slide after the cover. Each section becomes a slide "
        "with 1 or 2 chart panels, AI analysis, and an optional additional narrative."
    )

    if not panels:
        st.info("Add at least one dashboard panel above before building a presentation.")
        return

    # Panel labels for dropdowns
    panel_labels = []
    for i, p in enumerate(panels):
        label = p.get("title") or f"{p['chart_type']} — {', '.join(p.get('metrics', [])[:2])}"
        panel_labels.append(f"Panel {i + 1}: {label}")

    # ── Report title ─────────────────────────────────────────────────────────
    report_title = st.text_input(
        "Report title",
        value="Analytics Report",
        key="pres_report_title",
    )

    # ── Add / manage sections ────────────────────────────────────────────────
    sections = st.session_state["pres_sections"]

    col_a, col_b = st.columns([2, 8])
    with col_a:
        can_add = len(sections) < MAX_SECTIONS
        if st.button(
            "Add section" if can_add else f"Max {MAX_SECTIONS} sections",
            disabled=not can_add,
            type="primary",
            use_container_width=True,
            key="pres_add_section",
        ):
            sections.append(_DEFAULT_SECTION.copy())
            st.rerun()

    if not sections:
        st.info("Click **Add section** to start building your presentation.")
        return

    # ── Section configuration ────────────────────────────────────────────────
    for idx, section in enumerate(sections):
        with st.expander(f"Section {idx + 1}: {section.get('title') or 'Untitled'}", expanded=True):
            s1, s2, s3 = st.columns([3, 2, 1])

            with s1:
                section["title"] = st.text_input(
                    "Section title",
                    value=section.get("title", ""),
                    key=f"pres_title_{idx}",
                )

            with s2:
                layout_opts = ["1 panel", "2 panels"]
                current_layout = section.get("layout", "1 panel")
                section["layout"] = st.selectbox(
                    "Layout",
                    options=layout_opts,
                    index=layout_opts.index(current_layout) if current_layout in layout_opts else 0,
                    key=f"pres_layout_{idx}",
                )

            with s3:
                st.markdown("")
                st.markdown("")
                if st.button("Remove", key=f"pres_remove_{idx}", use_container_width=True):
                    sections.pop(idx)
                    st.rerun()

            # Panel selection
            p1_col, p2_col = st.columns(2)
            with p1_col:
                section["panel_1"] = st.selectbox(
                    "Panel 1",
                    options=range(len(panel_labels)),
                    format_func=lambda i: panel_labels[i],
                    index=min(section.get("panel_1", 0), len(panel_labels) - 1),
                    key=f"pres_p1_{idx}",
                )

            with p2_col:
                if section["layout"] == "2 panels":
                    section["panel_2"] = st.selectbox(
                        "Panel 2",
                        options=range(len(panel_labels)),
                        format_func=lambda i: panel_labels[i],
                        index=min(section.get("panel_2", 0), len(panel_labels) - 1),
                        key=f"pres_p2_{idx}",
                    )
                else:
                    st.markdown("*Single panel layout — no second panel.*")
                    section["panel_2"] = 0

            # Additional narrative (optional)
            section["narrative"] = st.text_area(
                "Additional Narrative (optional)",
                value=section.get("narrative", ""),
                height=80,
                key=f"pres_narr_{idx}",
                placeholder="Optional: add extra commentary or context beyond the AI insights...",
            )

    # ── Export ────────────────────────────────────────────────────────────────
    st.divider()
    if st.button("Generate PowerPoint", type="primary", key="pres_generate"):
        with st.spinner("Building presentation..."):
            try:
                pptx_bytes = generate_pptx(sections, panels, df, report_title)
                st.session_state["_pptx_bytes"] = pptx_bytes
                st.session_state["_pptx_title"] = report_title
                st.success(f"Presentation ready — {len(sections)} slide(s) generated.")
            except Exception as e:
                st.error(f"Error generating presentation: {e}")

    if st.session_state.get("_pptx_bytes"):
        title_slug = st.session_state.get("_pptx_title", "report").replace(" ", "_").lower()
        st.download_button(
            label="Download PowerPoint",
            data=st.session_state["_pptx_bytes"],
            file_name=f"{title_slug}.pptx",
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            key="pres_download",
        )
