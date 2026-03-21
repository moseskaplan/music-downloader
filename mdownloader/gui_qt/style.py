"""Shared Qt stylesheet and color constants."""

# Palette
BG = "#1a1a1a"
SURFACE = "#252525"
ACCENT = "#39ff14"       # neon green
BG_HOVER = "#1a1a1a"
TEXT = "#ffffff"
TEXT_DIM = "#aaaaaa"
TEXT_MUTED = "#666666"
BORDER = "#333333"
BORDER_DIM = "#444444"

APP_STYLE = f"""
/* ── Base ──────────────────────────────────────────── */
QWidget {{
    background-color: {BG};
    color: {TEXT};
    font-family: -apple-system, "SF Pro Text", "Helvetica Neue", Arial, sans-serif;
    font-size: 14px;
}}

QFrame#separator {{
    border: none;
    border-top: 1px solid {BORDER};
}}

/* ── Labels ─────────────────────────────────────────── */
QLabel#appTitle {{
    font-size: 26px;
    font-weight: 700;
    color: {ACCENT};
    letter-spacing: 0.5px;
}}

QLabel#appSubtitle {{
    font-size: 13px;
    color: {TEXT_DIM};
}}

QLabel#sectionLabel {{
    font-size: 11px;
    font-weight: 600;
    color: {TEXT_MUTED};
    letter-spacing: 1px;
}}

QLabel#folderPath {{
    font-size: 12px;
    color: {TEXT_DIM};
}}

/* ── Primary button (neon green outline) ────────────── */
QPushButton#primaryBtn {{
    background-color: transparent;
    border: 2px solid {ACCENT};
    color: {ACCENT};
    font-size: 15px;
    font-weight: 600;
    padding: 14px 20px;
    border-radius: 6px;
    text-align: left;
    padding-left: 20px;
}}

QPushButton#primaryBtn:hover {{
    background-color: {ACCENT};
    color: {BG};
}}

QPushButton#primaryBtn:pressed {{
    background-color: #2dcc10;
    border-color: #2dcc10;
    color: {BG};
}}

QPushButton#primaryBtn:focus {{
    outline: none;
    border: 2px solid {ACCENT};
}}

/* ── Secondary button (subtle) ──────────────────────── */
QPushButton#secondaryBtn {{
    background-color: transparent;
    border: 1px solid {BORDER_DIM};
    color: {TEXT_DIM};
    font-size: 13px;
    padding: 10px 20px;
    border-radius: 6px;
    text-align: left;
    padding-left: 20px;
}}

QPushButton#secondaryBtn:hover {{
    border-color: {TEXT_DIM};
    color: {TEXT};
}}

QPushButton#secondaryBtn:pressed {{
    background-color: #2a2a2a;
}}

QPushButton#secondaryBtn:focus {{
    outline: none;
    border: 1px solid {BORDER_DIM};
}}

/* ── Text input ─────────────────────────────────────── */
QLineEdit#folderField {{
    background-color: {SURFACE};
    border: 1px solid {BORDER_DIM};
    border-radius: 4px;
    color: {TEXT_DIM};
    padding: 0 10px;
    font-size: 12px;
}}

/* ── Link button (text-only) ────────────────────────── */
QPushButton#linkBtn {{
    background-color: transparent;
    border: none;
    color: {ACCENT};
    font-size: 12px;
    text-align: left;
    padding: 2px 0;
}}

QPushButton#linkBtn:hover {{
    color: {TEXT};
    text-decoration: underline;
}}

QPushButton#linkBtn:focus {{
    outline: none;
    border: none;
}}

/* ── Dialog button overrides (tighter padding for small buttons) ── */
QDialog QPushButton#primaryBtn {{
    padding: 6px 16px;
    font-size: 13px;
}}

QDialog QPushButton#secondaryBtn {{
    padding: 6px 16px;
    font-size: 13px;
}}

/* ── Download button (same style as primaryBtn, tighter padding) ── */
QPushButton#downloadBtn {{
    background-color: transparent;
    border: 2px solid {ACCENT};
    color: {ACCENT};
    font-size: 15px;
    font-weight: 600;
    padding: 6px 20px;
    border-radius: 6px;
}}

QPushButton#downloadBtn:hover {{
    background-color: {ACCENT};
    color: {BG};
}}

QPushButton#downloadBtn:pressed {{
    background-color: #2dcc10;
    border-color: #2dcc10;
    color: {BG};
}}

QPushButton#downloadBtn:focus {{
    outline: none;
    border: 2px solid {ACCENT};
}}

QPushButton#downloadBtn:disabled {{
    border-color: {BORDER_DIM};
    color: {TEXT_MUTED};
}}

/* ── Playlist checkbox ───────────────────────────────── */
QCheckBox {{
    color: {TEXT_DIM};
    font-size: 12px;
    spacing: 6px;
}}

QCheckBox:checked {{
    color: {ACCENT};
}}

/* ── URL input (album flow) ─────────────────────────── */
QLineEdit#urlInput {{
    background-color: {SURFACE};
    border: 1px solid {BORDER_DIM};
    border-radius: 4px;
    color: {TEXT};
    padding: 0 12px;
    font-size: 13px;
}}

QLineEdit#urlInput:focus {{
    border-color: {ACCENT};
}}

/* ── Track table ─────────────────────────────────────── */
QTableView#trackTable {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 4px;
    gridline-color: {BORDER};
    selection-background-color: #2a3a2a;
    selection-color: {TEXT};
}}

QTableView#trackTable QHeaderView::section {{
    background-color: {BG};
    color: {TEXT_MUTED};
    border: none;
    border-bottom: 1px solid {BORDER};
    border-right: 1px solid {BORDER};
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.5px;
    padding: 4px 8px;
}}

QTableView#trackTable::item {{
    padding: 4px 8px;
    border: none;
}}

QTableView#trackTable::item:selected {{
    background-color: #2a3a2a;
}}
"""
