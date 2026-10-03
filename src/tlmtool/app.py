from __future__ import annotations

import logging
import os
import threading
import time
import tkinter as tk
from collections import deque
from tkinter import filedialog, messagebox, simpledialog, ttk

from . import __version__
from .backend import Action, TlmBackend
from .game_data import map_name_to_id, map_names
from .services import DailyScheduleService, MonitorService
from .storage import SettingsStore
from .theme import BG, GREEN, GRAY, PURPLE, WHITE, button, configure_root, labelframe
from .widgets import account_table_header, add_vertical_scroll, start_bar

log = logging.getLogger("tlmtool")


class BaseTab(tk.Frame):
    def __init__(self, master, app: "TLMApplication") -> None:
        super().__init__(master, bg=BG)
        self.app, self.backend, self.store = app, app.backend, app.store

    def action_all(self, action: Action) -> None:
        results = self.backend.execute_all(action)
        bad = [r.detail for r in results if not r.ok]
        if bad:
            self.app.set_status(bad[0])


class StartTab(BaseTab):
    def __init__(self, master, app) -> None:
        super().__init__(master, app)
        mode = labelframe(self, "Chế độ"); mode.pack(fill="x", padx=5, pady=(5, 2))
        self.mode = tk.StringVar(value=self.store.get("start", "mode", "Auto"))
        tk.Radiobutton(mode, text="Auto", value="Auto", variable=self.mode, bg=BG, command=self.on_mode_change).pack(side="left", padx=5)
        tk.Radiobutton(mode, text="Xếp lưới", value="Xếp lưới", variable=self.mode, bg=BG, command=self.on_mode_change).pack(side="left", padx=18)

        self.sync_frame = labelframe(self, "Đồng bộ các cửa sổ")
        sync_top = tk.Frame(self.sync_frame, bg=BG); sync_top.pack(fill="x", padx=4, pady=2)
        self.grid_cols = tk.IntVar(value=max(1, min(9, self.store.get_int("start", "grid_cols", 2))))
        self.grid_rows = tk.IntVar(value=max(1, min(9, self.store.get_int("start", "grid_rows", 2))))
        button(sync_top, "－", lambda:self.change_grid("cols",-1), "gray", width=2).pack(side="left")
        tk.Label(sync_top,text="Cột:",bg=BG,font=("Segoe UI",9,"bold")).pack(side="left",padx=(3,0))
        self.grid_cols_label=tk.Label(sync_top,text=str(self.grid_cols.get()),bg=BG,width=2); self.grid_cols_label.pack(side="left")
        button(sync_top, "＋", lambda:self.change_grid("cols",1), "gray", width=2).pack(side="left")
        tk.Label(sync_top,text="   ",bg=BG).pack(side="left")
        button(sync_top, "－", lambda:self.change_grid("rows",-1), "gray", width=2).pack(side="left")
        tk.Label(sync_top,text="Hàng:",bg=BG,font=("Segoe UI",9,"bold")).pack(side="left",padx=(3,0))
        self.grid_rows_label=tk.Label(sync_top,text=str(self.grid_rows.get()),bg=BG,width=2); self.grid_rows_label.pack(side="left")
        button(sync_top, "＋", lambda:self.change_grid("rows",1), "gray", width=2).pack(side="left")

        master=tk.Frame(self.sync_frame,bg=BG); master.pack(fill="x",padx=4,pady=1)
        tk.Label(master,text="Cửa sổ chính:",bg=BG,font=("Segoe UI",9,"bold")).pack(side="left")
        self.master_var=tk.StringVar(value=""); self.master_combo=ttk.Combobox(master,textvariable=self.master_var,state="readonly",width=26)
        self.master_combo.pack(side="left",padx=4,fill="x",expand=True); self.master_combo.bind("<<ComboboxSelected>>",lambda _e:self.apply_grid_layout())
        sb=tk.Frame(self.sync_frame,bg=BG); sb.pack(fill="x",padx=4,pady=(1,4))
        self.layout_active=False; self.input_active=False
        self.layout_btn=button(sb,"Đồng bộ các cửa sổ",self.toggle_layout,"gray"); self.layout_btn.pack(side="left",fill="x",expand=True,padx=(0,2))
        self.input_btn=button(sb,"Đồng bộ phím chuột",self.toggle_input,"gray"); self.input_btn.pack(side="left",fill="x",expand=True,padx=(2,0))

        quick = labelframe(self, "Điều khiển nhanh"); self.quick_frame=quick; quick.pack(fill="x", padx=5, pady=2)
        q = tk.Frame(quick, bg=BG); q.pack(fill="x", padx=4, pady=3)
        rows = [
            [("Ẩn hết","green",self.hide_all),("Xem trước","green",self.refresh),("Xếp gọn","blue",self.arrange),("Xếp chéo","blue",self.diagonal)],
            [("Login","green",lambda:self.app.notebook.select(1)),("Reload","blue",lambda:self.action_all(Action.RELOAD))],
            [("Trừng ác","green",lambda:self.action_all(Action.TRUNG_AC)),("Tàng bảo đồ","blue",lambda:self.action_all(Action.TANG_BAO_DO)),("Tới bỏ đầu","blue",lambda:self.action_all(Action.TOI_BO_DAU)),("Trị liệu","blue",lambda:self.action_all(Action.TRI_LIEU))],
            [("Train","green",lambda:self.action_all(Action.TRAIN)),("Tới chỗ train","blue",lambda:self.action_all(Action.TOI_CHO_TRAIN)),("Đánh","blue",lambda:self.action_all(Action.DANH)),("Bán đồ","blue",lambda:self.action_all(Action.BAN_DO))],
            [("Train LSV","green",lambda:self.action_all(Action.TRAIN_LSV)),("Tới LSV","blue",lambda:self.action_all(Action.TOI_LSV)),("Tới chỗ train","blue",lambda:self.action_all(Action.TOI_CHO_TRAIN_LSV)),("Rời LSV","blue",lambda:self.action_all(Action.ROI_LSV))],
            [("Dồn vàng","green",lambda:self.action_all(Action.DON_VANG)),("Tới nơi nhận","blue",lambda:self.action_all(Action.TOI_NOI_NHAN)),("Tới chỗ bán","blue",lambda:self.action_all(Action.TOI_CHO_BAN)),("Tới nơi train","blue",lambda:self.action_all(Action.TOI_NOI_TRAIN))],
            [("Theo dõi","green",lambda:self.action_all(Action.THEO_DOI)),("Tối ưu","green",lambda:self.app.notebook.select(9))],
        ]
        config_tabs = {0:1, 2:6, 3:3, 4:4, 5:7, 6:9}
        for rr, cells in enumerate(rows):
            for cc, (text, kind, cmd) in enumerate(cells):
                button(q, text, cmd, kind, width=10).grid(row=rr, column=cc, sticky="ew", padx=1, pady=1)
            if rr in config_tabs:
                button(q, "Cấu hình", lambda i=config_tabs[rr]: self.app.notebook.select(i), "gray", width=7).grid(row=rr, column=4, padx=(36,1), pady=1)
        for c in range(4): q.grid_columnconfigure(c, weight=1)

        prev = labelframe(self, "Xem trước cửa sổ"); prev.pack(fill="x", padx=5, pady=2)
        line = tk.Frame(prev, bg=BG); line.pack(fill="x", padx=4, pady=(2,0))
        tk.Label(line, text="Cột:", bg=BG, font=("Segoe UI",9,"bold")).pack(side="left")
        self.columns = tk.IntVar(value=1)
        for i in range(1,6):
            tk.Radiobutton(line, text=f"{i}x", value=i, variable=self.columns, bg=BG).pack(side="left", padx=2)
        button(line,"Tách rời",self.detach,"blue").pack(side="left",padx=(4,1))
        button(line,"Làm mới",self.refresh,"green").pack(side="left",padx=1)
        button(line,"Đóng hết",self.close_all,"gray").pack(side="left",padx=1)
        self.preview = tk.Label(prev, text="Không tìm thấy cửa sổ game, hãy mở game trước.", bg=BG, anchor="w")
        self.preview.pack(fill="x", padx=4, pady=(2,4))
        lic = labelframe(self, "Thông tin bản quyền"); lic.pack(fill="x", padx=5, pady=2)
        tk.Label(lic,text="Bản quyền FREE vĩnh viễn",fg=GREEN,bg=BG,font=("Segoe UI",9,"bold")).pack(pady=8)
        self.on_mode_change()
        self.refresh()

    def save_start_config(self):
        self.store.set("start","mode",self.mode.get())
        self.store.set("start","grid_cols",self.grid_cols.get())
        self.store.set("start","grid_rows",self.grid_rows.get())
        self.store.set("start","preview_cols",self.columns.get())
        self.store.save()

    def on_mode_change(self):
        self.save_start_config()
        if self.mode.get()=="Xếp lưới":
            if not self.sync_frame.winfo_ismapped():
                self.sync_frame.pack(fill="x",padx=5,pady=2,before=self.quick_frame)
            self.update_master_choices()
            if not self.layout_active:
                self.toggle_layout()
        else:
            self.sync_frame.pack_forget()
            self.layout_active=False; self.input_active=False
            self.layout_btn.config(bg=GRAY); self.input_btn.config(bg=GRAY)

    def change_grid(self,which,delta):
        var=self.grid_cols if which=="cols" else self.grid_rows
        var.set(max(1,min(9,var.get()+delta)))
        self.grid_cols_label.config(text=str(self.grid_cols.get())); self.grid_rows_label.config(text=str(self.grid_rows.get()))
        self.save_start_config()
        if self.layout_active: self.apply_grid_layout()

    def update_master_choices(self):
        wins=self.backend.windows()
        values=[f"{g.hwnd}|{g.title or ('PID '+str(g.pid))}" for g in wins]
        self.master_combo.configure(values=values)
        if self.master_var.get() not in values:
            self.master_var.set(values[0] if values else "")

    def ordered_windows(self):
        wins=self.backend.windows()
        master=self.master_var.get().split("|",1)[0] if self.master_var.get() else ""
        return sorted(wins,key=lambda g:0 if str(g.hwnd)==master else 1)

    def apply_grid_layout(self):
        wins=self.ordered_windows()
        if not wins: return
        cols=max(1,self.grid_cols.get()); rows=max(1,self.grid_rows.get())
        sw,sh=self.backend.winapi.screen_size(); ww=max(320,sw//cols); hh=max(240,sh//rows)
        for i,g in enumerate(wins):
            col=i%cols; row=(i//cols)%rows
            self.backend.winapi.move(g.hwnd,col*ww,row*hh,ww,hh)
        self._windows_hidden=False
        self.app.set_status(f"[Xếp lưới] {len(wins)} cửa sổ • {cols}x{rows}")

    def toggle_layout(self):
        self.layout_active=not self.layout_active
        self.layout_btn.config(bg=GREEN if self.layout_active else GRAY)
        if self.layout_active: self.apply_grid_layout()

    def toggle_input(self):
        self.input_active=not self.input_active
        self.input_btn.config(bg=GREEN if self.input_active else GRAY)
        if self.input_active:
            self.app.set_status("[Đồng bộ] phím/chuột chờ InputSync runtime bridge.")
        else:
            self.app.set_status("[Đồng bộ] phím/chuột đã tắt.")

    def refresh(self):
        wins=self.backend.windows(); self.update_master_choices()
        self.preview.config(text=f"Đã tìm thấy {len(wins)} cửa sổ game." if wins else "Không tìm thấy cửa sổ game, hãy mở game trước.")
    def hide_all(self):
        windows = self.backend.windows()
        if not windows:
            self.app.set_status("[Ẩn] Không có cửa sổ game nào")
            return
        hidden = bool(getattr(self, "_windows_hidden", False))
        if not hidden:
            self._saved_window_rects = {}
            for g in windows:
                rect = self.backend.winapi.window_rect(g.hwnd)
                if rect:
                    self._saved_window_rects[g.hwnd] = (rect.left, rect.top, rect.width, rect.height)
                # TLM 2.1.2 moves windows off-screen instead of SW_HIDE so
                # Unity keeps rendering and PrintWindow/background input works.
                self.backend.winapi.move_keep_size(g.hwnd, -2200, -2200)
            self._windows_hidden = True
            self.app.set_status(f"[Ẩn] Đã ẩn {len(windows)} cửa sổ game")
        else:
            for g in windows:
                self.backend.winapi.move_keep_size(g.hwnd, 0, 0)
            self._windows_hidden = False
            self.app.set_status(f"[Ẩn] Đã hiện lại {len(windows)} cửa sổ game về (0,0)")
        self.refresh()
    def detach(self):
        # TLM's Tách rời is a DWM preview operation, not ShowWindow.
        self.refresh()
        self.app.set_status("Preview tách rời đang chờ DWM thumbnail renderer.")
    def arrange(self):
        windows = self.backend.windows()
        for g in windows:
            self.backend.winapi.move_keep_size(g.hwnd, 0, 0)
        self._windows_hidden = False
        self.app.set_status(f"[Xếp] Đã xếp gọn {len(windows)} cửa sổ")
    def diagonal(self):
        windows = self.backend.windows()
        for i, g in enumerate(windows):
            self.backend.winapi.move_keep_size(g.hwnd, i * 50, i * 50)
        self._windows_hidden = False
        self.app.set_status(f"[Xếp] Đã xếp chéo {len(windows)} cửa sổ")
    def close_all(self):
        if self.backend.windows() and messagebox.askyesno("TLMTool","Đóng tất cả cửa sổ game?"):
            for g in self.backend.windows(): self.backend.winapi.close(g.hwnd)


class LoginTab(BaseTab):
    # TLM 2.1.2 keeps a fixed 100-row account model; the screenshot only shows
    # the rows that fit in the scroll viewport.
    ROWS = 100

    def __init__(self, master, app) -> None:
        super().__init__(master, app)
        self.schedule = DailyScheduleService()
        self._batch_cancel = threading.Event()
        self._batch_running = False
        self._online: dict[int, int] = {}

        game = labelframe(self, "Cấu hình game")
        game.pack(fill="x", padx=5, pady=(5, 2))
        top = tk.Frame(game, bg=BG)
        top.pack(fill="x", padx=4, pady=3)
        button(top, "Chọn thư mục game", self.choose_game, "blue").pack(side="left", padx=1)
        button(top, "Mở game", self.open_game, "blue").pack(side="left", padx=4)
        self.game_dir = self.store.get("game", "directory", "")
        self.game_status = tk.Label(
            game, text=self._game_status(), bg=BG, fg=GREEN,
            font=("Segoe UI", 9, "bold"), anchor="w",
        )
        self.game_status.pack(fill="x", padx=5, pady=(0, 4))

        sched = labelframe(self, "Cấu hình lịch trình")
        sched.pack(fill="x", padx=5, pady=2)
        self.schedule_enabled = tk.BooleanVar(value=self.store.get_bool("schedule", "enabled", False))
        tk.Checkbutton(
            sched, text="Chạy theo lịch (mở/tắt game)",
            variable=self.schedule_enabled, bg=BG, command=self.apply_schedule,
        ).grid(row=0, column=0, columnspan=5, sticky="w", padx=4)

        self.close_h = tk.StringVar(value=self.store.get("schedule", "close_h", "04"))
        self.close_m = tk.StringVar(value=self.store.get("schedule", "close_m", "00"))
        self.open_h = tk.StringVar(value=self.store.get("schedule", "open_h", "04"))
        self.open_m = tk.StringVar(value=self.store.get("schedule", "open_m", "20"))
        self._time_row(sched, 1, "Hẹn giờ tắt game:", self.close_h, self.close_m)
        self.shutdown = tk.BooleanVar(value=self.store.get_bool("schedule", "shutdown", False))
        tk.Checkbutton(
            sched, text="Tắt máy sau khi tắt game",
            variable=self.shutdown, bg=BG, command=self.apply_schedule,
        ).grid(row=1, column=4, sticky="w", padx=8)
        self._time_row(sched, 2, "Hẹn giờ mở game:", self.open_h, self.open_m)

        aft = tk.Frame(sched, bg=BG)
        aft.grid(row=3, column=0, columnspan=5, sticky="w", padx=4, pady=2)
        tk.Label(aft, text="Sau khi login:", bg=BG, font=("Segoe UI", 9, "bold")).pack(side="left")
        self.after_login = tk.StringVar(value=self.store.get("schedule", "after_login", "Chờ"))
        for x in ["Chờ", "Party", "Train", "Train LSV", "Dồn vàng"]:
            tk.Radiobutton(
                aft, text=x, value=x, variable=self.after_login, bg=BG,
                command=self.apply_schedule,
            ).pack(side="left", padx=3)

        box = labelframe(self, "Cấu hình tài khoản")
        box.pack(fill="both", expand=True, padx=5, pady=2)
        flag = tk.Frame(box, bg=BG)
        flag.pack(fill="x")
        tk.Label(flag, text="Chọn tài khoản muốn login", bg=BG).pack(side="left", padx=4)
        self.show_password = tk.BooleanVar(value=False)
        tk.Checkbutton(
            flag, text="Hiện mật khẩu", variable=self.show_password,
            bg=BG, command=self.toggle_password,
        ).pack(side="left", padx=8)

        table_outer = tk.Frame(box, bg=BG)
        table_outer.pack(fill="both", expand=True, padx=3)
        self.accounts_canvas, table = add_vertical_scroll(table_outer)
        self.accounts_table = table

        self.select_all_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            table, variable=self.select_all_var, bg=BG,
            command=self.toggle_all_accounts,
        ).grid(row=0, column=0)
        account_table_header(
            table,
            [("Tài khoản", 14), ("Mật khẩu", 12), ("Ẩn captcha", 9), ("Login", 5), ("Proxy", 5)],
            start_col=1,
        )

        saved = self.store.get_json("accounts", "rows", [])
        self.account_rows: list[dict[str, object]] = []
        for i in range(self.ROWS):
            rec = saved[i] if i < len(saved) and isinstance(saved[i], dict) else {}
            enabled = tk.BooleanVar(value=bool(rec.get("enabled", False)))
            user = tk.StringVar(value=str(rec.get("username", "")))
            pwd = tk.StringVar(value=str(rec.get("password", "")))
            cap = tk.StringVar(value=str(rec.get("captcha", "Không")))
            if cap.get() not in {"Không", "Tool", "Proxy"}:
                cap.set("Không")
            proxy = tk.StringVar(value=str(rec.get("proxy", "")))

            tk.Checkbutton(table, variable=enabled, bg=BG).grid(row=i + 1, column=0)
            tk.Entry(table, textvariable=user, width=14).grid(row=i + 1, column=1, sticky="ew", padx=1, pady=2)
            pass_entry = tk.Entry(table, textvariable=pwd, width=12, show="*")
            pass_entry.grid(row=i + 1, column=2, sticky="ew", padx=1, pady=2)
            combo = ttk.Combobox(
                table, textvariable=cap, values=["Không", "Tool", "Proxy"],
                state="readonly", width=8,
            )
            combo.grid(row=i + 1, column=3, padx=1)
            login_btn = button(table, "▶", lambda ii=i: self.login_one(ii), "green", width=2)
            login_btn.grid(row=i + 1, column=4, padx=1)
            proxy_btn = button(table, "⇄", lambda ii=i: self.proxy_one(ii), "blue", width=2)
            proxy_btn.grid(row=i + 1, column=5, padx=1)
            row = {
                "enabled": enabled, "username": user, "password": pwd,
                "captcha": cap, "proxy": proxy, "password_entry": pass_entry,
                "captcha_combo": combo, "login_btn": login_btn, "proxy_btn": proxy_btn,
            }
            self.account_rows.append(row)
            combo.bind("<<ComboboxSelected>>", lambda _e, ii=i: self.on_captcha_mode_change(ii))
            self.on_captcha_mode_change(i, popup=False)

        self.start_button = start_bar(self, self.start_login)
        self.apply_schedule()

    def _time_row(self, parent, row, label, hv, mv):
        tk.Label(parent, text=label, bg=BG).grid(row=row, column=0, sticky="w", padx=4, pady=2)
        h = ttk.Combobox(parent, textvariable=hv, values=[f"{i:02d}" for i in range(24)], width=4, state="readonly")
        h.grid(row=row, column=1)
        tk.Label(parent, text=":", bg=BG).grid(row=row, column=2)
        m = ttk.Combobox(parent, textvariable=mv, values=[f"{i:02d}" for i in range(60)], width=4, state="readonly")
        m.grid(row=row, column=3)
        h.bind("<<ComboboxSelected>>", lambda _e: self.apply_schedule())
        m.bind("<<ComboboxSelected>>", lambda _e: self.apply_schedule())

    def _game_status(self):
        if self.game_dir:
            return f"✓ Đã chọn game thành công: {self.game_dir}"
        return "Đường dẫn game: (Chưa chọn)"

    def choose_game(self):
        d = filedialog.askdirectory(title="Chọn thư mục game")
        if d:
            self.game_dir = d
            self.store.set("game", "directory", d)
            self.store.save()
            self.game_status.config(text=self._game_status())

    def open_game(self):
        if not self.game_dir or not self.backend.winapi.launch_game(self.game_dir):
            messagebox.showwarning("TLMTool", "Không tìm thấy file Thần Long  Mobile.exe")

    def toggle_password(self):
        for row in self.account_rows:
            row["password_entry"].config(show="" if self.show_password.get() else "*")

    def toggle_all_accounts(self):
        value = self.select_all_var.get()
        for row in self.account_rows:
            row["enabled"].set(value)

    def on_captcha_mode_change(self, index: int, popup: bool = True):
        row = self.account_rows[index]
        mode = row["captcha"].get()
        btn = row["proxy_btn"]
        if mode == "Không":
            btn.config(text="⇄", state="disabled", bg="#e0e0e0")
        elif mode == "Tool":
            btn.config(text="⇄", state="normal", bg="#3465d9")
        else:
            btn.config(text="➜", state="normal", bg="#3465d9")
            if popup:
                self.edit_row_proxy(index)
        self._schedule_save_accounts()

    def edit_row_proxy(self, index: int):
        row = self.account_rows[index]
        value = simpledialog.askstring(
            "Proxy riêng",
            "Nhập proxy riêng (protocol://user:pass@ip:port hoặc user:pass:ip:port)",
            initialvalue=row["proxy"].get(),
            parent=self,
        )
        if value is not None:
            row["proxy"].set(value.strip())
            self.save_accounts()

    def proxy_one(self, index):
        row = self.account_rows[index]
        mode = row["captcha"].get()
        if mode == "Không":
            self.app.set_status(f"Dòng {index + 1}: ẩn captcha = Không (direct).")
            return
        if mode == "Proxy":
            self.edit_row_proxy(index)
            return
        # Tool mode is intentionally fail-closed until the bundled forwarder
        # protocol is ported.  Do not pretend a proxy rotation succeeded.
        self.app.set_status(f"Dòng {index + 1}: forwarder Tool chưa được kết nối.")

    def _schedule_save_accounts(self):
        try:
            self.after_cancel(getattr(self, "_save_after_id", ""))
        except Exception:
            pass
        self._save_after_id = self.after(250, self.save_accounts)

    def save_accounts(self):
        rows = []
        for row in self.account_rows:
            rows.append({
                "enabled": row["enabled"].get(),
                "username": row["username"].get(),
                "password": row["password"].get(),
                "captcha": row["captcha"].get(),
                "proxy": row["proxy"].get(),
            })
        self.store.set("accounts", "rows", rows)
        self.store.save()

    def _selected_indices(self):
        return [
            i for i, row in enumerate(self.account_rows)
            if row["enabled"].get() and row["username"].get().strip() and row["password"].get()
        ]

    def start_login(self):
        if self._batch_running:
            self._batch_cancel.set()
            self.app.set_status("Đang dừng batch login...")
            return
        self.save_accounts()
        selected = self._selected_indices()
        if not selected:
            self.app.set_status("Chưa chọn tài khoản để login.")
            return
        self._batch_cancel.clear()
        self._batch_running = True
        self.start_button.config(text="Dừng", bg="#d12228")
        threading.Thread(
            target=self._batch_worker, args=(selected,),
            name="tlm-login-batch", daemon=True,
        ).start()

    def _batch_worker(self, selected: list[int]):
        successes = 0
        try:
            windows = self._ensure_windows(len(selected))
            for pos, index in enumerate(selected):
                if self._batch_cancel.is_set():
                    break
                if pos >= len(windows):
                    break
                if self._login_row_to_window(index, windows[pos]):
                    successes += 1
            if not self._batch_cancel.is_set() and successes == len(selected):
                self.after(0, self._dispatch_after_login)
        finally:
            self.after(0, self._finish_batch)

    def _finish_batch(self):
        self._batch_running = False
        self.start_button.config(text="Bắt đầu", bg=GREEN)

    def _ensure_windows(self, count: int):
        windows = self.backend.windows()
        if len(windows) >= count:
            return windows[:count]
        if not self.game_dir:
            self.after(0, lambda: self.app.set_status("Chưa chọn thư mục game."))
            return windows
        deadline = time.monotonic() + 30.0
        while len(windows) < count and not self._batch_cancel.is_set():
            if not self.backend.winapi.launch_game(self.game_dir):
                break
            known = {w.hwnd for w in windows}
            wait_until = min(deadline, time.monotonic() + 8.0)
            while time.monotonic() < wait_until and not self._batch_cancel.is_set():
                time.sleep(0.2)
                current = self.backend.windows()
                if any(w.hwnd not in known for w in current):
                    windows = current
                    break
            if time.monotonic() >= deadline:
                break
        return self.backend.windows()[:count]

    def login_one(self, index):
        row = self.account_rows[index]
        username, password = row["username"].get().strip(), row["password"].get()
        if not username or not password:
            self.app.set_status("Thiếu tài khoản hoặc mật khẩu.")
            return
        windows = self.backend.windows()
        if index < len(windows):
            gw = windows[index]
            threading.Thread(
                target=lambda: self._login_row_to_window(index, gw),
                name=f"tlm-login-{gw.pid}", daemon=True,
            ).start()
            return

        def launch_and_login():
            current = self._ensure_windows(index + 1)
            if index >= len(current):
                self.after(0, lambda: self.app.set_status("Không mở được cửa sổ game tương ứng."))
                return
            self._login_row_to_window(index, current[index])

        threading.Thread(target=launch_and_login, name=f"tlm-login-launch-{index}", daemon=True).start()

    def _login_row_to_window(self, index: int, gw) -> bool:
        row = self.account_rows[index]
        username = row["username"].get().strip()
        password = row["password"].get()
        try:
            # Exact coordinate baseline recovered from TLM 2.1.2.
            if self._batch_cancel.is_set():
                return False
            self.backend.winapi.scaled_click(gw.hwnd, 613, 302)
            time.sleep(.15)
            self.backend.winapi.select_all(gw.hwnd)
            time.sleep(.05)
            self.backend.winapi.type_text(gw.hwnd, username)
            time.sleep(.15)
            self.backend.winapi.scaled_click(gw.hwnd, 573, 362)
            time.sleep(.15)
            self.backend.winapi.select_all(gw.hwnd)
            time.sleep(.05)
            self.backend.winapi.type_text(gw.hwnd, password)
            time.sleep(.15)
            self.backend.winapi.scaled_click(gw.hwnd, 684, 506)
            self.after(0, lambda: self.app.set_status(f"Đã gửi login: {username}"))

            # TLM waits for actual in-game state.  A request sent is not
            # considered success; prove the role exists through the semantic bridge.
            deadline = time.monotonic() + 100.0
            while time.monotonic() < deadline and not self._batch_cancel.is_set():
                if not self.backend.winapi.is_window(gw.hwnd):
                    return False
                snap = self.backend.driver.read_snapshot(gw)
                if snap and snap.role_id > 0 and snap.map_ready:
                    self._online[index] = gw.hwnd
                    self.after(0, lambda: row["login_btn"].config(text="Ⅱ", bg="#d12228"))
                    self.after(0, lambda: self.app.set_status(f"✓ Hoàn tất login: {username}"))
                    return True
                time.sleep(.5)
            self.after(0, lambda: self.app.set_status(f"Timeout chờ vào game: {username}"))
            return False
        except Exception as exc:
            self.after(0, lambda: self.app.set_status(f"Login lỗi: {exc}"))
            return False

    def _dispatch_after_login(self):
        mode = self.after_login.get()
        if mode == "Chờ":
            return

        # TLM 2.1.2 does not dispatch these choices through one generic
        # gameplay action. It switches to the target tab, waits for that tab's
        # account scan, then starts the tab-specific toggle.
        targets = {
            "Party": (2, "toggle_run"),
            "Train": (3, "_toggle_farm"),
            "Train LSV": (4, "_toggle_farm"),
            "Dồn vàng": (7, "_toggle_farm"),
        }
        target = targets.get(mode)
        if target is None:
            return
        tab_index, method_name = target
        self.app.notebook.select(tab_index)

        def activate():
            tab = self.app.tabs[tab_index]
            method = getattr(tab, method_name, None)
            if callable(method):
                method()
            else:
                self.app.set_status(f"[LOGIN] {mode}: workflow đang chờ hoàn thiện.")

        self.after(350, activate)

    def apply_schedule(self):
        for k, v in [
            ("enabled", self.schedule_enabled.get()),
            ("close_h", self.close_h.get()), ("close_m", self.close_m.get()),
            ("open_h", self.open_h.get()), ("open_m", self.open_m.get()),
            ("after_login", self.after_login.get()), ("shutdown", self.shutdown.get()),
        ]:
            self.store.set("schedule", k, v)
        self.store.save()
        if self.schedule_enabled.get():
            self.schedule.start(
                (int(self.close_h.get()), int(self.close_m.get())),
                (int(self.open_h.get()), int(self.open_m.get())),
                lambda: self.after(0, self.scheduled_close),
                lambda: self.after(0, self.scheduled_open),
            )
        else:
            self.schedule.stop()

    def scheduled_close(self):
        for g in self.backend.windows():
            self.backend.winapi.close(g.hwnd)
        if self.shutdown.get() and os.name == "nt":
            os.system("shutdown /s /t 5")

    def scheduled_open(self):
        self.open_game()
        self.after(3000, self.start_login)


def checks(parent, texts):
    for t in texts: tk.Checkbutton(parent,text=t,bg=BG).pack(anchor="w",padx=5)


class PartyTab(BaseTab):
    MAX_GROUP_MEMBERS = 6

    def __init__(self, master, app):
        super().__init__(master, app)
        self._runtime: dict[str, tuple[object, object]] = {}
        self._refresh_busy = False
        self._closed = False
        self._batch_running = False
        self._batch_cancel = threading.Event()
        self.groups: list[dict[str, object]] = []

        post = labelframe(self, "Sau khi party")
        post.pack(fill="x", padx=5, pady=(5, 2))
        row = tk.Frame(post, bg=BG)
        row.pack(fill="x", padx=4, pady=3)
        tk.Label(row, text="Sau khi party:", bg=BG, font=("Segoe UI", 9, "bold")).pack(side="left")
        self.after = tk.StringVar(value=self.store.get("party", "after", "Chờ"))
        for x in ["Chờ", "Train", "Train LSV", "Dồn vàng", "Phó bản"]:
            tk.Radiobutton(
                row, text=x, value=x, variable=self.after, bg=BG,
                command=self.save_config,
            ).pack(side="left", padx=3)

        ready = labelframe(self, "Cấu hình tổ đội")
        ready.pack(fill="x", padx=5, pady=2)
        self.ready_label = tk.Label(
            ready, text="Danh sách acc sẵn sàng:", bg=BG,
            font=("Segoe UI", 9, "bold"), anchor="w", justify="left",
        )
        self.ready_label.pack(fill="x", padx=4, pady=4)

        groups = labelframe(self, "Cấu hình nhóm")
        groups.pack(fill="x", padx=5, pady=2)
        self.holder = tk.Frame(groups, bg=BG)
        self.holder.pack(fill="x", padx=4)

        saved = self.store.get_json("party", "groups", [])
        if not isinstance(saved, list) or not saved:
            saved = [["", "", "", "", "", ""], ["", "", "", "", "", ""]]
        for members in saved:
            if isinstance(members, list):
                self.add_group(members)
        if not self.groups:
            self.add_group()
        button(groups, "+ Thêm nhóm", self.add_group, "green").pack(anchor="w", padx=4, pady=6)

        self.start_button = start_bar(self, self.toggle_run)
        self.after(250, self._schedule_refresh)

    def _schedule_refresh(self):
        if self._closed:
            return
        if not self._refresh_busy:
            self._refresh_busy = True
            threading.Thread(target=self._refresh_worker, name="tlm-party-scan", daemon=True).start()
        self.after(3000, self._schedule_refresh)

    def _refresh_worker(self):
        catalog: dict[str, tuple[object, object]] = {}
        try:
            for gw in self.backend.windows():
                if self._closed:
                    return
                snap = self.backend.driver.read_snapshot(gw)
                if not snap or snap.role_id <= 0 or not snap.name:
                    continue
                catalog[snap.name.strip()] = (gw, snap)
        finally:
            if not self._closed:
                self.after(0, lambda data=catalog: self._apply_runtime(data))

    def _apply_runtime(self, catalog):
        self._runtime = catalog
        self._refresh_busy = False
        names = sorted(catalog, key=str.casefold)
        suffix = ", ".join(names) if names else ""
        self.ready_label.config(text="Danh sách acc sẵn sàng:" + (f" {suffix}" if suffix else ""))
        for gd in self.groups:
            for cb in gd["combos"]:
                cb.configure(values=names)

    def add_group(self, members=None):
        n = len(self.groups) + 1
        frame = tk.LabelFrame(self.holder, text=f"Nhóm {n}", bg=BG, font=("Segoe UI", 9, "bold"))
        frame.pack(fill="x", pady=2)

        top = tk.Frame(frame, bg=BG)
        top.pack(fill="x")
        tk.Label(top, text="Trưởng nhóm:", bg=BG, font=("Segoe UI", 9, "bold")).pack(side="left", padx=(4, 2))
        leader_label = tk.Label(top, text="(chưa chọn)", bg=BG, fg=GRAY)
        leader_label.pack(side="left")
        button(top, "✕ Xóa nhóm", lambda f=frame: self.delete_group(f), "red").pack(side="right", padx=2)
        button(top, "Rời nhóm", lambda f=frame: self.leave_group(f), "blue").pack(side="right", padx=2)

        grid = tk.Frame(frame, bg=BG)
        grid.pack(fill="x", padx=4, pady=2)
        vars_, combos = [], []
        src = list(members or [])[:self.MAX_GROUP_MEMBERS]
        src += [""] * (self.MAX_GROUP_MEMBERS - len(src))
        for i in range(self.MAX_GROUP_MEMBERS):
            var = tk.StringVar(value=src[i])
            cb = ttk.Combobox(grid, textvariable=var, width=15, state="readonly", values=sorted(self._runtime))
            cb.grid(row=i // 3, column=i % 3, padx=2, pady=2, sticky="ew")
            cb.bind("<<ComboboxSelected>>", lambda _e, f=frame: self._group_changed(f))
            vars_.append(var)
            combos.append(cb)
        for col in range(3):
            grid.grid_columnconfigure(col, weight=1)

        run_btn = button(frame, f"▾ Tạo nhóm {n}", lambda f=frame: self.run_single(f), "green")
        run_btn.pack(fill="x", padx=4, pady=(2, 5))
        gd = {
            "frame": frame, "vars": vars_, "combos": combos,
            "leader_label": leader_label, "run_btn": run_btn,
            "cancel": threading.Event(), "running": False,
        }
        self.groups.append(gd)
        self._group_changed(frame, save=False)
        self._renumber_groups()
        self.save_config()

    def _group_for_frame(self, frame):
        for gd in self.groups:
            if gd["frame"] is frame:
                return gd
        return None

    def _group_changed(self, frame, save=True):
        gd = self._group_for_frame(frame)
        if not gd:
            return
        leader = gd["vars"][0].get().strip()
        gd["leader_label"].config(text=leader or "(chưa chọn)", fg="#1565c0" if leader else GRAY)
        if save:
            self.save_config()

    def _renumber_groups(self):
        for i, gd in enumerate(self.groups, 1):
            gd["frame"].config(text=f"Nhóm {i}")
            if not gd["running"]:
                gd["run_btn"].config(text=f"▾ Tạo nhóm {i}")

    def delete_group(self, frame):
        if len(self.groups) <= 1:
            return
        gd = self._group_for_frame(frame)
        if not gd:
            return
        gd["cancel"].set()
        frame.destroy()
        self.groups.remove(gd)
        self._renumber_groups()
        self.save_config()

    def _members(self, gd):
        out = []
        seen = set()
        for var in gd["vars"]:
            name = var.get().strip()
            key = name.casefold()
            if name and key not in seen:
                seen.add(key)
                out.append(name)
        return out

    def save_config(self):
        self.store.set("party", "after", self.after.get())
        self.store.set("party", "groups", [[v.get() for v in gd["vars"]] for gd in self.groups])
        self.store.save()

    def _fresh_catalog(self):
        catalog = {}
        for gw in self.backend.windows():
            snap = self.backend.driver.read_snapshot(gw)
            if snap and snap.role_id > 0 and snap.name:
                catalog[snap.name.strip().casefold()] = (gw, snap)
        return catalog

    def _wait_snapshot(self, gw, predicate, timeout, cancel):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline and not cancel.is_set() and not self._batch_cancel.is_set():
            snap = self.backend.driver.read_snapshot(gw)
            if snap and predicate(snap):
                return snap
            time.sleep(.25)
        return None

    def _leave_members(self, names, cancel):
        catalog = self._fresh_catalog()
        targets = []
        for name in names:
            item = catalog.get(name.casefold())
            if not item:
                continue
            gw, snap = item
            targets.append((name, gw))
            if snap.team_id not in (0, -1):
                result = self.backend.party_leave(gw)
                if not result.ok:
                    self.app.root.after(0, lambda t=result.detail: self.app.set_status(t))
        ok = True
        for name, gw in targets:
            if cancel.is_set() or self._batch_cancel.is_set():
                return False
            snap = self._wait_snapshot(gw, lambda s: s.team_id in (0, -1), 8.0, cancel)
            if not snap:
                ok = False
                self.app.root.after(0, lambda n=name: self.app.set_status(f"[Party] {n}: chưa xác nhận đã rời đội."))
        return ok

    def leave_group(self, frame):
        gd = self._group_for_frame(frame)
        if not gd:
            return
        names = self._members(gd)
        if not names:
            self.app.set_status("[Party] chưa chọn acc nào.")
            return
        cancel = threading.Event()
        threading.Thread(
            target=lambda: self._leave_members(names, cancel),
            name="tlm-party-leave", daemon=True,
        ).start()

    def run_single(self, frame):
        gd = self._group_for_frame(frame)
        if not gd:
            return
        if gd["running"]:
            gd["cancel"].set()
            return
        names = self._members(gd)
        if not names or not gd["vars"][0].get().strip():
            self.app.set_status("[Party] phải chọn trưởng nhóm ở ô đầu tiên.")
            return
        gd["cancel"].clear()
        gd["running"] = True
        gd["run_btn"].config(text="■ Dừng nhóm", bg="#d12228")
        threading.Thread(
            target=self._single_worker, args=(gd, names),
            name="tlm-party-single", daemon=True,
        ).start()

    def _single_worker(self, gd, names):
        try:
            ok = self._run_group(names, gd["cancel"])
            if ok:
                self.app.root.after(0, lambda: self.app.set_status(f"[Party] Hoàn tất: {', '.join(names)}"))
        finally:
            self.app.root.after(0, lambda: self._reset_group_button(gd))

    def _reset_group_button(self, gd):
        gd["running"] = False
        idx = self.groups.index(gd) + 1 if gd in self.groups else 0
        if idx:
            gd["run_btn"].config(text=f"▾ Tạo nhóm {idx}", bg=GREEN)

    def _run_group(self, names, cancel):
        catalog = self._fresh_catalog()
        resolved = []
        for name in names:
            item = catalog.get(name.casefold())
            if not item:
                self.app.root.after(0, lambda n=name: self.app.set_status(f"[Party] {n}: không online."))
                return False
            resolved.append((name, item[0], item[1]))
        leader_name, leader_gw, leader_snap = resolved[0]

        # TLM 2.1.2 first makes every selected account leave its old team and
        # proves TeamID is empty before creating the new group.
        if not self._leave_members(names, cancel):
            return False
        if cancel.is_set() or self._batch_cancel.is_set():
            return False

        leader_snap = self.backend.driver.read_snapshot(leader_gw)
        if not leader_snap:
            return False
        result = self.backend.party_create(leader_gw)
        if not result.ok:
            self.app.root.after(0, lambda t=result.detail: self.app.set_status(f"[Party] {t}"))
            return False
        leader_snap = self._wait_snapshot(
            leader_gw, lambda s: s.team_id not in (0, -1), 8.0, cancel,
        )
        if not leader_snap:
            self.app.root.after(0, lambda: self.app.set_status(f"[Party] {leader_name}: tạo đội chưa được xác nhận."))
            return False
        team_id = leader_snap.team_id
        leader_role_id = leader_snap.role_id

        for member_name, member_gw, member_snap in resolved[1:]:
            if cancel.is_set() or self._batch_cancel.is_set():
                return False
            joined = False
            for _attempt in range(3):
                fresh_member = self.backend.driver.read_snapshot(member_gw)
                fresh_leader = self.backend.driver.read_snapshot(leader_gw)
                if fresh_member and fresh_leader and fresh_member.team_id == fresh_leader.team_id == team_id:
                    joined = True
                    break

                invite = self.backend.party_invite(leader_gw, member_snap.role_id)
                if not invite.ok:
                    time.sleep(.4)
                    continue

                # Original TLM enables AutoAcceptInviteTeam. Until that setting
                # is live-proven through this bridge, use the already-verified
                # request-to-join route as a fail-closed acceptance fallback.
                proven = self._wait_snapshot(member_gw, lambda s: s.team_id == team_id, 1.5, cancel)
                if not proven:
                    self.backend.party_join(member_gw, leader_role_id)
                    proven = self._wait_snapshot(member_gw, lambda s: s.team_id == team_id, 5.0, cancel)
                if proven:
                    joined = True
                    break
            if not joined:
                self.app.root.after(0, lambda n=member_name: self.app.set_status(f"[Party] {n}: chưa vào cùng đội."))
                return False

        # Final proof: all current members share the leader's TeamID.
        for name, gw, _snap in resolved:
            current = self.backend.driver.read_snapshot(gw)
            if not current or current.team_id != team_id:
                self.app.root.after(0, lambda n=name: self.app.set_status(f"[Party] {n}: TeamID không khớp."))
                return False
        return True

    def toggle_run(self):
        if self._batch_running:
            self._batch_cancel.set()
            for gd in self.groups:
                gd["cancel"].set()
            self.app.set_status("[Party] đang dừng...")
            return

        groups = [self._members(gd) for gd in self.groups]
        groups = [g for g in groups if g]
        if not groups:
            self.app.set_status("[Party] chưa chọn nhóm.")
            return
        for gd, names in [(gd, self._members(gd)) for gd in self.groups if self._members(gd)]:
            if not gd["vars"][0].get().strip():
                self.app.set_status("[Party] trưởng nhóm phải nằm ở ô đầu tiên.")
                return
        used = set()
        for names in groups:
            for name in names:
                key = name.casefold()
                if key in used:
                    self.app.set_status(f"[Party] {name} bị chọn ở nhiều nhóm.")
                    return
                used.add(key)

        self.save_config()
        self._batch_cancel.clear()
        self._batch_running = True
        self.start_button.config(text="Dừng", bg="#d12228")
        threading.Thread(target=self._batch_worker, args=(groups,), name="tlm-party-batch", daemon=True).start()

    def _batch_worker(self, groups):
        results = [False] * len(groups)
        threads = []

        def run_one(i, names):
            results[i] = self._run_group(names, self._batch_cancel)

        try:
            for i, names in enumerate(groups):
                t = threading.Thread(target=run_one, args=(i, names), name=f"tlm-party-group-{i+1}", daemon=True)
                threads.append(t)
                t.start()
            for t in threads:
                t.join()
            if all(results) and not self._batch_cancel.is_set():
                self.app.root.after(0, self._after_party_action)
        finally:
            self.app.root.after(0, self._reset_run_button)

    def _reset_run_button(self):
        self._batch_running = False
        self.start_button.config(text="Bắt đầu", bg=GREEN)

    def _after_party_action(self):
        mode = self.after.get()
        targets = {
            "Train": (3, "_toggle_farm"),
            "Train LSV": (4, "_toggle_farm"),
            "Dồn vàng": (7, "_toggle_farm"),
            "Phó bản": (5, "_toggle_run"),
        }
        target = targets.get(mode)
        if not target:
            return
        tab_index, method_name = target
        self.app.notebook.select(tab_index)

        def activate():
            tab = self.app.tabs[tab_index]
            method = getattr(tab, method_name, None)
            if callable(method):
                method()
            else:
                self.app.set_status(f"[Party] Sau khi party={mode}: workflow đang chờ hoàn thiện.")

        self.after(350, activate)

    def stop(self):
        self._closed = True
        self._batch_cancel.set()
        for gd in self.groups:
            gd["cancel"].set()
        self.save_config()


class TrainTab(BaseTab):
    ARRIVE_TOLERANCE = 40
    REFRESH_MS = 2500

    def __init__(self, master, app):
        super().__init__(master, app)
        self._closed = False
        self._refresh_busy = False
        self._running = False
        self._stop_all_event = threading.Event()
        self._session_stops: dict[int, threading.Event] = {}
        self.coord_rows: list[dict[str, object]] = []
        self.account_rows: dict[int, dict[str, object]] = {}
        self.account_config = self.store.get_json("Farm", "accounts", {})

        city = labelframe(self, "Cấu hình Về thành")
        city.pack(fill="x", padx=5, pady=(5, 2))
        r = tk.Frame(city, bg=BG)
        r.pack(fill="x", padx=4, pady=3)
        tk.Label(r, text="Điều kiện về thành:", bg=BG, font=("Segoe UI", 9, "bold")).pack(side="left")
        self.town_condition = tk.StringVar(value=self.store.get("Farm", "town_condition", "period"))
        for text, value in [("Không về", "none"), ("Khi đầy túi", "bag"), ("Theo chu kỳ (phút):", "period")]:
            tk.Radiobutton(
                r, text=text, value=value, variable=self.town_condition, bg=BG,
                command=self._save_config,
            ).pack(side="left", padx=2)
        self.loop_minutes = tk.IntVar(value=max(1, self.store.get_int("Farm", "loop_minutes", 30)))
        self.loop_spin = tk.Spinbox(r, from_=1, to=999, width=4, textvariable=self.loop_minutes, command=self._save_config)
        self.loop_spin.pack(side="left")
        self.loop_spin.bind("<FocusOut>", lambda _e: self._save_config())
        button(r, "Hiện cấu hình", self._toggle_town_config, "gray").pack(side="right")

        self.town_extra = tk.Frame(city, bg=BG)
        self.town_extra_visible = False
        tk.Label(
            self.town_extra,
            text="Bán đồ / mua thuốc / trị liệu sẽ chỉ chạy khi primitive tương ứng đã có state proof.",
            bg=BG, fg=GRAY, anchor="w", wraplength=400,
        ).pack(fill="x", padx=5, pady=(0, 4))

        cfg = labelframe(self, "Cấu hình Train")
        cfg.pack(fill="x", padx=5, pady=2)
        tk.Label(cfg, text="Trong khi train:", bg=BG, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=5)
        self.respawn = tk.BooleanVar(value=self.store.get_bool("Farm", "respawn", False))
        self.auto_reconnect = tk.BooleanVar(value=self.store.get_bool("Farm", "auto_reconnect", False))
        self.pickup_no_cankhon = tk.BooleanVar(value=self.store.get_bool("Farm", "pickup_no_cankhon", False))
        self.heal_after_death = tk.BooleanVar(value=self.store.get_bool("Farm", "heal_after_death", False))
        for text, var in [
            ("Quay lại train khi chết", self.respawn),
            ("Tự kết nối lại khi mất mạng", self.auto_reconnect),
            ("Nhặt đồ không dùng hồ lô (cần khôn hồ)", self.pickup_no_cankhon),
            ("Trị liệu sau khi chết", self.heal_after_death),
        ]:
            tk.Checkbutton(cfg, text=text, variable=var, bg=BG, command=self._save_config).pack(anchor="w", padx=5)

        heal = tk.Frame(cfg, bg=BG)
        heal.pack(fill="x", padx=5)
        tk.Label(heal, text="Tọa độ trị liệu:", bg=BG).pack(side="left")
        self.heal_map = tk.StringVar(value=self.store.get("Farm", "heal_map", "Trị liệu Tô Châu"))
        ttk.Combobox(
            heal, textvariable=self.heal_map,
            values=["Trị liệu Tô Châu", "Trị liệu Đại Lý", "Trị liệu Lạc Dương"],
            state="readonly", width=20,
        ).pack(side="left")

        keep = tk.Frame(cfg, bg=BG)
        keep.pack(fill="x", padx=5)
        tk.Label(keep, text="Lọc đồ giữ lại:", bg=BG, font=("Segoe UI", 9, "bold")).pack(side="left")
        self.pickup_mode = tk.StringVar(value=self.store.get("Farm", "pickup_mode", "Tất cả"))
        for value in ["Không", "Chỉ vũ khí", "Tất cả"]:
            tk.Radiobutton(
                keep, text=value, value=value, variable=self.pickup_mode, bg=BG,
                command=self._save_config,
            ).pack(side="left")

        tk.Label(cfg, text="Dùng thú cưỡi gần được (2x, 4x...):", bg=BG, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=5)
        button(cfg, "+ Thêm", self._add_buff_placeholder, "green").pack(anchor="w", padx=5, pady=3)

        coord = labelframe(self, "Cấu hình tọa độ lưu sẵn")
        coord.pack(fill="x", padx=5, pady=2)
        self.coord_content = tk.Frame(coord, bg=BG)
        self.coord_content.pack(fill="x", padx=4, pady=(2, 0))
        header = tk.Frame(self.coord_content, bg=BG)
        header.pack(fill="x")
        for text, width in [("Tên", 9), ("Map", 12), ("X", 4), ("Y", 4), ("Áp dụng hết", 10), ("Xóa", 4)]:
            tk.Label(header, text=text, bg=BG, font=("Segoe UI", 9, "bold"), width=width).pack(side="left")
        self.coord_body = tk.Frame(self.coord_content, bg=BG)
        self.coord_body.pack(fill="x")
        toolbar = tk.Frame(coord, bg=BG)
        toolbar.pack(fill="x", padx=4, pady=(1, 4))
        button(toolbar, "+ Thêm tọa độ", self._add_coord_row, "green").pack(side="left")
        self.coord_toggle_btn = button(toolbar, "Ẩn danh sách tọa độ", self._toggle_coord_list, "gray")
        self.coord_toggle_btn.pack(side="right")

        lst = labelframe(self, "Danh sách tài khoản")
        lst.pack(fill="both", expand=True, padx=5, pady=2)
        account_table_header(lst, [("Nhân vật", 18), ("Tọa độ bán", 14), ("Tọa độ Train", 14)])
        self.account_body = tk.Frame(lst, bg=BG)
        self.account_body.grid(row=1, column=0, columnspan=3, sticky="nsew")
        lst.grid_columnconfigure(0, weight=1)
        lst.grid_columnconfigure(1, weight=1)
        lst.grid_columnconfigure(2, weight=1)

        bar = tk.Frame(self, bg=BG)
        bar.pack(side="bottom", fill="x", padx=7)
        tk.Label(bar, text="Điều khiển tất cả:", bg=BG, font=("Segoe UI", 9, "bold")).pack(side="left")
        button(bar, "Tới bán đồ", lambda: self._move_all("sell"), "blue").pack(side="left", padx=2)
        button(bar, "Bán đồ", self._sell_all_pending, "blue").pack(side="left", padx=2)
        button(bar, "Tới bãi train", lambda: self._move_all("farm"), "blue").pack(side="left", padx=2)
        button(bar, "Đánh", self._fight_all, "blue").pack(side="left", padx=2)
        self.start_button = start_bar(self, self._toggle_farm)

        self._load_coords()
        self._save_config()
        self.after(100, self._refresh_accounts)

    def _toggle_town_config(self):
        self.town_extra_visible = not self.town_extra_visible
        if self.town_extra_visible:
            self.town_extra.pack(fill="x", padx=4, pady=(0, 2))
        else:
            self.town_extra.pack_forget()

    def _add_buff_placeholder(self):
        self.app.set_status("[Train] Buff theo thời gian đang chờ port đúng runtime TLM.")

    def _save_config(self):
        self.store.set("Farm", "town_condition", self.town_condition.get())
        self.store.set("Farm", "loop_minutes", max(1, int(self.loop_minutes.get() or 1)))
        self.store.set("Farm", "respawn", self.respawn.get())
        self.store.set("Farm", "auto_reconnect", self.auto_reconnect.get())
        self.store.set("Farm", "pickup_no_cankhon", self.pickup_no_cankhon.get())
        self.store.set("Farm", "heal_after_death", self.heal_after_death.get())
        self.store.set("Farm", "pickup_mode", self.pickup_mode.get())
        self.store.set("Farm", "heal_map", self.heal_map.get())
        self.store.save()

    def _coord_names(self):
        return [row["name"].get().strip() for row in self.coord_rows if row["name"].get().strip()]

    def _coord_record(self, name: str):
        for row in self.coord_rows:
            if row["name"].get().strip() != name:
                continue
            map_name = row["map"].get().strip()
            try:
                x = int(row["x"].get())
                y = int(row["y"].get())
            except (TypeError, ValueError):
                return None
            map_id = map_name_to_id().get(map_name, 0)
            if map_id <= 0:
                return None
            return {"name": name, "map_name": map_name, "map_id": map_id, "x": x, "y": y}
        return None

    def _save_coords(self):
        rows = []
        for row in self.coord_rows:
            name = row["name"].get().strip()
            map_name = row["map"].get().strip()
            try:
                x, y = int(row["x"].get()), int(row["y"].get())
            except (TypeError, ValueError):
                x, y = 0, 0
            if name:
                rows.append({"name": name, "map": map_name, "x": x, "y": y})
        self.store.set("Farm", "coords", rows)
        self.store.save()
        self._refresh_coord_choices()

    def _load_coords(self):
        for rec in self.store.get_json("Farm", "coords", []):
            if isinstance(rec, dict):
                self._add_coord_row(rec, save=False)
        self._refresh_coord_choices()

    def _add_coord_row(self, rec=None, save=True):
        if rec is None:
            rec = {
                "name": f"Tọa độ {len(self.coord_rows) + 1}",
                "map": "Đại Lý",
                "x": 0,
                "y": 0,
            }
        frame = tk.Frame(self.coord_body, bg=BG)
        frame.pack(fill="x", pady=1)
        name = tk.StringVar(value=str(rec.get("name", "")))
        map_var = tk.StringVar(value=str(rec.get("map", "Đại Lý")))
        x_var = tk.StringVar(value=str(rec.get("x", 0)))
        y_var = tk.StringVar(value=str(rec.get("y", 0)))
        name_entry = tk.Entry(frame, textvariable=name, width=9)
        name_entry.pack(side="left")
        map_cb = ttk.Combobox(frame, textvariable=map_var, values=map_names(), state="readonly", width=11)
        map_cb.pack(side="left", padx=1)
        x_entry = tk.Entry(frame, textvariable=x_var, width=4)
        x_entry.pack(side="left", padx=1)
        y_entry = tk.Entry(frame, textvariable=y_var, width=4)
        y_entry.pack(side="left", padx=1)
        row = {"frame": frame, "name": name, "map": map_var, "x": x_var, "y": y_var}
        button(frame, "Train", lambda r=row: self._apply_coord_to_all(r), "green", width=8).pack(side="left", padx=1)
        button(frame, "✕", lambda r=row: self._remove_coord_row(r), "red", width=2).pack(side="left", padx=1)
        self.coord_rows.append(row)
        for widget in (name_entry, x_entry, y_entry):
            widget.bind("<FocusOut>", lambda _e: self._save_coords())
        map_cb.bind("<<ComboboxSelected>>", lambda _e: self._save_coords())
        if save:
            self._save_coords()
        return row

    def _remove_coord_row(self, row):
        if row not in self.coord_rows:
            return
        row["frame"].destroy()
        self.coord_rows.remove(row)
        self._save_coords()

    def _toggle_coord_list(self):
        visible = self.coord_content.winfo_ismapped()
        if visible:
            self.coord_content.pack_forget()
            self.coord_toggle_btn.config(text="Hiện danh sách tọa độ")
        else:
            self.coord_content.pack(fill="x", padx=4, pady=(2, 0), before=self.coord_toggle_btn.master)
            self.coord_toggle_btn.config(text="Ẩn danh sách tọa độ")

    def _apply_coord_to_all(self, coord_row):
        name = coord_row["name"].get().strip()
        if not name:
            return
        for row in self.account_rows.values():
            row["farm"].set(name)
        self._save_account_config()

    def _refresh_coord_choices(self):
        values = self._coord_names()
        for row in self.account_rows.values():
            row["sell_cb"].configure(values=values)
            row["farm_cb"].configure(values=values)
            if row["sell"].get() not in values:
                row["sell"].set("")
            if row["farm"].get() not in values:
                row["farm"].set(values[0] if values else "")

    def _save_account_config(self):
        data = {}
        for row in self.account_rows.values():
            name = row["name"].get().strip()
            if not name:
                continue
            data[name] = {
                "enabled": row["enabled"].get(),
                "sell": row["sell"].get(),
                "farm": row["farm"].get(),
            }
        self.account_config = data
        self.store.set("Farm", "accounts", data)
        self.store.save()

    def _refresh_accounts(self):
        if self._closed:
            return
        if self._refresh_busy:
            self.after(self.REFRESH_MS, self._refresh_accounts)
            return
        self._refresh_busy = True
        windows = self.backend.windows()

        def worker():
            infos = []
            for gw in windows:
                snap = self.backend.driver.read_snapshot(gw)
                infos.append((gw, snap))
            self.after(0, lambda: self._apply_accounts(infos))

        threading.Thread(target=worker, name="tlm-train-refresh", daemon=True).start()

    def _apply_accounts(self, infos):
        if self._closed:
            return
        seen = set()
        values = self._coord_names()
        for gw, snap in infos:
            seen.add(gw.hwnd)
            row = self.account_rows.get(gw.hwnd)
            role_name = (snap.name if snap and snap.name else "") or gw.title or f"PID {gw.pid}"
            if row is None:
                cfg = self.account_config.get(role_name, {}) if isinstance(self.account_config, dict) else {}
                frame = tk.Frame(self.account_body, bg=BG)
                frame.pack(fill="x", pady=1)
                enabled = tk.BooleanVar(value=bool(cfg.get("enabled", True)))
                name = tk.StringVar(value=role_name)
                sell = tk.StringVar(value=str(cfg.get("sell", "")))
                farm_default = str(cfg.get("farm", values[0] if values else ""))
                farm = tk.StringVar(value=farm_default)
                tk.Checkbutton(frame, variable=enabled, bg=BG, command=self._save_account_config).pack(side="left")
                name_label = tk.Label(frame, textvariable=name, bg=BG, width=14, anchor="w")
                name_label.pack(side="left")
                sell_cb = ttk.Combobox(frame, textvariable=sell, values=values, state="readonly", width=10)
                sell_cb.pack(side="left", padx=1)
                farm_cb = ttk.Combobox(frame, textvariable=farm, values=values, state="readonly", width=10)
                farm_cb.pack(side="left", padx=1)
                row = {
                    "frame": frame, "gw": gw, "snapshot": snap, "enabled": enabled,
                    "name": name, "name_label": name_label, "sell": sell, "farm": farm,
                    "sell_cb": sell_cb, "farm_cb": farm_cb,
                }
                play = button(frame, "▶", lambda r=row: self._toggle_single_farm(r), "green", width=2)
                play.pack(side="left", padx=1)
                row["play"] = play
                sell_cb.bind("<<ComboboxSelected>>", lambda _e: self._save_account_config())
                farm_cb.bind("<<ComboboxSelected>>", lambda _e: self._save_account_config())
                self.account_rows[gw.hwnd] = row
            else:
                row["gw"] = gw
                row["snapshot"] = snap
                if role_name and row["name"].get() != role_name:
                    row["name"].set(role_name)
            if snap:
                row["name_label"].config(fg=GREEN if snap.map_ready else GRAY)
        for hwnd in list(self.account_rows):
            if hwnd in seen:
                continue
            row = self.account_rows.pop(hwnd)
            stop = self._session_stops.pop(hwnd, None)
            if stop:
                stop.set()
            row["frame"].destroy()
        self._refresh_busy = False
        self._refresh_coord_choices()
        self.after(self.REFRESH_MS, self._refresh_accounts)

    def _checked_rows(self):
        return [row for row in self.account_rows.values() if row["enabled"].get()]

    def _row_coord(self, row, kind):
        return self._coord_record(row[kind].get())

    @staticmethod
    def _at_coord(snapshot, coord):
        if not snapshot or not snapshot.map_ready or snapshot.waiting_change_map:
            return False
        if snapshot.map_id != coord["map_id"]:
            return False
        dx = int(snapshot.x) - int(coord["x"])
        dy = int(snapshot.y) - int(coord["y"])
        return dx * dx + dy * dy <= TrainTab.ARRIVE_TOLERANCE * TrainTab.ARRIVE_TOLERANCE

    def _set_row_state(self, row, text, running=None):
        def apply():
            if row["frame"].winfo_exists():
                row["name_label"].config(text=f'{row["name"].get()} • {text}')
                if running is not None:
                    row["play"].config(text="■" if running else "▶", bg="#d12228" if running else GREEN)
        self.after(0, apply)

    def _move_worker(self, row, coord, cancel):
        gw = row["gw"]
        snap = self.backend.driver.read_snapshot(gw)
        if self._at_coord(snap, coord):
            self._set_row_state(row, "Đã tới")
            return True
        result = self.backend.start_path(gw, coord["map_id"], coord["x"], coord["y"])
        if not result.ok:
            self._set_row_state(row, "Lỗi di chuyển")
            self.after(0, lambda t=result.detail: self.app.set_status(f"[Train] {t}"))
            return False
        self._set_row_state(row, "Đang di chuyển")
        deadline = time.monotonic() + 90.0
        while time.monotonic() < deadline and not cancel.is_set() and not self._stop_all_event.is_set():
            snap = self.backend.driver.read_snapshot(gw)
            if self._at_coord(snap, coord):
                if snap and snap.auto_pathing:
                    self.backend.stop_path(gw)
                self._set_row_state(row, "Đã tới")
                return True
            time.sleep(.25)
        self.backend.stop_path(gw)
        self._set_row_state(row, "Di chuyển timeout")
        return False

    def _fight_worker(self, row, cancel):
        gw = row["gw"]
        result = self.backend.start_auto_fight(gw)
        if not result.ok:
            self._set_row_state(row, "Không bật Đánh")
            self.after(0, lambda t=result.detail: self.app.set_status(f"[Train] {t}"))
            return False
        deadline = time.monotonic() + 6.0
        while time.monotonic() < deadline and not cancel.is_set() and not self._stop_all_event.is_set():
            snap = self.backend.driver.read_snapshot(gw)
            if snap and snap.auto_fight:
                self._set_row_state(row, "Đang đánh", True)
                return True
            time.sleep(.2)
        self._set_row_state(row, "Chưa xác nhận Đánh")
        return False

    def _move_all(self, kind):
        rows = self._checked_rows()
        if not rows:
            self.app.set_status("[Train] Chưa chọn tài khoản.")
            return
        jobs = []
        for row in rows:
            coord = self._row_coord(row, kind)
            if not coord:
                self.app.set_status(f"[Train] {row['name'].get()}: chưa chọn tọa độ {kind}.")
                continue
            jobs.append((row, coord))
        if not jobs:
            return
        cancel = threading.Event()

        def run():
            for row, coord in jobs:
                if cancel.is_set():
                    break
                self._move_worker(row, coord, cancel)

        threading.Thread(target=run, name=f"tlm-train-move-{kind}", daemon=True).start()

    def _fight_all(self):
        rows = self._checked_rows()
        if not rows:
            self.app.set_status("[Train] Chưa chọn tài khoản.")
            return
        cancel = threading.Event()
        for row in rows:
            threading.Thread(
                target=self._fight_worker, args=(row, cancel),
                name=f"tlm-train-fight-{row['gw'].pid}", daemon=True,
            ).start()

    def _sell_all_pending(self):
        self.app.set_status("[Train] Bán đồ đang chờ port primitive bag/shop từ 12.4.2.")

    def _toggle_single_farm(self, row):
        hwnd = row["gw"].hwnd
        active = self._session_stops.get(hwnd)
        if active is not None:
            active.set()
            return
        coord = self._row_coord(row, "farm")
        if not coord:
            self.app.set_status(f"[Train] {row['name'].get()}: chưa chọn tọa độ Train.")
            return
        self._save_config()
        self._save_account_config()
        cancel = threading.Event()
        self._session_stops[hwnd] = cancel
        config = {
            "respawn": self.respawn.get(),
            "town_condition": self.town_condition.get(),
            "loop_minutes": max(1, int(self.loop_minutes.get() or 1)),
            "heal_after_death": self.heal_after_death.get(),
            "auto_reconnect": self.auto_reconnect.get(),
        }
        self._set_row_state(row, "Khởi động", True)
        threading.Thread(
            target=self._farm_worker, args=(row, coord, config, cancel),
            name=f"tlm-train-{row['gw'].pid}", daemon=True,
        ).start()

    def _farm_worker(self, row, coord, config, cancel):
        gw = row["gw"]
        started = time.monotonic()
        try:
            if not self._move_worker(row, coord, cancel):
                return
            if not self._fight_worker(row, cancel):
                return
            while not cancel.wait(.75) and not self._stop_all_event.is_set():
                snap = self.backend.driver.read_snapshot(gw)
                if not snap:
                    self._set_row_state(row, "Chờ snapshot", True)
                    continue
                if snap.is_dead:
                    self.backend.stop_auto_fight(gw)
                    if not config["respawn"]:
                        self._set_row_state(row, "Đã chết")
                        return
                    self._set_row_state(row, "Đầu thai", True)
                    result = self.backend.revive_normal(gw)
                    if not result.ok:
                        self.after(0, lambda t=result.detail: self.app.set_status(f"[Train] {t}"))
                        return
                    deadline = time.monotonic() + 20.0
                    revived = None
                    while time.monotonic() < deadline and not cancel.is_set():
                        revived = self.backend.driver.read_snapshot(gw)
                        if revived and not revived.is_dead and revived.map_ready:
                            break
                        time.sleep(.3)
                    if not revived or revived.is_dead:
                        self._set_row_state(row, "Hồi sinh timeout")
                        return
                    if config["heal_after_death"]:
                        self.after(0, lambda: self.app.set_status("[Train] Trị liệu sau chết chờ treatment primitive."))
                    if not self._move_worker(row, coord, cancel):
                        return
                    if not self._fight_worker(row, cancel):
                        return
                    started = time.monotonic()
                    continue

                if config["town_condition"] == "bag" and snap.free_bag_space == 0:
                    self.backend.stop_auto_fight(gw)
                    self._set_row_state(row, "Túi đầy • chờ Bán")
                    self.after(0, lambda: self.app.set_status("[Train] Túi đầy: sell workflow chưa được port, đã dừng an toàn."))
                    return
                if config["town_condition"] == "period" and time.monotonic() - started >= config["loop_minutes"] * 60:
                    self.backend.stop_auto_fight(gw)
                    self._set_row_state(row, "Đến chu kỳ • chờ Bán")
                    self.after(0, lambda: self.app.set_status("[Train] Đến chu kỳ về thành: sell/town workflow chưa được port, đã dừng an toàn."))
                    return
                if not snap.auto_fight and snap.map_ready and not snap.waiting_change_map:
                    if not self._fight_worker(row, cancel):
                        return
        finally:
            try:
                self.backend.stop_auto_fight(gw)
            except Exception:
                pass
            self.after(0, lambda h=gw.hwnd, r=row: self._session_finished(h, r))

    def _session_finished(self, hwnd, row):
        self._session_stops.pop(hwnd, None)
        self._set_row_state(row, "Chờ", False)
        if not self._session_stops:
            self._running = False
            self.start_button.config(text="Bắt đầu", bg=GREEN)

    def _toggle_farm(self):
        if self._running or self._session_stops:
            self._stop_all()
            return
        rows = self._checked_rows()
        if not rows:
            self.app.set_status("[Train] Chưa chọn tài khoản.")
            return
        missing = [row["name"].get() for row in rows if not self._row_coord(row, "farm")]
        if missing:
            self.app.set_status(f"[Train] Chưa chọn tọa độ Train: {', '.join(missing[:3])}")
            return
        self._stop_all_event.clear()
        self._running = True
        self.start_button.config(text="Dừng", bg="#d12228")
        for row in rows:
            self._toggle_single_farm(row)

    def _stop_all(self):
        self._stop_all_event.set()
        for stop in list(self._session_stops.values()):
            stop.set()
        rows = list(self.account_rows.values())

        def worker():
            for row in rows:
                try:
                    self.backend.stop_auto_fight(row["gw"])
                    self.backend.stop_path(row["gw"])
                except Exception:
                    pass
            self.after(0, self._finish_stop_all)

        threading.Thread(target=worker, name="tlm-train-stop-all", daemon=True).start()

    def _finish_stop_all(self):
        self._running = False
        self.start_button.config(text="Bắt đầu", bg=GREEN)
        self.app.set_status("[Train] Đã gửi dừng.")

    def stop(self):
        self._closed = True
        self._stop_all_event.set()
        for stop in self._session_stops.values():
            stop.set()
        self._save_config()
        self._save_coords()
        self._save_account_config()


class TrainLsvTab(BaseTab):
    def __init__(self,master,app):
        super().__init__(master,app)
        cfg=labelframe(self,"Cấu hình Train LSV"); cfg.pack(fill="x",padx=5,pady=(5,2)); tk.Label(cfg,text="Trong khi train:",bg=BG,font=("Segoe UI",9,"bold")).pack(anchor="w",padx=5)
        checks(cfg,["Quay lại train khi chết","Tự kết nối lại khi mất mạng","Trị liệu sau khi chết tại Lạc Dương LSV"])
        f=tk.Frame(cfg,bg=BG); f.pack(fill="x",padx=5); tk.Label(f,text="Nhặt đồ:",bg=BG,font=("Segoe UI",9,"bold")).pack(side="left"); v=tk.StringVar(value="Tất cả")
        for x in ["Không","Chỉ vũ khí","Tất cả"]: tk.Radiobutton(f,text=x,value=x,variable=v,bg=BG).pack(side="left")
        tk.Label(cfg,text="Dùng thú cống châu, đan dược (2x, 4x...):",bg=BG,font=("Segoe UI",9,"bold")).pack(anchor="w",padx=5)
        row=tk.Frame(cfg,bg=BG); row.pack(fill="x",padx=5,pady=2); tk.Checkbutton(row,bg=BG).pack(side="left"); tk.Label(row,text="Đạ Minh Châu",fg=PURPLE,bg=BG).pack(side="left"); tk.Label(row,text="Phím:",bg=BG).pack(side="left",padx=(8,1)); ttk.Combobox(row,values=[str(i) for i in range(1,9)],width=3).pack(side="left"); tk.Label(row,text="Thời gian:",bg=BG).pack(side="left",padx=(8,1)); tk.Entry(row,width=2).pack(side="left"); tk.Label(row,text="ph",bg=BG).pack(side="left"); tk.Entry(row,width=2).pack(side="left"); tk.Label(row,text="giây",bg=BG).pack(side="left")
        button(cfg,"+ Thêm",None,"green").pack(anchor="w",padx=5,pady=3)
        coord=labelframe(self,"Cấu hình tọa độ lưu sẵn"); coord.pack(fill="x",padx=5,pady=2); button(coord,"+ Thêm tọa độ",None,"green").pack(side="left",padx=5,pady=5); button(coord,"Ẩn danh sách tọa độ",None,"gray").pack(side="right",padx=5,pady=5)
        lst=labelframe(self,"Danh sách tài khoản"); lst.pack(fill="both",expand=True,padx=5,pady=2); account_table_header(lst,[("Nhân vật",20),("Tọa độ Train",20)])
        bar=tk.Frame(self,bg=BG); bar.pack(side="bottom",fill="x",padx=7); tk.Label(bar,text="Điều khiển tất cả:",bg=BG,font=("Segoe UI",9,"bold")).pack(side="left")
        for t,a in [("Tới LSV",Action.TOI_LSV),("Tới chỗ train",Action.TOI_CHO_TRAIN_LSV),("Đánh",Action.DANH),("Rời LSV",Action.ROI_LSV)]: button(bar,t,lambda aa=a:self.action_all(aa),"purple").pack(side="left",padx=2)
        start_bar(self,lambda:self.action_all(Action.TRAIN_LSV))


class PhoBanTab(BaseTab):
    def __init__(self,master,app):
        super().__init__(master,app)
        ready=labelframe(self,"Cấu hình tổ đội"); ready.pack(fill="x",padx=5,pady=(5,2)); tk.Label(ready,text="Danh sách acc sẵn sàng:",bg=BG,font=("Segoe UI",9,"bold")).pack(anchor="w",padx=4,pady=5)
        cfg=labelframe(self,"Cấu hình phó bản"); cfg.pack(fill="x",padx=5,pady=2)
        g=tk.Frame(cfg,bg=BG); g.pack(fill="x",padx=4)
        for i,t in enumerate(["Tạo lại đội","Theo sau đội trưởng","Nhặt không hồ lô","Vứt trang bị","Vứt vật phẩm","Vứt thuốc","Nga My buff (Sát Trí)"]): tk.Checkbutton(g,text=t,bg=BG).grid(row=i//3,column=i%3,sticky="w",padx=3,pady=2)
        sch=labelframe(self,"Cấu hình lịch trình"); sch.pack(fill="both",expand=True,padx=5,pady=2); tk.Label(sch,text="Nhóm 1",bg=BG,font=("Segoe UI",9,"bold")).pack(anchor="w",padx=4)
        lead=tk.Frame(sch,bg=BG); lead.pack(fill="x",padx=4); tk.Label(lead,text="Đội trưởng:",bg=BG,font=("Segoe UI",9,"bold")).pack(side="left"); ttk.Combobox(lead,width=18).pack(side="left",padx=3); button(lead,"✕ Xóa nhóm",None,"red").pack(side="right")
        mem=tk.Frame(sch,bg=BG); mem.pack(fill="x",padx=4)
        for rr in range(2):
            for cc in range(3): ttk.Combobox(mem,width=15).grid(row=rr,column=cc,padx=2,pady=2)
        b=tk.Frame(sch,bg=BG); b.pack(fill="x",padx=4,pady=3); button(b,"+ Thêm lịch trình",None,"green").pack(side="left"); button(b,"Tắt auto PB",None,"blue").pack(side="left",padx=3); button(b,"Bắt đầu lịch trình",lambda:self.action_all(Action.PHO_BAN),"green").pack(side="left",fill="x",expand=True)
        button(sch,"+ Thêm nhóm",None,"green").pack(side="bottom",anchor="w",padx=4,pady=5); start_bar(self,lambda:self.action_all(Action.PHO_BAN))


class DailyTab(BaseTab):
    def __init__(self,master,app):
        super().__init__(master,app)
        ta=labelframe(self,"Trừng ác"); ta.pack(fill="x",padx=5,pady=(5,2)); tk.Label(ta,text="Cấu hình chung:",bg=BG,font=("Segoe UI",9,"bold")).pack(anchor="w",padx=5)
        row=tk.Frame(ta,bg=BG); row.pack(fill="x",padx=18); tk.Label(row,text="Thời gian đánh tà ác (giây):",bg=BG).pack(side="left"); tk.Spinbox(row,from_=1,to=999,width=4).pack(side="left",padx=6)
        row=tk.Frame(ta,bg=BG); row.pack(fill="x",padx=18); tk.Label(row,text="Cách về NPC nhận nhiệm vụ:",bg=BG).pack(side="left"); v=tk.StringVar(value="Ngựa"); tk.Radiobutton(row,text="Ngựa",value="Ngựa",variable=v,bg=BG).pack(side="left"); tk.Radiobutton(row,text="Định vị phù",value="Định vị phù",variable=v,bg=BG).pack(side="left"); tk.Label(row,text="Phím tắt phù:",bg=BG).pack(side="left"); ttk.Combobox(row,width=4).pack(side="left")
        self.daily_checks(ta); button(ta,"Áp dụng Trừng ác cho tất cả acc",lambda:self.action_all(Action.TRUNG_AC),"brown").pack(fill="x",padx=5,pady=4)
        tb=labelframe(self,"Tàng bảo đồ"); tb.pack(fill="x",padx=5,pady=2); row=tk.Frame(tb,bg=BG); row.pack(fill="x",padx=18,pady=2); tk.Label(row,text="Thời gian đứng trong huyết mộ (giây):",bg=BG).pack(side="left"); tk.Spinbox(row,from_=1,to=999,width=4).pack(side="left",padx=6)
        self.daily_checks(tb,False); button(tb,"Áp dụng Tàng bảo đồ cho tất cả acc",lambda:self.action_all(Action.TANG_BAO_DO),"brown").pack(fill="x",padx=5,pady=4)
        lst=labelframe(self,"Danh sách tài khoản"); lst.pack(fill="both",expand=True,padx=5,pady=2); account_table_header(lst,[("Nhân vật",22),("Hoạt động",22)])
        bar=tk.Frame(self,bg=BG); bar.pack(side="bottom",fill="x",padx=7); tk.Label(bar,text="Điều khiển tất cả:",bg=BG,font=("Segoe UI",9,"bold")).pack(side="left"); button(bar,"Tới bỏ đầu",lambda:self.action_all(Action.TOI_BO_DAU),"brown").pack(side="left",padx=3); button(bar,"Trị liệu",lambda:self.action_all(Action.TRI_LIEU),"brown").pack(side="left"); start_bar(self,lambda:self.action_all(Action.TRUNG_AC))
    def daily_checks(self,p,bag=True):
        row=tk.Frame(p,bg=BG); row.pack(fill="x",padx=5); tk.Checkbutton(row,text="Trị liệu khi HP < 30%",bg=BG).pack(side="left"); tk.Label(row,text="Vị trí trị liệu:",bg=BG).pack(side="left",padx=6); ttk.Combobox(row,values=["Tô Châu","Đại Lý","Lạc Dương"],width=12).pack(side="left")
        if bag: tk.Checkbutton(p,text="Lọc trang bị (vứt vũ khí, trang bị trong quá trình làm nhiệm vụ)",bg=BG).pack(anchor="w",padx=5)
        row=tk.Frame(p,bg=BG); row.pack(fill="x",padx=5); tk.Checkbutton(row,text="Tự kết nối lại khi mất mạng",bg=BG).pack(side="left"); tk.Checkbutton(row,text="Hồi sinh khi chết/Địa phủ",bg=BG).pack(side="left",padx=8)


class DonVangTab(BaseTab):
    def __init__(self,master,app):
        super().__init__(master,app)
        city=labelframe(self,"Cấu hình Về thành"); city.pack(fill="x",padx=5,pady=(5,2)); row=tk.Frame(city,bg=BG); row.pack(fill="x",padx=4); tk.Label(row,text="Điều kiện về thành:",bg=BG,font=("Segoe UI",9,"bold")).pack(side="left"); v=tk.StringVar(value="period"); tk.Radiobutton(row,text="Không về",value="none",variable=v,bg=BG).pack(side="left"); tk.Radiobutton(row,text="Theo chu kỳ (phút):",value="period",variable=v,bg=BG).pack(side="left"); tk.Spinbox(row,from_=1,to=999,width=4).pack(side="left")
        row=tk.Frame(city,bg=BG); row.pack(fill="x",padx=4,pady=2); tk.Label(row,text="Phương thức về thành:",bg=BG,font=("Segoe UI",9,"bold")).pack(side="left"); tk.Label(row,text="Ưu tiên lần lượt:",bg=BG).pack(side="left",padx=5)
        for _ in range(4): ttk.Combobox(row,values=["Phù 1","Phù 2","Phù 3","Ngựa"],width=6).pack(side="left",padx=2)
        cfg=labelframe(self,"Cấu hình Train"); cfg.pack(fill="x",padx=5,pady=2); tk.Label(cfg,text="Trong khi train:",bg=BG,font=("Segoe UI",9,"bold")).pack(anchor="w",padx=5); checks(cfg,["Quay lại train khi chết","Dừng khi mất kết nối mạng","Tự gỡ kẹt","Trị liệu sau khi chết"])
        coord=labelframe(self,"Cấu hình tọa độ lưu sẵn"); coord.pack(fill="x",padx=5,pady=2); button(coord,"+ Thêm tọa độ",None,"green").pack(side="left",padx=5,pady=5); button(coord,"Ẩn danh sách tọa độ",None,"gray").pack(side="right",padx=5,pady=5)
        recv=labelframe(self,"Danh sách nhận"); recv.pack(fill="both",expand=True,padx=5,pady=2)
        for i,label in enumerate(["Tọa độ dồn:","Acc nhận 1:","Acc nhận 2:"]):
            row=tk.Frame(recv,bg=BG); row.pack(fill="x",padx=5,pady=2); tk.Label(row,text=label,bg=BG,width=12,anchor="w").pack(side="left"); ttk.Combobox(row,width=20).pack(side="left")
            if i: button(row,"✕",None,"red",width=2).pack(side="left",padx=8)
        button(recv,"+ Thêm acc nhận",None,"green").pack(anchor="w",padx=5,pady=3)
        bar=tk.Frame(self,bg=BG); bar.pack(side="bottom",fill="x",padx=7); tk.Label(bar,text="Điều khiển tất cả:",bg=BG,font=("Segoe UI",9,"bold")).pack(side="left")
        for t,a in [("Tới nơi nhận",Action.TOI_NOI_NHAN),("Tới chỗ bán",Action.TOI_CHO_BAN),("Tới nơi train",Action.TOI_NOI_TRAIN)]: button(bar,t,lambda aa=a:self.action_all(aa),"gold").pack(side="left",padx=2)
        start_bar(self,lambda:self.action_all(Action.DON_VANG))


class RaoTab(BaseTab):
    def __init__(self,master,app):
        super().__init__(master,app)
        cfg=labelframe(self,"Cấu hình rao tự động"); cfg.pack(fill="x",padx=5,pady=(5,2))
        h=tk.Frame(cfg,bg=BG); h.pack(fill="x",padx=4)
        for t,w in [("Tên",8),("Nội dung rao",24),("Kênh",9),("Lặp (s)",6),("Xóa",4)]: tk.Label(h,text=t,bg=BG,font=("Segoe UI",9,"bold"),width=w).pack(side="left")
        row=tk.Frame(cfg,bg=BG); row.pack(fill="x",padx=4,pady=2); tk.Entry(row,width=8).pack(side="left"); tk.Entry(row,width=24).pack(side="left",padx=2); ttk.Combobox(row,values=["Thế giới","Bang","Đội","Lân cận"],width=8).pack(side="left"); tk.Spinbox(row,from_=1,to=9999,width=5).pack(side="left",padx=2); button(row,"✕",None,"red",width=2).pack(side="left")
        button(cfg,"+ Thêm rao",None,"green").pack(anchor="w",padx=4,pady=(1,5)); lst=labelframe(self,"Danh sách tài khoản"); lst.pack(fill="both",expand=True,padx=5,pady=2); account_table_header(lst,[("Nhân vật",22),("Nội dung rao",25)]); start_bar(self,lambda:self.action_all(Action.RAO))


class ToiUuTab(BaseTab):
    def __init__(self,master,app):
        super().__init__(master,app)
        mon=labelframe(self,"Giám sát CPU/GPU"); mon.pack(fill="x",padx=5,pady=(5,2)); top=tk.Frame(mon,bg=BG); top.pack(fill="x",padx=5); tk.Label(top,text="Theo dõi hiệu năng...",bg=BG,fg=GRAY).pack(side="left"); button(top,"Tách theo dõi",lambda:self.app.set_status("Theo dõi hiệu năng đang chạy độc lập."),"gray").pack(side="right")
        self.cpu_label=tk.Label(mon,text="CPU: 0%",bg=BG,fg="#0066cc",font=("Segoe UI",9,"bold"),anchor="w"); self.cpu_label.pack(fill="x",padx=5); self.canvas=tk.Canvas(mon,height=62,bg=WHITE,bd=1,relief="sunken",highlightthickness=0); self.canvas.pack(fill="x",padx=5,pady=2); self.samples=deque([0.0]*60,maxlen=60)
        tk.Label(mon,text="GPU: N/A (không có nvidia-smi)",bg=BG,fg="#ff3300",font=("Segoe UI",9,"bold"),anchor="w").pack(fill="x",padx=5); tk.Canvas(mon,height=62,bg=WHITE,bd=1,relief="sunken",highlightthickness=0).pack(fill="x",padx=5,pady=(2,5))
        lst=labelframe(self,"Danh sách tài khoản"); lst.pack(fill="both",expand=True,padx=5,pady=2); account_table_header(lst,[("Nhân vật",28),("Giảm cấu hình",20)])
        bar=tk.Frame(self,bg=BG); bar.pack(side="bottom",fill="x",padx=7); tk.Label(bar,text="Điều khiển tất cả:",bg=BG,font=("Segoe UI",9,"bold")).pack(side="left")
        for t in ["Thấp vừa","Cực thấp","Cực đại"]: button(bar,t,lambda tt=t:self.app.set_status(f"Tối ưu: {tt}"),"gray").pack(side="left",padx=2)
        start_bar(self,lambda:self.action_all(Action.TOI_UU)); self.monitor=MonitorService(); self.monitor.start(lambda s:self.after(0,lambda:self.sample(s.cpu)))
    def sample(self,cpu):
        self.samples.append(cpu); self.cpu_label.config(text=f"CPU: {cpu:.0f}%"); self.canvas.delete("all"); w=max(1,self.canvas.winfo_width()); h=max(1,self.canvas.winfo_height()); vals=list(self.samples); pts=[]
        for i,v in enumerate(vals): pts.extend((i*w/max(1,len(vals)-1),h-v*h/100))
        if len(pts)>=4: self.canvas.create_line(*pts,fill="#0066cc",width=1)
        for y in [h//4,h//2,3*h//4]: self.canvas.create_line(0,y,w,y,fill="#dddddd")


class InfoTab(BaseTab):
    def __init__(self,master,app):
        super().__init__(master,app)
        box=labelframe(self,"Thông tin"); box.pack(fill="x",padx=5,pady=5)
        tk.Label(box,text="TLMTool",bg=BG,font=("Segoe UI",14,"bold")).pack(pady=(10,2)); tk.Label(box,text=f"Phiên bản hiện tại: {__version__}",bg=BG).pack(); tk.Label(box,text="Bản quyền FREE vĩnh viễn",fg=GREEN,bg=BG,font=("Segoe UI",9,"bold")).pack(pady=5); button(box,"Kiểm tra cập nhật",lambda:self.app.set_status("Phiên bản hiện tại: 2.1.2"),"blue").pack(pady=(4,10))


class TLMApplication:
    def __init__(self,root:tk.Tk):
        self.root=root; configure_root(root); root.title("TLMTool"); root.geometry("454x1032"); root.minsize(454,720); root.maxsize(454,1400)
        self.store=SettingsStore(); self.backend=TlmBackend(); self.status_var=tk.StringVar(value=""); self.notebook=ttk.Notebook(root); self.notebook.pack(fill="both",expand=True,padx=3,pady=2); self.tabs=[]
        for cls,label in [(StartTab,"▶"),(LoginTab,"Login"),(PartyTab,"Party"),(TrainTab,"Train"),(TrainLsvTab,"Train LSV"),(PhoBanTab,"Phó Bản"),(DailyTab,"Daily"),(DonVangTab,"Dồn"),(RaoTab,"Rao"),(ToiUuTab,"Tối ưu"),(InfoTab,"i")]:
            tab=cls(self.notebook,self); self.notebook.add(tab,text=label); self.tabs.append(tab)
        self.backend.on_status(lambda text:self.root.after(0,lambda:self.set_status(text))); self.root.protocol("WM_DELETE_WINDOW",self.close)
    def set_status(self,text): self.status_var.set(text); log.info(text)
    def close(self):
        for tab in self.tabs:
            if isinstance(tab,LoginTab): tab.save_accounts(); tab.schedule.stop()
            if isinstance(tab,PartyTab): tab.stop()
            if isinstance(tab,TrainTab): tab.stop()
            if isinstance(tab,ToiUuTab): tab.monitor.stop()
        self.store.save(); self.backend.driver.close(); self.root.destroy()


def main():
    logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s %(message)s")
    root=tk.Tk(); TLMApplication(root); root.mainloop()
