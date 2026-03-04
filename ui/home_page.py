import threading
import customtkinter as ctk
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from storage.settings_manager import load_settings, load_alerts, save_alerts
from core.alert_engine import run_alerts
from core.notifier import notify

# Indicator stat keys that are clickable for subplot
INDICATOR_STAT_KEYS = {"CCI": "CCI", "MACD": "MACD", "KDJ K": "KDJ"}


class HomePage(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, corner_radius=0, fg_color="transparent")
        self._app = app
        self._chart_canvas = None
        self._fig = None
        self._selected_ticker = None
        self._current_df = None
        self._active_indicator = None  # currently overlaid indicator name (CCI/MACD/KDJ)
        self._alert_data = {}
        self._build_ui()
        self._load_saved_alerts()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _build_ui(self):
        # ── Top bar ──────────────────────────────────────────────────
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(12, 0))

        self._lbl_header = ctk.CTkLabel(top, text="Stock Tracker", font=ctk.CTkFont(size=20, weight="bold"))
        self._lbl_header.pack(side="left")

        self._lbl_updated = ctk.CTkLabel(top, text="Last updated: —", text_color="gray")
        self._lbl_updated.pack(side="left", padx=20)

        self._btn_update = ctk.CTkButton(top, text="Update", width=110, command=self._on_update)
        self._btn_update.pack(side="right")

        self._lbl_status = ctk.CTkLabel(top, text="", text_color="gray")
        self._lbl_status.pack(side="right", padx=10)

        # ── Middle row: attention list + detail panels ────────────────
        mid = ctk.CTkFrame(self, fg_color="transparent")
        mid.pack(fill="both", expand=True, padx=16, pady=12)

        # Right: attention list — narrower, just fits a ticker symbol
        right_panel = ctk.CTkFrame(mid, width=150)
        right_panel.pack(side="right", fill="y", padx=(8, 0))
        right_panel.pack_propagate(False)

        ctk.CTkLabel(right_panel, text="Attention", font=ctk.CTkFont(weight="bold")).pack(pady=(10, 4), padx=8)
        self._attention_list = ctk.CTkScrollableFrame(right_panel, label_text="")
        self._attention_list.pack(fill="both", expand=True, padx=4, pady=4)

        # Left: detail panels
        left_panel = ctk.CTkFrame(mid, fg_color="transparent")
        left_panel.pack(side="left", fill="both", expand=True)

        # Bottom three panels
        bottom = ctk.CTkFrame(left_panel, fg_color="transparent")
        bottom.pack(fill="both", expand=True)
        bottom.columnconfigure(0, weight=2)   # Reason
        bottom.columnconfigure(1, weight=5)   # Chart (dominant)
        bottom.columnconfigure(2, weight=2)   # Stats (more space now)
        bottom.rowconfigure(0, weight=1)

        # Panel 1 – Reason
        reason_frame = ctk.CTkFrame(bottom)
        reason_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        ctk.CTkLabel(reason_frame, text="Reason", font=ctk.CTkFont(weight="bold")).pack(pady=(10, 4), padx=8, anchor="w")
        self._txt_reason = ctk.CTkTextbox(reason_frame, wrap="word", state="disabled")
        self._txt_reason.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # Panel 2 – Chart
        chart_frame = ctk.CTkFrame(bottom)
        chart_frame.grid(row=0, column=1, sticky="nsew", padx=4)
        ctk.CTkLabel(chart_frame, text="Price Chart", font=ctk.CTkFont(weight="bold")).pack(pady=(10, 4), padx=8, anchor="w")
        self._chart_container = ctk.CTkFrame(chart_frame, fg_color="transparent")
        self._chart_container.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # Panel 3 – Stats
        stats_frame = ctk.CTkFrame(bottom)
        stats_frame.grid(row=0, column=2, sticky="nsew", padx=(4, 0))
        ctk.CTkLabel(stats_frame, text="Stock Stats", font=ctk.CTkFont(weight="bold")).pack(pady=(10, 4), padx=8, anchor="w")
        ctk.CTkLabel(stats_frame, text="Click CCI/MACD/KDJ to plot", text_color="gray",
                     font=ctk.CTkFont(size=10)).pack(padx=8, anchor="w")
        self._stats_inner = ctk.CTkFrame(stats_frame, fg_color="transparent")
        self._stats_inner.pack(fill="both", expand=True, padx=8, pady=(4, 8))

        self._stat_labels = {}
        self._stat_key_btns = {}

        # Non-clickable stats
        for key, display in [("Close", "Close"), ("Change % (1d)", "Change (1d)"), ("Volume", "Volume")]:
            row = ctk.CTkFrame(self._stats_inner, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=f"{display}:", width=80, anchor="w").pack(side="left")
            lbl = ctk.CTkLabel(row, text="—", anchor="w")
            lbl.pack(side="left")
            self._stat_labels[key] = lbl

        # Separator
        ctk.CTkLabel(self._stats_inner, text="─── Indicators (click to plot) ───",
                     text_color="gray", font=ctk.CTkFont(size=10)).pack(pady=(6, 2), anchor="w")

        # Clickable indicator stats
        for stat_key, ind_type in INDICATOR_STAT_KEYS.items():
            row = ctk.CTkFrame(self._stats_inner, fg_color="transparent")
            row.pack(fill="x", pady=2)
            key_btn = ctk.CTkButton(
                row, text=f"{stat_key}:", width=72, anchor="w",
                fg_color="transparent", hover_color=("gray70", "gray35"),
                text_color=("gray30", "gray70"),
                font=ctk.CTkFont(size=12),
                command=lambda k=stat_key, t=ind_type: self._toggle_indicator_plot(k, t)
            )
            key_btn.pack(side="left")
            lbl = ctk.CTkLabel(row, text="—", anchor="w")
            lbl.pack(side="left")
            self._stat_labels[stat_key] = lbl
            self._stat_key_btns[stat_key] = key_btn

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------
    def on_show(self):
        self._load_saved_alerts()

    def _load_saved_alerts(self):
        data = load_alerts()
        self._render_alerts(data)

    def _render_alerts(self, data: dict):
        for w in self._attention_list.winfo_children():
            w.destroy()

        alerts = data.get("alerts", {})
        ts = data.get("last_updated", "")
        if ts:
            self._lbl_updated.configure(text=f"Last updated: {ts}")

        attention_tickers = [t for t, a in alerts.items() if a]
        if not attention_tickers:
            ctk.CTkLabel(self._attention_list, text="No alerts", text_color="gray").pack(pady=8)
        else:
            for ticker in attention_tickers:
                btn = ctk.CTkButton(
                    self._attention_list, text=ticker, anchor="w",
                    fg_color="transparent", hover_color=("gray70", "gray40"),
                    command=lambda t=ticker, d=data: self._select_ticker(t, d)
                )
                btn.pack(fill="x", pady=2)

        self._alert_data = data

    def _select_ticker(self, ticker: str, data: dict):
        self._selected_ticker = ticker
        self._active_indicator = None
        self._reset_indicator_btn_highlights()

        alerts = data.get("alerts", {}).get(ticker, [])
        stats = data.get("stats", {}).get(ticker, {})

        self._lbl_header.configure(text=ticker)

        # Reason text
        self._txt_reason.configure(state="normal")
        self._txt_reason.delete("1.0", "end")
        if alerts:
            for a in alerts:
                signal = a.get("signal", "").upper()
                reason = a.get("reason", "")
                self._txt_reason.insert("end", f"[{signal}] {reason}\n\n")
        else:
            self._txt_reason.insert("end", "No alerts for this stock.")
        self._txt_reason.configure(state="disabled")

        # Stats
        def fmt(val, suffix=""):
            return f"{val}{suffix}" if val is not None else "—"

        self._stat_labels["Close"].configure(text=fmt(stats.get("close")))
        change = stats.get("change_pct")
        color = "green" if (change or 0) >= 0 else "red"
        self._stat_labels["Change % (1d)"].configure(text=fmt(change, "%"), text_color=color)
        vol = stats.get("volume")
        self._stat_labels["Volume"].configure(text=f"{vol:,}" if vol else "—")
        self._stat_labels["CCI"].configure(text=fmt(stats.get("cci")))
        self._stat_labels["MACD"].configure(text=fmt(stats.get("macd")))
        self._stat_labels["KDJ K"].configure(text=fmt(stats.get("kdj_k")))

        # Fetch + draw chart in background thread
        threading.Thread(target=self._fetch_and_draw, args=(ticker,), daemon=True).start()

    def _fetch_and_draw(self, ticker: str):
        try:
            from core.data_fetcher import fetch_stock_data
            df = fetch_stock_data(ticker, period="3mo")
            self._current_df = df
            self.after(0, lambda: self._render_chart(df, ticker, self._active_indicator))
        except Exception as e:
            self.after(0, lambda: self._clear_chart(str(e)))

    # ------------------------------------------------------------------
    # Indicator subplot toggle
    # ------------------------------------------------------------------
    def _toggle_indicator_plot(self, stat_key: str, ind_type: str):
        if self._current_df is None or self._selected_ticker is None:
            return
        if self._active_indicator == ind_type:
            # Deselect — back to price-only
            self._active_indicator = None
            self._reset_indicator_btn_highlights()
        else:
            self._active_indicator = ind_type
            self._reset_indicator_btn_highlights()
            self._stat_key_btns[stat_key].configure(
                text_color=("#1a7fd4", "#4a9eff"),
                fg_color=("gray80", "gray25")
            )
        self._render_chart(self._current_df, self._selected_ticker, self._active_indicator)

    def _reset_indicator_btn_highlights(self):
        for btn in self._stat_key_btns.values():
            btn.configure(text_color=("gray30", "gray70"), fg_color="transparent")

    # ------------------------------------------------------------------
    # Chart rendering
    # ------------------------------------------------------------------
    def _render_chart(self, df, ticker: str, indicator: str = None):
        for w in self._chart_container.winfo_children():
            w.destroy()
        if self._fig:
            plt.close(self._fig)

        bg = "#2b2b2b"
        fg = "white"

        if indicator:
            self._fig, (ax_price, ax_ind) = plt.subplots(
                2, 1, figsize=(5, 4), facecolor=bg,
                gridspec_kw={"height_ratios": [3, 2]}, sharex=False
            )
        else:
            self._fig, ax_price = plt.subplots(figsize=(5, 3), facecolor=bg)
            ax_ind = None

        # ── Price subplot ──────────────────────────────────────────
        ax_price.set_facecolor(bg)
        ax_price.plot(df.index, df["Close"], color="#4a9eff", linewidth=1.5)
        ax_price.set_title(ticker, color=fg, fontsize=10)
        ax_price.tick_params(colors=fg, labelsize=7)
        ax_price.spines[:].set_color("gray")
        if ax_ind is None:
            ax_price.xaxis.set_major_locator(matplotlib.dates.AutoDateLocator())
            ax_price.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%m/%d"))
            plt.setp(ax_price.get_xticklabels(), rotation=30, ha="right")
        else:
            plt.setp(ax_price.get_xticklabels(), visible=False)

        # ── Indicator subplot ──────────────────────────────────────
        if ax_ind is not None:
            ax_ind.set_facecolor(bg)
            ax_ind.tick_params(colors=fg, labelsize=7)
            ax_ind.spines[:].set_color("gray")
            ax_ind.xaxis.set_major_locator(matplotlib.dates.AutoDateLocator())
            ax_ind.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%m/%d"))
            plt.setp(ax_ind.get_xticklabels(), rotation=30, ha="right")

            settings = load_settings()
            ind_cfg = next((i for i in settings.get("indicators", []) if i["type"] == indicator), {})
            self._plot_indicator(ax_ind, df, indicator, ind_cfg, fg, bg)

        self._fig.tight_layout(pad=0.5)
        canvas = FigureCanvasTkAgg(self._fig, master=self._chart_container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        self._chart_canvas = canvas

    def _plot_indicator(self, ax, df, indicator: str, ind_cfg: dict, fg: str, bg: str):
        from core.indicators import calc_cci, calc_macd, calc_kdj

        if indicator == "CCI":
            period = ind_cfg.get("period", 20)
            cci = calc_cci(df, period).dropna()
            ax.plot(cci.index, cci.values, color="#ff9f40", linewidth=1.2)
            buy_th = ind_cfg.get("buy_threshold", -100)
            sell_th = ind_cfg.get("sell_threshold", 100)
            ax.axhline(buy_th, color="lime", linestyle="--", linewidth=0.8, alpha=0.8)
            ax.axhline(sell_th, color="tomato", linestyle="--", linewidth=0.8, alpha=0.8)
            ax.axhline(0, color="gray", linewidth=0.5, alpha=0.5)
            ax.set_ylabel("CCI", color=fg, fontsize=7)

        elif indicator == "MACD":
            fast = ind_cfg.get("fast", 12)
            slow = ind_cfg.get("slow", 26)
            signal = ind_cfg.get("signal", 9)
            result = calc_macd(df, fast, slow, signal)
            macd_s = result["macd"].dropna()
            sig_s = result["signal"].dropna()
            hist_s = result["histogram"].dropna()
            idx = macd_s.index.intersection(sig_s.index).intersection(hist_s.index)
            ax.plot(macd_s[idx].index, macd_s[idx].values, color="#4a9eff", linewidth=1.2, label="MACD")
            ax.plot(sig_s[idx].index, sig_s[idx].values, color="#ff6b6b", linewidth=1.2, label="Signal")
            pos = hist_s[idx][hist_s[idx] >= 0]
            neg = hist_s[idx][hist_s[idx] < 0]
            if not pos.empty:
                ax.bar(pos.index, pos.values, color="lime", alpha=0.45, width=0.8)
            if not neg.empty:
                ax.bar(neg.index, neg.values, color="tomato", alpha=0.45, width=0.8)
            buy_th = ind_cfg.get("buy_threshold")
            sell_th = ind_cfg.get("sell_threshold")
            if buy_th is not None and buy_th != 0:
                ax.axhline(buy_th, color="lime", linestyle="--", linewidth=0.8, alpha=0.8)
            if sell_th is not None and sell_th != 0:
                ax.axhline(sell_th, color="tomato", linestyle="--", linewidth=0.8, alpha=0.8)
            ax.axhline(0, color="gray", linewidth=0.5, alpha=0.5)
            ax.set_ylabel("MACD", color=fg, fontsize=7)
            ax.legend(fontsize=6, facecolor=bg, labelcolor=fg, loc="upper left")

        elif indicator == "KDJ":
            period = ind_cfg.get("period", 9)
            k_smooth = ind_cfg.get("k_smooth", 3)
            d_smooth = ind_cfg.get("d_smooth", 3)
            result = calc_kdj(df, period, k_smooth, d_smooth)
            K = result["K"].dropna()
            D = result["D"].dropna()
            J = result["J"].dropna()
            ax.plot(K.index, K.values, color="#4a9eff", linewidth=1.2, label="K")
            ax.plot(D.index, D.values, color="#ff9f40", linewidth=1.2, label="D")
            ax.plot(J.index, J.values, color="#ff6b6b", linewidth=1.2, label="J")
            buy_th = ind_cfg.get("buy_threshold", 20)
            sell_th = ind_cfg.get("sell_threshold", 80)
            ax.axhline(buy_th, color="lime", linestyle="--", linewidth=0.8, alpha=0.8)
            ax.axhline(sell_th, color="tomato", linestyle="--", linewidth=0.8, alpha=0.8)
            ax.set_ylabel("KDJ", color=fg, fontsize=7)
            ax.legend(fontsize=6, facecolor=bg, labelcolor=fg, loc="upper left")

    def _clear_chart(self, msg=""):
        for w in self._chart_container.winfo_children():
            w.destroy()
        ctk.CTkLabel(self._chart_container, text=msg or "No chart", text_color="gray").pack(expand=True)

    # ------------------------------------------------------------------
    # Update button
    # ------------------------------------------------------------------
    def _on_update(self):
        self._btn_update.configure(state="disabled", text="Updating...")
        self._lbl_status.configure(text="Fetching data...")
        threading.Thread(target=self._run_update, daemon=True).start()

    def _run_update(self):
        try:
            settings = load_settings()
            stocks = settings.get("stocks", [])
            indicators = settings.get("indicators", [])

            if not stocks:
                self.after(0, lambda: self._finish_update(None, "No stocks configured."))
                return

            def progress(ticker, i, total):
                self.after(0, lambda: self._lbl_status.configure(
                    text=f"Fetching {ticker} ({i+1}/{total})..."))

            result = run_alerts(stocks, indicators, on_progress=progress)
            save_alerts(result)

            alert_tickers = [t for t, a in result["alerts"].items() if a]
            if alert_tickers:
                msg = "Alerts: " + ", ".join(alert_tickers)
                notify("Stock Tracker", msg)

            self.after(0, lambda: self._finish_update(result, "Done."))
        except Exception as e:
            self.after(0, lambda: self._finish_update(None, f"Error: {e}"))

    def _finish_update(self, result, status_msg):
        self._btn_update.configure(state="normal", text="Update")
        self._lbl_status.configure(text=status_msg)
        if result:
            saved = load_alerts()
            self._render_alerts(saved)
