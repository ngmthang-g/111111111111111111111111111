from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Iterable

from .theme import BG, button


def add_vertical_scroll(parent: tk.Widget) -> tuple[tk.Canvas, tk.Frame]:
    canvas = tk.Canvas(parent, bg=BG, borderwidth=0, highlightthickness=0)
    bar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
    inner = tk.Frame(canvas, bg=BG)
    win = canvas.create_window((0, 0), window=inner, anchor="nw")
    canvas.configure(yscrollcommand=bar.set)
    canvas.pack(side="left", fill="both", expand=True)
    bar.pack(side="right", fill="y")
    inner.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind("<Configure>", lambda e: canvas.itemconfigure(win, width=e.width))
    return canvas, inner


def section_title(parent: tk.Widget, text: str, row: int, columnspan: int = 1):
    tk.Label(parent, text=text, bg=BG, font=("Segoe UI", 9, "bold"), anchor="w").grid(
        row=row, column=0, columnspan=columnspan, sticky="ew", padx=2, pady=(3, 1)
    )


def start_bar(parent: tk.Widget, command=None):
    b = button(parent, "Bắt đầu", command=command, kind="green")
    b.pack(side="bottom", fill="x", padx=5, pady=5)
    return b


def labeled_combo(parent: tk.Widget, label: str, values: Iterable[str], row: int, variable=None, width=18):
    tk.Label(parent, text=label, bg=BG).grid(row=row, column=0, sticky="w", padx=3, pady=2)
    cb = ttk.Combobox(parent, values=list(values), state="readonly", width=width, textvariable=variable)
    cb.grid(row=row, column=1, sticky="w", padx=3, pady=2)
    if cb["values"] and not cb.get():
        cb.current(0)
    return cb


def account_table_header(parent: tk.Widget, headers: list[tuple[str, int]], row=0, start_col=0):
    for offset, (text, width) in enumerate(headers):
        col = start_col + offset
        tk.Label(parent, text=text, bg=BG, font=("Segoe UI", 9, "bold"), width=width, anchor="center").grid(
            row=row, column=col, sticky="ew", padx=1
        )
