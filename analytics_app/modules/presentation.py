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
        1, Emu(0), Emu(0), prs.slide_width, Inches(2.2),  # MSO_SHAPE.RECTANGLE = 1
    )
    shp.fill.solid()
    shp.fill.fore_color.rgb = c["BLUE"]
    shp.line.fill.background()

    # Title text
    txBox = slide.shapes.add_textbox(Inches(0.8), Inches(0.5), Inches(8.4), Inches(1.2))
    tf = txBox.text_frame
    tf.word_wrap = True
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


def _add_section_slide(prs, section, panels, df):
    """Add a content slide for one section."""
    c = _brand_colours()
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank
    slide_w = prs.slide_width
    slide_h = prs.slide_height

    # ── Top bar ──────────────────────────────────────────────────────────────
    bar = slide.shapes.add_shape(1, Emu(0), Emu(0), slide_w, Inches(0.7))
    bar.fill.solid()
    bar.fill.fore_color.rgb = c["BLUE"]
    bar.line.fill.background()

    # Section title in bar
    ttl = slide.shapes.add_textbox(Inches(0.5), Inches(0.1), Inches(9), Inches(0.5))
    tf = ttl.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = section.get("title") or "Untitled Section"
    p.font.size = Pt(22)
    p.font.bold = True
    p.font.color.rgb = c["WHITE"]
    p.font.name = "Calibri"

    # ── Charts ───────────────────────────────────────────────────────────────
    layout = section.get("layout", "1 panel")
    has_narrative = bool(section.get("narrative", "").strip())

    # Calculate chart area — leave room for narrative at bottom
    chart_top = Inches(0.9)
    chart_height_in = 3.8 if has_narrative else 5.5
    narrative_top = Inches(0.9 + chart_height_in + 0.15)

    panel_indices = [section.get("panel_1", 0)]
    if layout == "2 panels":
        panel_indices.append(section.get("panel_2", 0))

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
            img_w, img_h = 900, int(chart_height_in * 130)
            left = Inches(0.5)
            width = Inches(9.0)
        else:
            img_w, img_h = 550, int(chart_height_in * 130)
            left = Inches(0.3 + i * 4.85)
            width = Inches(4.6)

        png_bytes = _fig_to_png(fig, width=img_w, height=img_h)
        if png_bytes:
            slide.shapes.add_picture(
                io.BytesIO(png_bytes), left, chart_top,
                width=width, height=Inches(chart_height_in),
            )

    # ── Narrative ────────────────────────────────────────────────────────────
    narrative_text = section.get("narrative", "").strip()
    if narrative_text:
        # Light grey background box
        nbox = slide.shapes.add_shape(
            1, Inches(0.3), narrative_top,
            Inches(9.4), Inches(1.9),
        )
        nbox.fill.solid()
        nbox.fill.fore_color.rgb = c["LIGHT_BG"]
        nbox.line.fill.background()

        # Narrative text
        txBox = slide.shapes.add_textbox(
            Inches(0.5), narrative_top + Inches(0.1),
            Inches(9.0), Inches(1.7),
        )
        tf = txBox.text_frame
        tf.word_wrap = True
        tf.auto_size = None

        # "Narrative" label
        label = tf.paragraphs[0]
        label.text = "Narrative"
        label.font.size = Pt(11)
        label.font.bold = True
        label.font.color.rgb = c["BLUE"]
        label.font.name = "Calibri"
        label.space_after = Pt(4)

        # Body text
        body = tf.add_paragraph()
        body.text = narrative_text
        body.font.size = Pt(10)
        body.font.color.rgb = c["DARK"]
        body.font.name = "Calibri"
        body.line_spacing = Pt(14)


def generate_pptx(sections, panels, df, report_title="Analytics Report"):
    """Generate a PowerPoint file and return bytes."""
    _check_pptx()
    prs = _Presentation()
    prs.slide_width = Inches(10)
    prs.slide_height = Inches(7.5)

    _add_title_slide(prs, report_title)

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
        "Compose a PowerPoint report by adding sections. Each section becomes "
        "a slide with 1 or 2 chart panels and an optional narrative."
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

            # Narrative
            section["narrative"] = st.text_area(
                "Narrative",
                value=section.get("narrative", ""),
                height=100,
                key=f"pres_narr_{idx}",
                placeholder="Add commentary, insights, or context for this slide...",
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
