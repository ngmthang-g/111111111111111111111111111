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
        self.mode = tk.StringVar(value="Auto")
        tk.Radiobutton(mode, text="Auto", value="Auto", variable=self.mode, bg=BG).pack(side="left", padx=5)
        tk.Radiobutton(mode, text="Xếp lưới", value="Xếp lưới", variable=self.mode, bg=BG).pack(side="left", padx=18)

        quick = labelframe(self, "Điều khiển nhanh"); quick.pack(fill="x", padx=5, pady=2)
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

    def refresh(self):
        n=len(self.backend.windows()); self.preview.config(text=f"Đã tìm thấy {n} cửa sổ game." if n else "Không tìm thấy cửa sổ game, hãy mở game trước.")
    def hide_all(self):
        for g in self.backend.windows(): self.backend.winapi.show(g.hwnd,False)
        self.refresh()
    def detach(self):
        for g in self.backend.windows(): self.backend.winapi.show(g.hwnd,True)
    def arrange(self): self.backend.winapi.arrange_grid(self.backend.windows(),self.columns.get())
    def diagonal(self): self.backend.winapi.arrange_grid(self.backend.windows(),self.columns.get(),diagonal=True)
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
        mapping = {
            "Party": Action.PARTY,
            "Train": Action.TRAIN,
            "Train LSV": Action.TRAIN_LSV,
            "Dồn vàng": Action.DON_VANG,
        }
        action = mapping.get(mode)
        if action is not None:
            self.action_all(action)

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
    def __init__(self,master,app):
        super().__init__(master,app)
        post=labelframe(self,"Sau khi party"); post.pack(fill="x",padx=5,pady=(5,2))
        row=tk.Frame(post,bg=BG); row.pack(fill="x",padx=4,pady=3); tk.Label(row,text="Sau khi party:",bg=BG,font=("Segoe UI",9,"bold")).pack(side="left")
        self.after=tk.StringVar(value="Chờ")
        for x in ["Chờ","Train","Train LSV","Dồn vàng","Phó bản"]: tk.Radiobutton(row,text=x,value=x,variable=self.after,bg=BG).pack(side="left",padx=3)
        ready=labelframe(self,"Cấu hình tổ đội"); ready.pack(fill="x",padx=5,pady=2); tk.Label(ready,text="Danh sách acc sẵn sàng:",bg=BG,font=("Segoe UI",9,"bold"),anchor="w").pack(fill="x",padx=4,pady=4)
        groups=labelframe(self,"Cấu hình nhóm"); groups.pack(fill="x",padx=5,pady=2); self.holder=tk.Frame(groups,bg=BG); self.holder.pack(fill="x",padx=4); self.groups=[]
        self.add_group(); self.add_group(); button(groups,"+ Thêm nhóm",self.add_group,"green").pack(anchor="w",padx=4,pady=6); start_bar(self,lambda:self.action_all(Action.PARTY))
    def add_group(self):
        n=len(self.groups)+1; f=tk.LabelFrame(self.holder,text=f"Nhóm {n}",bg=BG,font=("Segoe UI",9,"bold")); f.pack(fill="x",pady=2)
        top=tk.Frame(f,bg=BG); top.pack(fill="x"); tk.Label(top,text="Trưởng nhóm:",bg=BG,font=("Segoe UI",9,"bold")).pack(side="left",padx=4); ttk.Combobox(top,width=17).pack(side="left")
        button(top,"Rời nhóm",lambda:self.action_all(Action.PARTY),"blue").pack(side="right",padx=2); button(top,"✕ Xóa nhóm",lambda:self.delete_group(f),"red").pack(side="right",padx=2)
        grid=tk.Frame(f,bg=BG); grid.pack(fill="x",padx=4,pady=2)
        for r in range(2):
            for c in range(3): ttk.Combobox(grid,width=15).grid(row=r,column=c,padx=2,pady=2)
        button(f,f"▾ Tạo nhóm {n}",lambda:self.action_all(Action.PARTY),"green").pack(fill="x",padx=4,pady=(2,5)); self.groups.append(f)
    def delete_group(self,f):
        if len(self.groups)>1: f.destroy(); self.groups.remove(f)


class TrainTab(BaseTab):
    def __init__(self,master,app):
        super().__init__(master,app)
        city=labelframe(self,"Cấu hình Về thành"); city.pack(fill="x",padx=5,pady=(5,2))
        r=tk.Frame(city,bg=BG); r.pack(fill="x",padx=4,pady=3); tk.Label(r,text="Điều kiện về thành:",bg=BG,font=("Segoe UI",9,"bold")).pack(side="left")
        v=tk.StringVar(value="period")
        for t,x in [("Không về","none"),("Khi đầy túi","bag"),("Theo chu kỳ (phút):","period")]: tk.Radiobutton(r,text=t,value=x,variable=v,bg=BG).pack(side="left",padx=2)
        tk.Spinbox(r,from_=1,to=999,width=4).pack(side="left"); button(r,"Hiện cấu hình",None,"gray").pack(side="right")
        cfg=labelframe(self,"Cấu hình Train"); cfg.pack(fill="x",padx=5,pady=2); tk.Label(cfg,text="Trong khi train:",bg=BG,font=("Segoe UI",9,"bold")).pack(anchor="w",padx=5)
        checks(cfg,["Quay lại train khi chết","Tự kết nối lại khi mất mạng","Nhặt đồ không dùng hồ lô (cần khôn hồ)","Trị liệu sau khi chết"])
        h=tk.Frame(cfg,bg=BG); h.pack(fill="x",padx=5); tk.Label(h,text="Tọa độ trị liệu:",bg=BG).pack(side="left"); ttk.Combobox(h,values=["Trị liệu Tô Châu"],width=20).pack(side="left")
        f=tk.Frame(cfg,bg=BG); f.pack(fill="x",padx=5); tk.Label(f,text="Lọc đồ giữ lại:",bg=BG,font=("Segoe UI",9,"bold")).pack(side="left"); q=tk.StringVar(value="Tất cả")
        for x in ["Không","Chỉ vũ khí","Tất cả"]: tk.Radiobutton(f,text=x,value=x,variable=q,bg=BG).pack(side="left")
        tk.Label(cfg,text="Dùng thú cưỡi gần được (2x, 4x...):",bg=BG,font=("Segoe UI",9,"bold")).pack(anchor="w",padx=5); button(cfg,"+ Thêm",None,"green").pack(anchor="w",padx=5,pady=3)
        coord=labelframe(self,"Cấu hình tọa độ lưu sẵn"); coord.pack(fill="x",padx=5,pady=2); button(coord,"+ Thêm tọa độ",None,"green").pack(side="left",padx=5,pady=5); button(coord,"Ẩn danh sách tọa độ",None,"gray").pack(side="right",padx=5,pady=5)
        lst=labelframe(self,"Danh sách tài khoản"); lst.pack(fill="both",expand=True,padx=5,pady=2); account_table_header(lst,[("Nhân vật",18),("Tọa độ bán",16),("Tọa độ Train",16)])
        bar=tk.Frame(self,bg=BG); bar.pack(side="bottom",fill="x",padx=7); tk.Label(bar,text="Điều khiển tất cả:",bg=BG,font=("Segoe UI",9,"bold")).pack(side="left")
        for t,a in [("Tới bán đồ",Action.TOI_CHO_BAN),("Bán đồ",Action.BAN_DO),("Tới bãi train",Action.TOI_CHO_TRAIN),("Đánh",Action.DANH)]: button(bar,t,lambda aa=a:self.action_all(aa),"blue").pack(side="left",padx=2)
        start_bar(self,lambda:self.action_all(Action.TRAIN))


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
            if isinstance(tab,ToiUuTab): tab.monitor.stop()
        self.store.save(); self.backend.driver.close(); self.root.destroy()


def main():
    logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s %(message)s")
    root=tk.Tk(); TLMApplication(root); root.mainloop()
