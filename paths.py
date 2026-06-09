"""Application paths and image loading (source tree vs PyInstaller .exe)."""

from __future__ import annotations

import sys
from pathlib import Path

import customtkinter as ctk
from PIL import Image

LOGO_SIZE = (30, 30)

try:
    _RESAMPLE = Image.Resampling.LANCZOS
except AttributeError:
    _RESAMPLE = Image.LANCZOS  # type: ignore[attr-defined]


def app_root() -> Path:
    """Folder containing the .exe when frozen, or the project folder in development."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def data_dir() -> Path:
    return app_root() / "data"


def archive_dir() -> Path:
    return data_dir() / "archive"


def asset_path(*parts: str) -> Path | None:
    relative = Path(*parts)
    candidates = [app_root() / "assets" / relative]
    if getattr(sys, "frozen", False):
        candidates.append(Path(sys._MEIPASS) / "assets" / relative)  # type: ignore[attr-defined]
    for path in candidates:
        if path.is_file():
            return path
    return None


def load_ctk_image(
    *parts: str,
    size: tuple[int, int],
) -> ctk.CTkImage | None:
    path = asset_path(*parts)
    if path is None:
        return None
    pil = Image.open(path).convert("RGBA").resize(size, _RESAMPLE)
    image = ctk.CTkImage(light_image=pil, dark_image=pil, size=size)
    image._pil_ref = pil  # type: ignore[attr-defined]
    return image


def load_logo_image() -> ctk.CTkImage | None:
    for parts in (("icons", "kernel-png.png"), ("kernel-png.png",)):
        image = load_ctk_image(*parts, size=LOGO_SIZE)
        if image is not None:
            return image
    return None
