# app/components/styles.py
"""Shared design system - colors, typography, and component styles."""

# =============================================================================
# COLOR PALETTE - Brighter, more modern blues
# =============================================================================
COLORS = {
    # Primary blues
    "primary": "#2563eb",        # Bright blue (main actions, headers)
    "primary_dark": "#1d4ed8",   # Darker blue (hover states)
    "primary_light": "#3b82f6",  # Lighter blue (accents)

    # Secondary colors
    "secondary": "#64748b",      # Slate gray (secondary text)
    "muted": "#94a3b8",          # Light gray (muted text)

    # Semantic colors
    "success": "#22c55e",        # Green
    "warning": "#f59e0b",        # Amber
    "danger": "#ef4444",         # Red
    "info": "#0ea5e9",           # Sky blue

    # Backgrounds
    "bg_white": "#ffffff",
    "bg_light": "#f8fafc",       # Very light gray
    "bg_card": "#ffffff",
    "bg_highlight": "#eff6ff",   # Light blue tint

    # Borders
    "border": "#e2e8f0",
    "border_light": "#f1f5f9",

    # Text
    "text_primary": "#1e293b",   # Dark slate
    "text_secondary": "#475569", # Medium slate
    "text_muted": "#94a3b8",     # Light slate
}

# =============================================================================
# TYPOGRAPHY - Consistent sizing
# =============================================================================
TYPOGRAPHY = {
    "h1": "1.75rem",      # Page titles
    "h2": "1.25rem",      # Section headers
    "h3": "1.1rem",       # Card titles
    "body": "0.95rem",    # Body text
    "small": "0.85rem",   # Secondary text
    "caption": "0.75rem", # Captions, labels
}

# =============================================================================
# SHARED CSS - Import this in pages
# =============================================================================
def get_page_styles():
    """Return CSS for consistent page styling."""
    return f"""
<style>
    /* =========================================
       BASE STYLES
       ========================================= */
    .block-container {{
        padding-top: 1rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }}

    /* =========================================
       SECTION CONTAINERS
       ========================================= */
    .section-box {{
        background: {COLORS['bg_white']};
        border: 1px solid {COLORS['border']};
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
    }}

    .section-header {{
        font-size: {TYPOGRAPHY['h2']};
        font-weight: 600;
        color: {COLORS['primary']};
        margin: 0 0 1rem 0;
        padding-bottom: 0.75rem;
        border-bottom: 2px solid {COLORS['bg_highlight']};
    }}

    .section-subheader {{
        font-size: {TYPOGRAPHY['h3']};
        font-weight: 600;
        color: {COLORS['text_primary']};
        margin: 0 0 0.75rem 0;
    }}

    /* =========================================
       METRIC CARDS
       ========================================= */
    .metric-card {{
        background: linear-gradient(135deg, {COLORS['primary']} 0%, {COLORS['primary_dark']} 100%);
        border-radius: 12px;
        padding: 1.25rem;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.2);
    }}

    .metric-card .value {{
        font-size: 2rem;
        font-weight: 700;
        margin: 0;
        line-height: 1.2;
    }}

    .metric-card .label {{
        font-size: {TYPOGRAPHY['caption']};
        opacity: 0.9;
        margin: 0.25rem 0 0 0;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}

    .metric-card .subtext {{
        font-size: {TYPOGRAPHY['caption']};
        opacity: 0.7;
        margin: 0.25rem 0 0 0;
    }}

    /* Light metric variant */
    .metric-card-light {{
        background: {COLORS['bg_light']};
        border: 1px solid {COLORS['border']};
        border-radius: 12px;
        padding: 1.25rem;
        text-align: center;
    }}

    .metric-card-light .value {{
        font-size: 1.75rem;
        font-weight: 700;
        color: {COLORS['primary']};
        margin: 0;
    }}

    .metric-card-light .label {{
        font-size: {TYPOGRAPHY['caption']};
        color: {COLORS['text_secondary']};
        margin: 0.25rem 0 0 0;
        text-transform: uppercase;
    }}

    /* =========================================
       INSIGHT CARDS
       ========================================= */
    .insight-card {{
        background: {COLORS['bg_white']};
        border: 1px solid {COLORS['border']};
        border-left: 4px solid {COLORS['info']};
        border-radius: 8px;
        padding: 1rem 1.25rem;
        margin-bottom: 0.75rem;
    }}

    .insight-card.success {{
        border-left-color: {COLORS['success']};
        background: linear-gradient(90deg, rgba(34, 197, 94, 0.05) 0%, {COLORS['bg_white']} 100%);
    }}

    .insight-card.warning {{
        border-left-color: {COLORS['warning']};
        background: linear-gradient(90deg, rgba(245, 158, 11, 0.05) 0%, {COLORS['bg_white']} 100%);
    }}

    .insight-card.danger {{
        border-left-color: {COLORS['danger']};
        background: linear-gradient(90deg, rgba(239, 68, 68, 0.05) 0%, {COLORS['bg_white']} 100%);
    }}

    .insight-card h4 {{
        font-size: {TYPOGRAPHY['body']};
        font-weight: 600;
        color: {COLORS['text_primary']};
        margin: 0 0 0.5rem 0;
    }}

    .insight-card p {{
        font-size: {TYPOGRAPHY['small']};
        color: {COLORS['text_secondary']};
        margin: 0;
        line-height: 1.5;
    }}

    /* =========================================
       DATA CARDS (for stats/comparisons)
       ========================================= */
    .data-card {{
        background: {COLORS['bg_light']};
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
    }}

    .data-card .big-number {{
        font-size: 2.25rem;
        font-weight: 700;
        color: {COLORS['primary']};
        line-height: 1;
    }}

    .data-card .label {{
        font-size: {TYPOGRAPHY['caption']};
        color: {COLORS['text_muted']};
        text-transform: uppercase;
        margin-top: 0.5rem;
    }}

    .data-card .detail {{
        font-size: {TYPOGRAPHY['small']};
        color: {COLORS['text_secondary']};
        margin-top: 0.25rem;
    }}

    /* =========================================
       COMPARISON HIGHLIGHT BOX
       ========================================= */
    .highlight-box {{
        background: {COLORS['bg_highlight']};
        border: 1px solid {COLORS['border']};
        border-radius: 12px;
        padding: 1.25rem;
    }}

    .highlight-box .eyebrow {{
        font-size: {TYPOGRAPHY['caption']};
        color: {COLORS['text_muted']};
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin: 0 0 0.5rem 0;
    }}

    .highlight-box .primary-stat {{
        font-size: 2.5rem;
        font-weight: 700;
        color: {COLORS['primary']};
        margin: 0;
        line-height: 1.2;
    }}

    .highlight-box .secondary-stat {{
        font-size: 1.25rem;
        color: {COLORS['text_secondary']};
        margin: 0.25rem 0 0 0;
    }}

    .highlight-box .insight {{
        font-size: {TYPOGRAPHY['small']};
        color: {COLORS['success']};
        font-weight: 600;
        margin-top: 0.75rem;
    }}

    .highlight-box .insight.negative {{
        color: {COLORS['danger']};
    }}

    /* =========================================
       CHART CONTAINERS
       ========================================= */
    .chart-container {{
        background: {COLORS['bg_white']};
        border: 1px solid {COLORS['border']};
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 1rem;
    }}

    .chart-title {{
        font-size: {TYPOGRAPHY['body']};
        font-weight: 600;
        color: {COLORS['text_primary']};
        margin: 0 0 0.5rem 0;
    }}

    .chart-description {{
        font-size: {TYPOGRAPHY['caption']};
        color: {COLORS['text_muted']};
        margin: 0 0 0.75rem 0;
    }}

    /* =========================================
       BADGES & TAGS
       ========================================= */
    .badge {{
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: {TYPOGRAPHY['caption']};
        font-weight: 600;
    }}

    .badge-primary {{
        background: {COLORS['primary']};
        color: white;
    }}

    .badge-success {{
        background: {COLORS['success']};
        color: white;
    }}

    .badge-warning {{
        background: {COLORS['warning']};
        color: white;
    }}

    .badge-danger {{
        background: {COLORS['danger']};
        color: white;
    }}

    .badge-muted {{
        background: {COLORS['bg_light']};
        color: {COLORS['text_secondary']};
        border: 1px solid {COLORS['border']};
    }}

    /* =========================================
       TABLES
       ========================================= */
    .styled-table {{
        width: 100%;
        border-collapse: collapse;
        font-size: {TYPOGRAPHY['small']};
    }}

    .styled-table th {{
        background: {COLORS['bg_light']};
        color: {COLORS['text_primary']};
        font-weight: 600;
        padding: 0.75rem 1rem;
        text-align: left;
        border-bottom: 2px solid {COLORS['border']};
    }}

    .styled-table td {{
        padding: 0.75rem 1rem;
        border-bottom: 1px solid {COLORS['border_light']};
        color: {COLORS['text_secondary']};
    }}

    .styled-table tr:hover {{
        background: {COLORS['bg_light']};
    }}

    /* =========================================
       UTILITY CLASSES
       ========================================= */
    .text-primary {{ color: {COLORS['text_primary']}; }}
    .text-secondary {{ color: {COLORS['text_secondary']}; }}
    .text-muted {{ color: {COLORS['text_muted']}; }}
    .text-success {{ color: {COLORS['success']}; }}
    .text-warning {{ color: {COLORS['warning']}; }}
    .text-danger {{ color: {COLORS['danger']}; }}
    .text-blue {{ color: {COLORS['primary']}; }}

    .font-bold {{ font-weight: 700; }}
    .font-semibold {{ font-weight: 600; }}

    .text-sm {{ font-size: {TYPOGRAPHY['small']}; }}
    .text-xs {{ font-size: {TYPOGRAPHY['caption']}; }}

    .mt-1 {{ margin-top: 0.5rem; }}
    .mt-2 {{ margin-top: 1rem; }}
    .mb-1 {{ margin-bottom: 0.5rem; }}
    .mb-2 {{ margin-bottom: 1rem; }}
</style>
"""


def get_nav_colors():
    """Return colors for navigation component."""
    return {
        "nav_bg": "#1e40af",          # Bright blue nav background
        "nav_hover": "rgba(255,255,255,0.15)",
        "dropdown_bg": "#ffffff",
        "dropdown_text": "#1e293b",
        "dropdown_hover": "#eff6ff",
    }
