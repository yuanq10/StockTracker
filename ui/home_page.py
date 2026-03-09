import threading
import customtkinter as ctk
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from storage.settings_manager import load_settings, load_alerts, save_alerts
from core.alert_engine import run_alerts
import ui.theme as T

INDICATOR_STAT_KEYS = {"CCI": "CCI", "MACD": "MACD", "KDJ K": "KDJ"}


class HomePage(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, corner_radius=0, fg_color="transparent")
        self._app = app
        self._chart_canvas = None
        self._fig = None
        self._selected_ticker = None
        self._current_df = None
        self._active_indicator = None
        self._alert_data = {}
        self._build_ui()
        self._load_saved_alerts()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _build_ui(self):
        # ── Top bar ──────────────────────────────────────────────────
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(16, 0))

        self._lbl_header = ctk.CTkLabel(
            top, text="Dashboard",
            font=ctk.CTkFont(size=22, weight="bold"), text_color=T.TEXT
        )
        self._lbl_header.pack(side="left")

        self._lbl_updated = ctk.CTkLabel(
            top, text="", font=ctk.CTkFont(size=11), text_color=T.TEXT_MUTED
        )
        self._lbl_updated.pack(side="left", padx=16)

        self._btn_update = ctk.CTkButton(
            top, text="Update", width=110, height=36, corner_radius=18,
            fg_color=T.ACCENT, hover_color="#79b8ff", text_color="#000000",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._on_update
        )
        self._btn_update.pack(side="right")

        self._lbl_status = ctk.CTkLabel(
            top, text="", font=ctk.CTkFont(size=11), text_color=T.TEXT_MUTED
        )
        self._lbl_status.pack(side="right", padx=12)

        # ── Middle row ───────────────────────────────────────────────
        mid = ctk.CTkFrame(self, fg_color="transparent")
        mid.pack(fill="both", expand=True, padx=20, pady=16)

        # LEFT: attention list
        attn_panel = ctk.CTkFrame(
            mid, width=170, fg_color=T.CARD,
            corner_radius=12, border_width=1, border_color=T.BORDER
        )
        attn_panel.pack(side="left", fill="y", padx=(0, 10))
        attn_panel.pack_propagate(False)

        ctk.CTkLabel(
            attn_panel, text="Attention",
            font=ctk.CTkFont(size=18, weight="bold"), text_color=T.TEXT
        ).pack(pady=(10, 4), padx=12, anchor="w")

        self._attention_list = ctk.CTkScrollableFrame(
            attn_panel, fg_color="transparent", scrollbar_button_color=T.BORDER
        )
        self._attention_list.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        # RIGHT: detail panels
        detail_area = ctk.CTkFrame(mid, fg_color="transparent")
        detail_area.pack(side="left", fill="both", expand=True)

        bottom = ctk.CTkFrame(detail_area, fg_color="transparent")
        bottom.pack(fill="both", expand=True)
        bottom.columnconfigure(0, weight=2)   # Reason
        bottom.columnconfigure(1, weight=8)   # Chart (dominant)
        bottom.columnconfigure(2, weight=0, minsize=60)  # Stats fixed ~60px
        bottom.rowconfigure(0, weight=1)

        # Panel 1 – Reason
        reason_frame = ctk.CTkFrame(
            bottom, fg_color=T.CARD, corner_radius=12,
            border_width=1, border_color=T.BORDER
        )
        reason_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        ctk.CTkLabel(
            reason_frame, text="Signal Reasons",
            font=ctk.CTkFont(size=18, weight="bold"), text_color=T.TEXT
        ).pack(pady=(14, 8), padx=12, anchor="w")

        self._txt_reason = ctk.CTkTextbox(
            reason_frame, wrap="word", state="disabled",
            fg_color=T.BG, text_color=T.TEXT,
            font=ctk.CTkFont(size=11), corner_radius=8,
            border_width=0, scrollbar_button_color=T.BORDER
        )
        self._txt_reason.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Configure colour tags for signal types
        try:
            tb = self._txt_reason._textbox
            tb.tag_config("buy",   foreground=T.SUCCESS)
            tb.tag_config("sell",  foreground=T.DANGER)
            tb.tag_config("alert", foreground=T.WARNING)
            tb.tag_config("error", foreground=T.DANGER)
            tb.tag_config("body",  foreground=T.TEXT_MUTED)
        except Exception:
            pass

        # Panel 2 – Chart
        chart_frame = ctk.CTkFrame(
            bottom, fg_color=T.CARD, corner_radius=12,
            border_width=1, border_color=T.BORDER
        )
        chart_frame.grid(row=0, column=1, sticky="nsew", padx=6)

        ctk.CTkLabel(
            chart_frame, text="Price Chart",
            font=ctk.CTkFont(size=18, weight="bold"), text_color=T.TEXT
        ).pack(pady=(14, 4), padx=12, anchor="w")

        self._chart_container = ctk.CTkFrame(chart_frame, fg_color="transparent")
        self._chart_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Panel 3 – Stats
        stats_frame = ctk.CTkFrame(
            bottom, fg_color=T.CARD, corner_radius=12,
            border_width=1, border_color=T.BORDER
        )
        stats_frame.grid(row=0, column=2, sticky="nsew", padx=(6, 0))

        ctk.CTkLabel(
            stats_frame, text="Stats",
            font=ctk.CTkFont(size=18, weight="bold"), text_color=T.TEXT
        ).pack(pady=(14, 8), padx=12, anchor="w")

        self._stats_inner = ctk.CTkScrollableFrame(
            stats_frame, fg_color="transparent", scrollbar_button_color=T.BORDER
        )
        self._stats_inner.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self._stat_labels = {}
        self._stat_key_btns = {}

        for key, display in [
            ("Close", "Close Price"),
            ("Change % (1d)", "Change (1d)"),
            ("Volume", "Volume"),
        ]:
            self._stat_labels[key] = self._make_metric_card(self._stats_inner, display)

        ctk.CTkLabel(
            self._stats_inner, text="INDICATORS",
            font=ctk.CTkFont(size=9, weight="bold"), text_color=T.TEXT_DIM
        ).pack(anchor="w", padx=4, pady=(10, 2))

        for stat_key, ind_type in INDICATOR_STAT_KEYS.items():
            self._stat_labels[stat_key] = self._make_metric_card(
                self._stats_inner, stat_key,
                clickable=True,
                click_cmd=lambda k=stat_key, t=ind_type: self._toggle_indicator_plot(k, t),
                btn_store_key=stat_key,
            )

    def _make_metric_card(self, parent, label, clickable=False, click_cmd=None, btn_store_key=None):
        card = ctk.CTkFrame(parent, fg_color=T.BG, corner_radius=6,
                            border_width=1, border_color=T.BORDER)
        card.pack(fill="x", pady=2)

        if clickable:
            header_btn = ctk.CTkButton(
                card, text=label, anchor="w", height=18,
                fg_color="transparent", hover_color=T.CARD,
                text_color=T.TEXT_MUTED, font=ctk.CTkFont(size=9),
                command=click_cmd
            )
            header_btn.pack(anchor="w", padx=5, pady=(4, 0))
            if btn_store_key is not None:
                self._stat_key_btns[btn_store_key] = header_btn
        else:
            ctk.CTkLabel(
                card, text=label, font=ctk.CTkFont(size=9),
                text_color=T.TEXT_MUTED, anchor="w"
            ).pack(anchor="w", padx=5, pady=(4, 0))

        val_lbl = ctk.CTkLabel(
            card, text="—",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=T.TEXT, anchor="w"
        )
        val_lbl.pack(anchor="w", padx=5, pady=(0, 4))
        return val_lbl

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
            self._lbl_updated.configure(text=f"Updated {ts}")

        attention_tickers = [t for t, a in alerts.items() if a]
        if not attention_tickers:
            ctk.CTkLabel(
                self._attention_list, text="No alerts",
                font=ctk.CTkFont(size=11), text_color=T.TEXT_MUTED
            ).pack(pady=10)
        else:
            for ticker in attention_tickers:
                ticker_alerts = alerts[ticker]
                signals = {a.get("signal") for a in ticker_alerts}
                if "buy" in signals:
                    bar_color = T.SUCCESS
                elif "sell" in signals:
                    bar_color = T.DANGER
                else:
                    bar_color = T.WARNING

                row = ctk.CTkFrame(
                    self._attention_list, fg_color="transparent",
                    height=36, cursor="hand2"
                )
                row.pack(fill="x", pady=3)
                row.pack_propagate(False)

                # Accent bar sits outside the card — no corner mismatch
                ctk.CTkFrame(row, width=3, corner_radius=2,
                             fg_color=bar_color).pack(
                    side="left", fill="y", padx=(0, 5)
                )

                item = ctk.CTkFrame(
                    row, fg_color=T.BG,
                    corner_radius=8, border_width=1, border_color=T.BORDER,
                    cursor="hand2"
                )
                item.pack(side="left", fill="both", expand=True)

                lbl = ctk.CTkLabel(
                    item, text=ticker, anchor="w",
                    text_color=T.TEXT, font=ctk.CTkFont(size=16, weight="bold"),
                    cursor="hand2"
                )
                lbl.pack(fill="both", expand=True, padx=8)

                cmd = lambda e, t=ticker, d=data: self._select_ticker(t, d)
                hover_in  = lambda e, i=item: i.configure(fg_color=T.CARD)
                hover_out = lambda e, i=item: i.configure(fg_color=T.BG)
                for w in (row, item, lbl):
                    w.bind("<Button-1>", cmd)
                for w in (item, lbl):
                    w.bind("<Enter>", hover_in)
                    w.bind("<Leave>", hover_out)

        self._alert_data = data

    def _select_ticker(self, ticker: str, data: dict):
        self._selected_ticker = ticker
        self._active_indicator = None
        self._reset_indicator_btn_highlights()

        alerts = data.get("alerts", {}).get(ticker, [])
        stats = data.get("stats", {}).get(ticker, {})

        self._lbl_header.configure(text=ticker)

        # Reason text with coloured signal labels
        self._txt_reason.configure(state="normal")
        self._txt_reason.delete("1.0", "end")
        tb = getattr(self._txt_reason, "_textbox", None)
        if alerts:
            for a in alerts:
                signal = a.get("signal", "").lower()
                reason = a.get("reason", "")
                tag = signal if signal in ("buy", "sell", "alert", "error") else "body"
                if tb:
                    tb.insert("end", f"[{signal.upper()}] ", tag)
                    tb.insert("end", f"{reason}\n\n", "body")
                else:
                    self._txt_reason.insert("end", f"[{signal.upper()}] {reason}\n\n")
        else:
            self._txt_reason.insert("end", "No alerts for this stock.")
        self._txt_reason.configure(state="disabled")

        # Stats
        def fmt(val, suffix=""):
            return f"{val}{suffix}" if val is not None else "—"

        self._stat_labels["Close"].configure(text=fmt(stats.get("close")))
        change = stats.get("change_pct")
        color = T.SUCCESS if (change or 0) >= 0 else T.DANGER
        self._stat_labels["Change % (1d)"].configure(text=fmt(change, "%"), text_color=color)
        vol = stats.get("volume")
        self._stat_labels["Volume"].configure(text=f"{vol:,}" if vol else "—")
        self._stat_labels["CCI"].configure(text=fmt(stats.get("cci")))
        self._stat_labels["MACD"].configure(text=fmt(stats.get("macd")))
        self._stat_labels["KDJ K"].configure(text=fmt(stats.get("kdj_k")))

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
            self._active_indicator = None
            self._reset_indicator_btn_highlights()
        else:
            self._active_indicator = ind_type
            self._reset_indicator_btn_highlights()
            self._stat_key_btns[stat_key].configure(
                text_color=T.ACCENT, fg_color=T.CARD
            )
        self._render_chart(self._current_df, self._selected_ticker, self._active_indicator)

    def _reset_indicator_btn_highlights(self):
        for btn in self._stat_key_btns.values():
            btn.configure(text_color=T.TEXT_MUTED, fg_color="transparent")

    # ------------------------------------------------------------------
    # Chart rendering
    # ------------------------------------------------------------------
    def _render_chart(self, df, ticker: str, indicator: str = None):
        for w in self._chart_container.winfo_children():
            w.destroy()
        if self._fig:
            plt.close(self._fig)

        bg = T.CHART_BG
        fg = T.TEXT

        if indicator:
            self._fig, (ax_price, ax_ind) = plt.subplots(
                2, 1, figsize=(5, 4), facecolor=bg,
                gridspec_kw={"height_ratios": [3, 2]}, sharex=False
            )
        else:
            self._fig, ax_price = plt.subplots(figsize=(5, 3), facecolor=bg)
            ax_ind = None

        self._style_ax(ax_price, bg)
        ax_price.plot(df.index, df["Close"], color=T.CHART_PRICE, linewidth=1.8)
        ax_price.fill_between(df.index, df["Close"], alpha=0.08, color=T.CHART_PRICE)
        ax_price.set_title(ticker, color=fg, fontsize=10, pad=8)

        if ax_ind is None:
            ax_price.xaxis.set_major_locator(matplotlib.dates.AutoDateLocator())
            ax_price.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%m/%d"))
            plt.setp(ax_price.get_xticklabels(), rotation=30, ha="right")
        else:
            plt.setp(ax_price.get_xticklabels(), visible=False)

        if ax_ind is not None:
            self._style_ax(ax_ind, bg)
            ax_ind.xaxis.set_major_locator(matplotlib.dates.AutoDateLocator())
            ax_ind.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%m/%d"))
            plt.setp(ax_ind.get_xticklabels(), rotation=30, ha="right")

            settings = load_settings()
            ind_cfg = next(
                (i for i in settings.get("indicators", []) if i["type"] == indicator), {}
            )
            self._plot_indicator(ax_ind, df, indicator, ind_cfg, fg, bg)

        self._fig.tight_layout(pad=0.8)
        canvas = FigureCanvasTkAgg(self._fig, master=self._chart_container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        self._chart_canvas = canvas

    def _style_ax(self, ax, bg: str):
        ax.set_facecolor(bg)
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.tick_params(colors=T.TEXT_MUTED, labelsize=7)
        ax.yaxis.tick_right()
        ax.grid(True, color=T.CHART_GRID, linewidth=0.5, alpha=0.8, axis="y")

    def _plot_indicator(self, ax, df, indicator: str, ind_cfg: dict, fg: str, bg: str):
        from core.indicators import calc_cci, calc_macd, calc_kdj

        if indicator == "CCI":
            period = ind_cfg.get("period", 20)
            cci = calc_cci(df, period).dropna()
            ax.plot(cci.index, cci.values, color=T.CHART_CCI, linewidth=1.4)
            buy_th = ind_cfg.get("buy_threshold", -100)
            sell_th = ind_cfg.get("sell_threshold", 100)
            ax.axhline(buy_th,  color=T.SUCCESS, linestyle="--", linewidth=0.8, alpha=0.7)
            ax.axhline(sell_th, color=T.DANGER,  linestyle="--", linewidth=0.8, alpha=0.7)
            ax.axhline(0, color=T.TEXT_DIM, linewidth=0.5, alpha=0.6)
            ax.fill_between(cci.index, cci.values, buy_th,
                            where=(cci.values < buy_th), alpha=0.2, color=T.SUCCESS, interpolate=True)
            ax.fill_between(cci.index, cci.values, sell_th,
                            where=(cci.values > sell_th), alpha=0.2, color=T.DANGER, interpolate=True)
            ax.set_ylabel("CCI", color=T.TEXT_MUTED, fontsize=7)

        elif indicator == "MACD":
            fast = ind_cfg.get("fast", 12)
            slow = ind_cfg.get("slow", 26)
            signal = ind_cfg.get("signal", 9)
            result = calc_macd(df, fast, slow, signal)
            macd_s = result["macd"].dropna()
            sig_s  = result["signal"].dropna()
            hist_s = result["histogram"].dropna()
            idx = macd_s.index.intersection(sig_s.index).intersection(hist_s.index)
            ax.plot(macd_s[idx].index, macd_s[idx].values, color=T.CHART_MACD_LINE, linewidth=1.2, label="MACD")
            ax.plot(sig_s[idx].index,  sig_s[idx].values,  color=T.CHART_SIG_LINE,  linewidth=1.2, label="Signal")
            pos = hist_s[idx][hist_s[idx] >= 0]
            neg = hist_s[idx][hist_s[idx] <  0]
            if not pos.empty:
                ax.bar(pos.index, pos.values, color=T.CHART_HIST_POS, alpha=0.5, width=0.8)
            if not neg.empty:
                ax.bar(neg.index, neg.values, color=T.CHART_HIST_NEG, alpha=0.5, width=0.8)
            buy_th  = ind_cfg.get("buy_threshold")
            sell_th = ind_cfg.get("sell_threshold")
            if buy_th  is not None and buy_th  != 0:
                ax.axhline(buy_th,  color=T.SUCCESS, linestyle="--", linewidth=0.8, alpha=0.7)
            if sell_th is not None and sell_th != 0:
                ax.axhline(sell_th, color=T.DANGER,  linestyle="--", linewidth=0.8, alpha=0.7)
            ax.axhline(0, color=T.TEXT_DIM, linewidth=0.5, alpha=0.6)
            ax.set_ylabel("MACD", color=T.TEXT_MUTED, fontsize=7)
            ax.legend(fontsize=6, facecolor=T.CARD, labelcolor=T.TEXT_MUTED,
                      loc="upper left", framealpha=0.8, edgecolor=T.BORDER)

        elif indicator == "KDJ":
            period   = ind_cfg.get("period", 9)
            k_smooth = ind_cfg.get("k_smooth", 3)
            d_smooth = ind_cfg.get("d_smooth", 3)
            result = calc_kdj(df, period, k_smooth, d_smooth)
            K = result["K"].dropna()
            D = result["D"].dropna()
            J = result["J"].dropna()
            ax.plot(K.index, K.values, color=T.CHART_K, linewidth=1.2, label="K")
            ax.plot(D.index, D.values, color=T.CHART_D, linewidth=1.2, label="D")
            ax.plot(J.index, J.values, color=T.CHART_J, linewidth=1.2, label="J")
            buy_th  = ind_cfg.get("buy_threshold", 20)
            sell_th = ind_cfg.get("sell_threshold", 80)
            ax.axhline(buy_th,  color=T.SUCCESS, linestyle="--", linewidth=0.8, alpha=0.7)
            ax.axhline(sell_th, color=T.DANGER,  linestyle="--", linewidth=0.8, alpha=0.7)
            ax.set_ylabel("KDJ", color=T.TEXT_MUTED, fontsize=7)
            ax.legend(fontsize=6, facecolor=T.CARD, labelcolor=T.TEXT_MUTED,
                      loc="upper left", framealpha=0.8, edgecolor=T.BORDER)

    def _clear_chart(self, msg=""):
        for w in self._chart_container.winfo_children():
            w.destroy()
        ctk.CTkLabel(self._chart_container, text=msg or "No chart",
                     text_color=T.TEXT_MUTED).pack(expand=True)

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
            stocks     = settings.get("stocks", [])
            indicators = settings.get("indicators", [])

            if not stocks:
                self.after(0, lambda: self._finish_update(None, "No stocks configured."))
                return

            def progress(ticker, i, total):
                self.after(0, lambda: self._lbl_status.configure(
                    text=f"Fetching {ticker} ({i+1}/{total})..."))

            result = run_alerts(stocks, indicators, on_progress=progress)
            save_alerts(result)


            self.after(0, lambda: self._finish_update(result, "Done."))
        except Exception as e:
            self.after(0, lambda: self._finish_update(None, f"Error: {e}"))

    def _finish_update(self, result, status_msg):
        self._btn_update.configure(state="normal", text="Update")
        self._lbl_status.configure(text=status_msg)
        if result:
            saved = load_alerts()
            self._render_alerts(saved)
