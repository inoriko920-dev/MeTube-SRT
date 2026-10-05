from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ThemeTokens:
    color_bg: str = "#F5F7FB"
    color_surface: str = "#FFFFFF"
    color_surface_alt: str = "#F8FAFC"
    color_border: str = "#DDE3EC"
    color_border_strong: str = "#C8D1DE"
    color_text: str = "#172033"
    color_text_muted: str = "#667085"
    color_primary: str = "#2563EB"
    color_primary_hover: str = "#1D4ED8"
    color_primary_soft: str = "#EAF1FF"
    color_success: str = "#15803D"
    color_success_soft: str = "#ECFDF3"
    color_warning: str = "#B45309"
    color_warning_soft: str = "#FFF7E6"
    color_danger: str = "#B42318"
    color_danger_soft: str = "#FEF3F2"
    radius_sm: int = 6
    radius_md: int = 10
    radius_lg: int = 14
    space_xs: int = 6
    space_sm: int = 10
    space_md: int = 16
    space_lg: int = 24
    space_xl: int = 32
    navigation_width: int = 188
    ai_panel_width: int = 318
    ai_collapsed_width: int = 44


TOKENS = ThemeTokens()
