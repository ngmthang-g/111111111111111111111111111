from __future__ import annotations

import tkinter as tk
from tkinter import ttk

BG = "#f0f0f0"
GREEN = "#2e9637"
BLUE = "#3465d9"
GRAY = "#666666"
RED = "#d12228"
BROWN = "#7b5546"
PURPLE = "#8e24aa"
GOLD = "#b58b00"
WHITE = "#ffffff"
BLACK = "#000000"


def configure_root(root: tk.Tk) -> None:
    root.configure(bg=BG)
    style = ttk.Style(root)
    try:
        style.theme_use("vista")
    except tk.TclError:
        pass
    style.configure("TNotebook", background=BG, borderwidth=0, tabmargins=0)
    style.configure("TNotebook.Tab", padding=(4, 2), font=("Segoe UI", 9))
    style.configure("TCombobox", padding=1)


def button(parent, text: str, command=None, kind: str = "green", width: int | None = None, **kw):
    colors = {
        "green": GREEN,
        "blue": BLUE,
        "gray": GRAY,
        "red": RED,
        "brown": BROWN,
        "purple": PURPLE,
        "gold": GOLD,
    }
    bg = colors.get(kind, GREEN)
    opts = dict(text=text, command=command, bg=bg, fg=WHITE, activebackground=bg,
                activeforeground=WHITE, relief="raised", bd=1, font=("Segoe UI", 9, "bold"),
                highlightthickness=0, padx=4, pady=1)
    if width is not None:
        opts["width"] = width
    opts.update(kw)
    return tk.Button(parent, **opts)


def labelframe(parent, text: str):
    return tk.LabelFrame(parent, text=text, bg=BG, fg=BLACK, font=("Segoe UI", 9, "bold"), bd=1, relief="groove")
