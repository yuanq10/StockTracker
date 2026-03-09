import threading
import customtkinter as ctk
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from storage.settings_manager import load_settings, save_settings, load_alerts
import ui.theme as T

INDICATOR_STAT_KEYS = {"CCI": "CCI", "MACD": "MACD", "KDJ K": "KDJ"}


class StockSettingsPage(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, corner_radius=0, fg_color="transparent")
        self._app = app
        self._fig = None
        self._current_df = None
        self._current_ticker = None
        self._active_indicator = None
        self._stat_key_btns = {}
        self._build_ui()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _build_ui(self):
        # ── Top bar ──────────────────────────────────────────────────
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(16, 0))

        ctk.CTkLabel(
            top, text="Stocks",
            font=ctk.CTkFont(size=22, weight="bold"), text_color=T.TEXT
        ).pack(side="left")

        search_frame = ctk.CTkFrame(top, fg_color="transparent")
        search_frame.pack(side="right")

        self._entry_ticker = ctk.CTkEntry(
            search_frame, placeholder_text="Enter ticker (e.g. AAPL)",
            width=220, height=36, corner_radius=18,
            fg_color=T.CARD, border_color=T.BORDER,
            text_color=T.TEXT, placeholder_text_color=T.TEXT_MUTED
        )
        self._entry_ticker.pack(side="left", padx=(0, 8))
        self._entry_ticker.bind("<Return>", lambda _: self._on_add())

        ctk.CTkButton(
            search_frame, text="Add", width=80, height=36, corner_radius=18,
            fg_color=T.ACCENT, hover_color="#79b8ff", text_color="#000000",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._on_add
        ).pack(side="left")

        self._lbl_msg = ctk.CTkLabel(
            top, text="", font=ctk.CTkFont(size=11), text_color=T.TEXT_MUTED
        )
        self._lbl_msg.pack(side="left", padx=16)

        # ── Middle row ───────────────────────────────────────────────
        mid = ctk.CTkFrame(self, fg_color="transparent")
        mid.pack(fill="both", expand=True, padx=20, pady=16)

        # Right: stocks list
        right_panel = ctk.CTkFrame(
            mid, width=160, fg_color=T.CARD,
            corner_radius=12, border_width=1, border_color=T.BORDER
        )
        right_panel.pack(side="right", fill="y", padx=(10, 0))
        right_panel.pack_propagate(False)

        ctk.CTkLabel(
            right_panel, text="My Stocks",
            font=ctk.CTkFont(size=13, weight="bold"), text_color=T.TEXT
        ).pack(pady=(14, 8), padx=12, anchor="w")

        self._stocks_list = ctk.CTkScrollableFrame(
            right_panel, fg_color="transparent", scrollbar_button_color=T.BORDER
        )
        self._stocks_list.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # Left: chart + stats
        left_panel = ctk.CTkFrame(mid, fg_color="transparent")
        left_panel.pack(side="left", fill="both", expand=True)

        bottom = ctk.CTkFrame(left_panel, fg_color="transparent")
        bottom.pack(fill="both", expand=True)
        bottom.columnconfigure(0, weight=5)
        bottom.columnconfigure(1, weight=2)
        bottom.rowconfigure(0, weight=1)

        # Chart
        chart_frame = ctk.CTkFrame(
            bottom, fg_color=T.CARD, corner_radius=12,
            border_width=1, border_color=T.BORDER
        )
        chart_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        ctk.CTkLabel(
            chart_frame, text="Price Chart",
            font=ctk.CTkFont(size=12, weight="bold"), text_color=T.TEXT
        ).pack(pady=(14, 4), padx=12, anchor="w")

        self._chart_container = ctk.CTkFrame(chart_frame, fg_color="transparent")
        self._chart_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Stats
        stats_frame = ctk.CTkFrame(
            bottom, fg_color=T.CARD, corner_radius=12,
            border_width=1, border_color=T.BORDER
        )
        stats_frame.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        ctk.CTkLabel(
            stats_frame, text="Stats",
            font=ctk.CTkFont(size=12, weight="bold"), text_color=T.TEXT
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

        self._refresh_stocks_list()

    def _make_metric_card(self, parent, label, clickable=False, click_cmd=None, btn_store_key=None):
        card = ctk.CTkFrame(parent, fg_color=T.BG, corner_radius=8,
                            border_width=1, border_color=T.BORDER)
        card.pack(fill="x", pady=3)

        if clickable:
            header_btn = ctk.CTkButton(
                card, text=label, anchor="w", height=20,
                fg_color="transparent", hover_color=T.CARD,
                text_color=T.TEXT_MUTED, font=ctk.CTkFont(size=10),
                command=click_cmd
            )
            header_btn.pack(anchor="w", padx=8, pady=(6, 0))
            if btn_store_key is not None:
                self._stat_key_btns[btn_store_key] = header_btn
        else:
            ctk.CTkLabel(
                card, text=label, font=ctk.CTkFont(size=10),
                text_color=T.TEXT_MUTED, anchor="w"
            ).pack(anchor="w", padx=8, pady=(6, 0))

        val_lbl = ctk.CTkLabel(
            card, text="—",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=T.TEXT, anchor="w"
        )
        val_lbl.pack(anchor="w", padx=8, pady=(1, 7))
        return val_lbl

    # ------------------------------------------------------------------
    # Stocks list
    # ------------------------------------------------------------------
    def on_show(self):
        self._refresh_stocks_list()

    def _refresh_stocks_list(self):
        for w in self._stocks_list.winfo_children():
            w.destroy()
        settings = load_settings()
        stocks = settings.get("stocks", [])
        if not stocks:
            ctk.CTkLabel(
                self._stocks_list, text="No stocks added",
                font=ctk.CTkFont(size=12), text_color=T.TEXT_MUTED
            ).pack(pady=16)
        for ticker in stocks:
            item = ctk.CTkFrame(
                self._stocks_list, fg_color=T.BG,
                corner_radius=8, border_width=1, border_color=T.BORDER
            )
            item.pack(fill="x", pady=3)
            btn = ctk.CTkButton(
                item, text=ticker, anchor="w",
                fg_color="transparent", hover_color=T.CARD,
                text_color=T.TEXT, font=ctk.CTkFont(size=13, weight="bold"),
                command=lambda t=ticker: self._select_ticker(t)
            )
            btn.pack(side="left", fill="x", expand=True, padx=4, pady=4)
            del_btn = ctk.CTkButton(
                item, text="✕", width=28, height=28, corner_radius=14,
                fg_color="transparent", hover_color=T.DANGER,
                text_color=T.TEXT_MUTED, font=ctk.CTkFont(size=11),
                command=lambda t=ticker: self._on_remove(t)
            )
            del_btn.pack(side="right", padx=6, pady=4)

    def _on_add(self):
        ticker = self._entry_ticker.get().strip().upper()
        if not ticker:
            return
        settings = load_settings()
        stocks = settings.get("stocks", [])
        if ticker in stocks:
            self._lbl_msg.configure(text=f"{ticker} already added.", text_color=T.WARNING)
            return
        stocks.append(ticker)
        settings["stocks"] = stocks
        save_settings(settings)
        self._entry_ticker.delete(0, "end")
        self._lbl_msg.configure(text=f"Added {ticker}.", text_color=T.SUCCESS)
        self._refresh_stocks_list()

    def _on_remove(self, ticker: str):
        settings = load_settings()
        stocks = settings.get("stocks", [])
        if ticker in stocks:
            stocks.remove(ticker)
        settings["stocks"] = stocks
        save_settings(settings)
        self._lbl_msg.configure(text=f"Removed {ticker}.", text_color=T.TEXT_MUTED)
        self._refresh_stocks_list()

    # ------------------------------------------------------------------
    # Ticker selection
    # ------------------------------------------------------------------
    def _select_ticker(self, ticker: str):
        self._current_ticker = ticker
        self._active_indicator = None
        self._reset_indicator_btn_highlights()
        threading.Thread(target=self._load_ticker_data, args=(ticker,), daemon=True).start()

    def _load_ticker_data(self, ticker: str):
        try:
            from core.data_fetcher import fetch_stock_data, get_stock_info
            df = fetch_stock_data(ticker)
            info = get_stock_info(ticker)
            alerts_data = load_alerts()
            stat = alerts_data.get("stats", {}).get(ticker, {})
            self.after(0, lambda: self._show_ticker_detail(df, ticker, info, stat))
        except Exception as e:
            self.after(0, lambda: self._show_error(str(e)))

    def _show_ticker_detail(self, df, ticker, info, stat):
        self._current_df = df
        self._render_chart(df, ticker, self._active_indicator)

        def fmt(val, suffix=""):
            return f"{val}{suffix}" if val is not None else "—"

        self._stat_labels["Close"].configure(text=fmt(info.get("price")))
        change = info.get("change_pct")
        color = T.SUCCESS if (change or 0) >= 0 else T.DANGER
        self._stat_labels["Change % (1d)"].configure(text=fmt(change, "%"), text_color=color)
        vol = info.get("volume")
        self._stat_labels["Volume"].configure(text=f"{vol:,}" if vol else "—")
        self._stat_labels["CCI"].configure(text=fmt(stat.get("cci")))
        self._stat_labels["MACD"].configure(text=fmt(stat.get("macd")))
        self._stat_labels["KDJ K"].configure(text=fmt(stat.get("kdj_k")))

    def _show_error(self, msg: str):
        for w in self._chart_container.winfo_children():
            w.destroy()
        ctk.CTkLabel(self._chart_container, text=f"Error: {msg}",
                     text_color=T.DANGER).pack(expand=True)

    # ------------------------------------------------------------------
    # Indicator subplot toggle
    # ------------------------------------------------------------------
    def _toggle_indicator_plot(self, stat_key: str, ind_type: str):
        if self._current_df is None or self._current_ticker is None:
            return
        if self._active_indicator == ind_type:
            self._active_indicator = None
            self._reset_indicator_btn_highlights()
        else:
            self._active_indicator = ind_type
            self._reset_indicator_btn_highlights()
            self._stat_key_btns[stat_key].configure(text_color=T.ACCENT, fg_color=T.CARD)
        self._render_chart(self._current_df, self._current_ticker, self._active_indicator)

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
            buy_th  = ind_cfg.get("buy_threshold", -100)
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
