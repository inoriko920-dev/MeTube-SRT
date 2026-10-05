from __future__ import annotations

from metube_srt_desktop.presentation.theme.tokens import TOKENS


def build_stylesheet() -> str:
    t = TOKENS
    return f"""
    QWidget {{
        color: {t.color_text};
        font-family: 'Segoe UI';
        font-size: 12px;
    }}
    QMainWindow, QWidget#app_root {{ background: {t.color_bg}; }}

    QFrame#navigation_rail {{
        background: {t.color_surface};
        border-right: 1px solid {t.color_border};
    }}
    QLabel#brand_title {{ font-size: 17px; font-weight: 700; color: {t.color_text}; }}
    QLabel#brand_subtitle {{ color: {t.color_text_muted}; font-size: 10px; }}
    QPushButton[nav='true'] {{
        border: 0;
        border-radius: {t.radius_md}px;
        padding: 10px 12px;
        text-align: left;
        color: {t.color_text_muted};
        background: transparent;
        font-weight: 500;
    }}
    QPushButton[nav='true']:hover {{ background: {t.color_surface_alt}; color: {t.color_text}; }}
    QPushButton[nav='true']:checked {{
        background: {t.color_primary_soft};
        color: {t.color_primary};
        font-weight: 650;
    }}

    QLabel#page_title {{ font-size: 22px; font-weight: 700; }}
    QLabel#page_subtitle {{ color: {t.color_text_muted}; }}
    QLabel[muted='true'] {{ color: {t.color_text_muted}; }}
    QLabel[sectionTitle='true'] {{ font-size: 14px; font-weight: 650; }}

    QFrame[card='true'] {{
        background: {t.color_surface};
        border: 1px solid {t.color_border};
        border-radius: {t.radius_lg}px;
    }}
    QFrame[softCard='true'] {{
        background: {t.color_surface_alt};
        border: 1px solid {t.color_border};
        border-radius: {t.radius_md}px;
    }}

    QLineEdit, QComboBox, QSpinBox {{
        background: {t.color_surface};
        border: 1px solid {t.color_border_strong};
        border-radius: {t.radius_sm}px;
        padding: 8px 10px;
        min-height: 18px;
    }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{ border: 1px solid {t.color_primary}; }}
    QCheckBox {{ spacing: 8px; }}

    QPushButton[role='primary'] {{
        color: white;
        background: {t.color_primary};
        border: 1px solid {t.color_primary};
        border-radius: {t.radius_sm}px;
        padding: 8px 14px;
        font-weight: 600;
    }}
    QPushButton[role='primary']:hover {{ background: {t.color_primary_hover}; }}
    QPushButton[role='secondary'] {{
        background: {t.color_surface};
        border: 1px solid {t.color_border_strong};
        border-radius: {t.radius_sm}px;
        padding: 8px 12px;
    }}
    QPushButton[role='secondary']:hover {{ background: {t.color_surface_alt}; }}
    QPushButton[role='ghost'] {{ border: 0; background: transparent; padding: 7px; }}
    QPushButton[role='ghost']:hover {{
        background: {t.color_surface_alt};
        border-radius: {t.radius_sm}px;
    }}

    QLabel[badge='success'] {{
        color: {t.color_success}; background: {t.color_success_soft};
        border-radius: 8px; padding: 3px 7px; font-weight: 600;
    }}
    QLabel[badge='warning'] {{
        color: {t.color_warning}; background: {t.color_warning_soft};
        border-radius: 8px; padding: 3px 7px; font-weight: 600;
    }}
    QLabel[badge='danger'] {{
        color: {t.color_danger}; background: {t.color_danger_soft};
        border-radius: 8px; padding: 3px 7px; font-weight: 600;
    }}

    QTableView {{
        background: {t.color_surface};
        alternate-background-color: {t.color_surface_alt};
        border: 1px solid {t.color_border};
        border-radius: {t.radius_md}px;
        gridline-color: {t.color_border};
        selection-background-color: {t.color_primary_soft};
        selection-color: {t.color_text};
    }}
    QHeaderView::section {{
        background: {t.color_surface_alt};
        color: {t.color_text_muted};
        border: 0;
        border-bottom: 1px solid {t.color_border};
        padding: 8px;
        font-weight: 600;
    }}
    QSplitter::handle {{ background: {t.color_border}; width: 1px; }}

    QFrame#ai_workspace {{
        background: {t.color_surface};
        border-left: 1px solid {t.color_border};
    }}
    QTextEdit#ai_prompt {{
        background: {t.color_surface};
        border: 1px solid {t.color_border_strong};
        border-radius: {t.radius_md}px;
        padding: 8px;
    }}
    """
