import customtkinter as ctk
from storage.settings_manager import load_settings, save_settings
import ui.theme as T

# ── TA-Lib integration ───────────────────────────────────────────────────────
_USEFUL_GROUPS = {
    "Momentum Indicators", "Overlap Studies", "Volatility Indicators",
    "Volume Indicators", "Cycle Indicators", "Statistic Functions",
}
try:
    import talib
    from talib import abstract as _talib_abstract
    _groups = talib.get_function_groups()
    _ALL_INDICATORS = sorted(
        fn for grp, fns in _groups.items() if grp in _USEFUL_GROUPS for fn in fns
    )
    _TA_AVAILABLE = True
except Exception:
    _ALL_INDICATORS = []
    _TA_AVAILABLE = False

# ── Constants ─────────────────────────────────────────────────────────────────
INDICATOR_TYPES = ["CCI", "MACD", "KDJ"]

THRESHOLD_FIELDS = {
    "CCI": [
        ("buy_threshold",  "Buy threshold (lower bound, e.g. -100)"),
        ("sell_threshold", "Sell threshold (upper bound, e.g. 100)"),
    ],
    "MACD": [
        ("buy_threshold",  "Upper bound — alert when histogram < this (e.g. 0.5)"),
        ("sell_threshold", "Lower bound — alert when histogram > this (e.g. -0.5)"),
    ],
    "KDJ": [
        ("buy_threshold",  "Oversold threshold for J (e.g. 20) — alert when J < this"),
        ("sell_threshold", "Overbought threshold for J (e.g. 80) — alert when J > this"),
    ],
}

GENERIC_THRESHOLD_FIELDS = [
    ("buy_threshold",  "Buy threshold (alert when value < this)"),
    ("sell_threshold", "Sell threshold (alert when value > this)"),
]

CALC_PARAMS = {
    "CCI":  [("period", "Period", 20)],
    "MACD": [("fast", "Fast EMA", 12), ("slow", "Slow EMA", 26), ("signal", "Signal EMA", 9)],
    "KDJ":  [("period", "Period", 9), ("k_smooth", "K smooth", 3), ("d_smooth", "D smooth", 3)],
}

INDICATOR_DEFAULTS = {
    # ── Built-in (custom calculated) ──────────────────────────────────────────
    "CCI":  {"type": "CCI",  "enabled": True, "period": 20,
             "buy_threshold": -100, "sell_threshold": 100},
    "MACD": {"type": "MACD", "enabled": True, "fast": 12, "slow": 26, "signal": 9,
             "buy_threshold": 0.5, "sell_threshold": -0.5},
    "KDJ":  {"type": "KDJ",  "enabled": True, "period": 9, "k_smooth": 3, "d_smooth": 3,
             "buy_threshold": 20, "sell_threshold": 80},

    # ── Momentum Indicators ───────────────────────────────────────────────────
    # ADX: 0–100; >25 = strong trend (no direction), >50 = very strong
    "ADX":      {"type": "ADX",  "enabled": True, "timeperiod": 14,
                 "buy_threshold": None, "sell_threshold": 25},
    # ADXR: smoothed ADX, same interpretation
    "ADXR":     {"type": "ADXR", "enabled": True, "timeperiod": 14,
                 "buy_threshold": None, "sell_threshold": 25},
    # APO: price-absolute oscillator; positive = bullish, negative = bearish
    "APO":      {"type": "APO",  "enabled": True, "fastperiod": 12, "slowperiod": 26, "matype": 0,
                 "buy_threshold": None, "sell_threshold": None},
    # AROON: two outputs (down, up); first output=aroondown; thresholds not straightforward
    "AROON":    {"type": "AROON", "enabled": True, "timeperiod": 14,
                 "buy_threshold": None, "sell_threshold": None},
    # AROONOSC: range -100 to +100; >50 = bullish, <-50 = bearish
    "AROONOSC": {"type": "AROONOSC", "enabled": True, "timeperiod": 14,
                 "buy_threshold": -50, "sell_threshold": 50},
    # BOP: range -1 to +1; >0.5 = strong buying pressure, <-0.5 = strong selling pressure
    "BOP":      {"type": "BOP",  "enabled": True,
                 "buy_threshold": -0.5, "sell_threshold": 0.5},
    # CMO: range -100 to +100; Chande standard: <-50 oversold, >+50 overbought
    "CMO":      {"type": "CMO",  "enabled": True, "timeperiod": 14,
                 "buy_threshold": -50, "sell_threshold": 50},
    # DX: 0–100; directional movement index, same as ADX for strength
    "DX":       {"type": "DX",   "enabled": True, "timeperiod": 14,
                 "buy_threshold": None, "sell_threshold": 25},
    # MACDEXT/MACDFIX: outputs macd line; crossover zero = signal
    "MACDEXT":  {"type": "MACDEXT", "enabled": True,
                 "fastperiod": 12, "fastmatype": 0,
                 "slowperiod": 26, "slowmatype": 0,
                 "signalperiod": 9, "signalmatype": 0,
                 "buy_threshold": None, "sell_threshold": None},
    "MACDFIX":  {"type": "MACDFIX", "enabled": True, "signalperiod": 9,
                 "buy_threshold": None, "sell_threshold": None},
    # MFI: Money Flow Index 0–100; <20 oversold, >80 overbought (like RSI with volume)
    "MFI":      {"type": "MFI",  "enabled": True, "timeperiod": 14,
                 "buy_threshold": 20, "sell_threshold": 80},
    # MINUS_DI: bearish directional indicator; >25 = strong bearish pressure
    "MINUS_DI": {"type": "MINUS_DI", "enabled": True, "timeperiod": 14,
                 "buy_threshold": None, "sell_threshold": 25},
    # MINUS_DM: raw bearish directional movement
    "MINUS_DM": {"type": "MINUS_DM", "enabled": True, "timeperiod": 14,
                 "buy_threshold": None, "sell_threshold": None},
    # MOM: momentum = close - close[n]; cross above/below zero
    "MOM":      {"type": "MOM",  "enabled": True, "timeperiod": 10,
                 "buy_threshold": None, "sell_threshold": None},
    # PLUS_DI: bullish directional indicator; >25 = strong bullish pressure
    "PLUS_DI":  {"type": "PLUS_DI", "enabled": True, "timeperiod": 14,
                 "buy_threshold": None, "sell_threshold": 25},
    # PLUS_DM: raw bullish directional movement
    "PLUS_DM":  {"type": "PLUS_DM", "enabled": True, "timeperiod": 14,
                 "buy_threshold": None, "sell_threshold": None},
    # PPO: percentage price oscillator; ±2% = significant divergence
    "PPO":      {"type": "PPO",  "enabled": True, "fastperiod": 12, "slowperiod": 26, "matype": 0,
                 "buy_threshold": -2.0, "sell_threshold": 2.0},
    # ROC: % rate of change; ±5% = significant momentum
    "ROC":      {"type": "ROC",  "enabled": True, "timeperiod": 10,
                 "buy_threshold": -5.0, "sell_threshold": 5.0},
    # ROCP: ROC as proportion (not %); ±0.05 = 5%
    "ROCP":     {"type": "ROCP", "enabled": True, "timeperiod": 10,
                 "buy_threshold": -0.05, "sell_threshold": 0.05},
    # ROCR: ROC as ratio (1.0 = no change); <0.95 oversold, >1.05 overbought
    "ROCR":     {"type": "ROCR", "enabled": True, "timeperiod": 10,
                 "buy_threshold": 0.95, "sell_threshold": 1.05},
    # ROCR100: ROC ratio * 100; <95 oversold, >105 overbought
    "ROCR100":  {"type": "ROCR100", "enabled": True, "timeperiod": 10,
                 "buy_threshold": 95.0, "sell_threshold": 105.0},
    # RSI: 0–100; <30 oversold, >70 overbought (Wilder's standard)
    "RSI":      {"type": "RSI",  "enabled": True, "timeperiod": 14,
                 "buy_threshold": 30, "sell_threshold": 70},
    # STOCH: 0–100 (first output = slowK); <20 oversold, >80 overbought
    "STOCH":    {"type": "STOCH", "enabled": True,
                 "fastk_period": 5, "slowk_period": 3, "slowk_matype": 0,
                 "slowd_period": 3, "slowd_matype": 0,
                 "buy_threshold": 20, "sell_threshold": 80},
    # STOCHF: fast stochastic 0–100 (first output = fastK); more sensitive
    "STOCHF":   {"type": "STOCHF", "enabled": True,
                 "fastk_period": 5, "fastd_period": 3, "fastd_matype": 0,
                 "buy_threshold": 20, "sell_threshold": 80},
    # STOCHRSI: 0–100 (first output = fastK of RSI); <20 oversold, >80 overbought
    "STOCHRSI": {"type": "STOCHRSI", "enabled": True,
                 "timeperiod": 14, "fastk_period": 5, "fastd_period": 3, "fastd_matype": 0,
                 "buy_threshold": 20, "sell_threshold": 80},
    # TRIX: 1-day ROC of triple-smoothed EMA; >+0.1% notable upward momentum, <-0.1% downward
    "TRIX":     {"type": "TRIX", "enabled": True, "timeperiod": 30,
                 "buy_threshold": -0.1, "sell_threshold": 0.1},
    # ULTOSC: 0–100; <30 oversold, >70 overbought (Williams' standard)
    "ULTOSC":   {"type": "ULTOSC", "enabled": True,
                 "timeperiod1": 7, "timeperiod2": 14, "timeperiod3": 28,
                 "buy_threshold": 30, "sell_threshold": 70},
    # WILLR: -100 to 0; <-80 oversold, >-20 overbought (Williams %R)
    "WILLR":    {"type": "WILLR", "enabled": True, "timeperiod": 14,
                 "buy_threshold": -80, "sell_threshold": -20},

    # ── Overlap Studies (price-based MAs — compare price to output, not fixed threshold) ──
    "BBANDS":   {"type": "BBANDS", "enabled": True,
                 "timeperiod": 20, "nbdevup": 2.0, "nbdevdn": 2.0, "matype": 0,
                 "buy_threshold": None, "sell_threshold": None},
    "DEMA":     {"type": "DEMA",   "enabled": True, "timeperiod": 21,
                 "buy_threshold": None, "sell_threshold": None},
    "EMA":      {"type": "EMA",    "enabled": True, "timeperiod": 21,
                 "buy_threshold": None, "sell_threshold": None},
    "HT_TRENDLINE": {"type": "HT_TRENDLINE", "enabled": True,
                     "buy_threshold": None, "sell_threshold": None},
    "KAMA":     {"type": "KAMA",   "enabled": True, "timeperiod": 30,
                 "buy_threshold": None, "sell_threshold": None},
    "MA":       {"type": "MA",     "enabled": True, "timeperiod": 30, "matype": 0,
                 "buy_threshold": None, "sell_threshold": None},
    "MAMA":     {"type": "MAMA",   "enabled": True, "fastlimit": 0.5, "slowlimit": 0.05,
                 "buy_threshold": None, "sell_threshold": None},
    "MAVP":     {"type": "MAVP",   "enabled": True,
                 "minperiod": 2, "maxperiod": 30, "matype": 0,
                 "buy_threshold": None, "sell_threshold": None},
    "MIDPOINT": {"type": "MIDPOINT", "enabled": True, "timeperiod": 14,
                 "buy_threshold": None, "sell_threshold": None},
    "MIDPRICE": {"type": "MIDPRICE", "enabled": True, "timeperiod": 14,
                 "buy_threshold": None, "sell_threshold": None},
    # SAR: parabolic stop-and-reverse; output flips above/below price
    "SAR":      {"type": "SAR",    "enabled": True, "acceleration": 0.02, "maximum": 0.2,
                 "buy_threshold": None, "sell_threshold": None},
    "SAREXT":   {"type": "SAREXT", "enabled": True,
                 "startvalue": 0.0, "offsetonreverse": 0.0,
                 "accelerationinitlong": 0.02, "accelerationlong": 0.02, "accelerationmaxlong": 0.2,
                 "accelerationinitshort": 0.02, "accelerationshort": 0.02, "accelerationmaxshort": 0.2,
                 "buy_threshold": None, "sell_threshold": None},
    "SMA":      {"type": "SMA",    "enabled": True, "timeperiod": 20,
                 "buy_threshold": None, "sell_threshold": None},
    "T3":       {"type": "T3",     "enabled": True, "timeperiod": 5, "vfactor": 0.7,
                 "buy_threshold": None, "sell_threshold": None},
    "TEMA":     {"type": "TEMA",   "enabled": True, "timeperiod": 21,
                 "buy_threshold": None, "sell_threshold": None},
    "TRIMA":    {"type": "TRIMA",  "enabled": True, "timeperiod": 30,
                 "buy_threshold": None, "sell_threshold": None},
    "WMA":      {"type": "WMA",    "enabled": True, "timeperiod": 20,
                 "buy_threshold": None, "sell_threshold": None},

    # ── Volatility Indicators ─────────────────────────────────────────────────
    # ATR: absolute price range; no fixed threshold (stock-price dependent)
    "ATR":      {"type": "ATR",  "enabled": True, "timeperiod": 14,
                 "buy_threshold": None, "sell_threshold": None},
    # NATR: normalised ATR in %; >3% = elevated volatility, >5% = high
    "NATR":     {"type": "NATR", "enabled": True, "timeperiod": 14,
                 "buy_threshold": None, "sell_threshold": 3.0},
    # TRANGE: single-bar true range; stock-price dependent
    "TRANGE":   {"type": "TRANGE", "enabled": True,
                 "buy_threshold": None, "sell_threshold": None},

    # ── Volume Indicators ─────────────────────────────────────────────────────
    # AD: cumulative A/D line; divergence-based, no fixed threshold
    "AD":       {"type": "AD",    "enabled": True,
                 "buy_threshold": None, "sell_threshold": None},
    # ADOSC: A/D oscillator; >0 = accumulation, <0 = distribution
    "ADOSC":    {"type": "ADOSC", "enabled": True, "fastperiod": 3, "slowperiod": 10,
                 "buy_threshold": None, "sell_threshold": None},
    # OBV: on-balance volume; trend-following, no fixed threshold
    "OBV":      {"type": "OBV",   "enabled": True,
                 "buy_threshold": None, "sell_threshold": None},

    # ── Cycle Indicators (Hilbert Transform) ──────────────────────────────────
    "HT_DCPERIOD": {"type": "HT_DCPERIOD", "enabled": True,
                    "buy_threshold": None, "sell_threshold": None},
    "HT_DCPHASE":  {"type": "HT_DCPHASE",  "enabled": True,
                    "buy_threshold": None, "sell_threshold": None},
    # HT_PHASOR: first output = inphase component
    "HT_PHASOR":   {"type": "HT_PHASOR",   "enabled": True,
                    "buy_threshold": None, "sell_threshold": None},
    # HT_SINE: first output = sine; oscillates -1 to +1; <-0.8 oversold, >+0.8 overbought
    "HT_SINE":     {"type": "HT_SINE",     "enabled": True,
                    "buy_threshold": -0.8, "sell_threshold": 0.8},
    # HT_TRENDMODE: 0 = cycle mode, 1 = trend mode
    "HT_TRENDMODE": {"type": "HT_TRENDMODE", "enabled": True,
                     "buy_threshold": None, "sell_threshold": None},

    # ── Statistic Functions ───────────────────────────────────────────────────
    # BETA: market sensitivity; >1.5 = high beta alert
    "BETA":     {"type": "BETA",   "enabled": True, "timeperiod": 5,
                 "buy_threshold": None, "sell_threshold": 1.5},
    # CORREL: Pearson correlation -1 to +1 between High and Low series
    "CORREL":   {"type": "CORREL", "enabled": True, "timeperiod": 30,
                 "buy_threshold": None, "sell_threshold": None},
    # LINEARREG: linear regression value (price-based); no fixed threshold
    "LINEARREG":           {"type": "LINEARREG",           "enabled": True, "timeperiod": 14,
                            "buy_threshold": None, "sell_threshold": None},
    # LINEARREG_ANGLE: slope in degrees; >0 = uptrend, <0 = downtrend
    "LINEARREG_ANGLE":     {"type": "LINEARREG_ANGLE",     "enabled": True, "timeperiod": 14,
                            "buy_threshold": -45, "sell_threshold": 45},
    "LINEARREG_INTERCEPT": {"type": "LINEARREG_INTERCEPT", "enabled": True, "timeperiod": 14,
                            "buy_threshold": None, "sell_threshold": None},
    # LINEARREG_SLOPE: positive = uptrend, negative = downtrend (price-unit based)
    "LINEARREG_SLOPE":     {"type": "LINEARREG_SLOPE",     "enabled": True, "timeperiod": 14,
                            "buy_threshold": None, "sell_threshold": None},
    # STDDEV: price standard deviation; stock-price dependent
    "STDDEV":   {"type": "STDDEV", "enabled": True, "timeperiod": 5, "nbdev": 1.0,
                 "buy_threshold": None, "sell_threshold": None},
    # TSF: time series forecast (linear regression of next value)
    "TSF":      {"type": "TSF",    "enabled": True, "timeperiod": 14,
                 "buy_threshold": None, "sell_threshold": None},
    # VAR: statistical variance; stock-price dependent
    "VAR":      {"type": "VAR",    "enabled": True, "timeperiod": 5, "nbdev": 1.0,
                 "buy_threshold": None, "sell_threshold": None},
}

# Params excluded from the "add indicator" form — not calc parameters
def _sorted_indicator_types() -> list[str]:
    settings = load_settings()
    saved = [i["type"] for i in settings.get("indicators", [])]
    all_types = sorted(set(INDICATOR_TYPES) | set(saved))
    return all_types


def _get_ta_calc_params(name: str) -> list[tuple[str, int | float]]:
    """Return (param_name, default) for calc params of a TA-Lib indicator."""
    if not _TA_AVAILABLE:
        return [("timeperiod", 14)]
    try:
        info = _talib_abstract.Function(name.upper()).info
        return list(info["parameters"].items())
    except Exception:
        return [("timeperiod", 14)]


# ── Autocomplete suggestion popup ─────────────────────────────────────────────
class _SuggestionPopup:
    """A borderless Toplevel that floats below an entry to show filtered suggestions."""

    def __init__(self, anchor: ctk.CTkEntry, on_select):
        self._anchor = anchor
        self._on_select = on_select
        self._win: ctk.CTkToplevel | None = None

    def show(self, matches: list[str]):
        if not matches:
            self.hide()
            return

        if self._win is None or not self._win.winfo_exists():
            self._win = ctk.CTkToplevel(self._anchor)
            self._win.overrideredirect(True)
            self._win.attributes("-topmost", True)
            self._win.configure(fg_color=T.BORDER)  # 1px border effect via bg

        self._win.deiconify()

        # Position below anchor
        x = self._anchor.winfo_rootx()
        y = self._anchor.winfo_rooty() + self._anchor.winfo_height() + 2
        w = self._anchor.winfo_width()
        item_h = 28
        h = min(len(matches) * item_h + 6, 168)
        self._win.geometry(f"{w}x{h}+{x}+{y}")

        for child in self._win.winfo_children():
            child.destroy()

        inner = ctk.CTkScrollableFrame(
            self._win, fg_color=T.CARD,
            scrollbar_button_color=T.BORDER, corner_radius=0
        )
        inner.pack(fill="both", expand=True, padx=1, pady=1)

        for name in matches:
            btn = ctk.CTkButton(
                inner, text=name.upper(), anchor="w",
                height=26, corner_radius=4,
                fg_color="transparent", hover_color=T.BORDER,
                text_color=T.TEXT, font=ctk.CTkFont(size=12),
                command=lambda n=name: self._on_select(n)
            )
            btn.pack(fill="x", padx=2, pady=1)

    def hide(self):
        if self._win and self._win.winfo_exists():
            self._win.withdraw()

    def destroy(self):
        if self._win and self._win.winfo_exists():
            self._win.destroy()
        self._win = None


# ── Main page ─────────────────────────────────────────────────────────────────
class IndicatorSettingsPage(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, corner_radius=0, fg_color="transparent")
        self._app = app
        self._threshold_entries: dict = {}
        self._calc_entries: dict = {}
        self._calc_param_types: dict = {}  # key -> type (int or float)
        self._add_param_entries: dict = {}
        self._current_ind = "CCI"
        self._selected_new_ind: str | None = None
        self._popup: _SuggestionPopup | None = None
        self._updating_name = False  # guard: suppress trace while setting entry text
        self._build_ui()
        self._load_indicator("CCI")
        self.bind("<Destroy>", self._on_destroy)

    def _on_destroy(self, event):
        if event.widget is self and self._popup:
            self._popup.destroy()

    # ------------------------------------------------------------------
    # Top-level layout
    # ------------------------------------------------------------------
    def _build_ui(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(16, 0))
        ctk.CTkLabel(
            top, text="Indicators",
            font=ctk.CTkFont(size=22, weight="bold"), text_color=T.TEXT
        ).pack(side="left")

        mid = ctk.CTkFrame(self, fg_color="transparent")
        mid.pack(fill="both", expand=True, padx=20, pady=16)

        # Pack right panels first so left_panel fills remaining space
        right_panel = ctk.CTkFrame(
            mid, width=200, fg_color=T.CARD,
            corner_radius=12, border_width=1, border_color=T.BORDER
        )
        right_panel.pack(side="right", fill="y", padx=(10, 0))
        right_panel.pack_propagate(False)
        self._build_active_list(right_panel)

        add_panel = ctk.CTkFrame(
            mid, width=290, fg_color=T.CARD,
            corner_radius=12, border_width=1, border_color=T.BORDER
        )
        add_panel.pack(side="right", fill="y", padx=(10, 0))
        add_panel.pack_propagate(False)
        self._build_add_panel(add_panel)

        left_panel = ctk.CTkFrame(
            mid, fg_color=T.CARD,
            corner_radius=12, border_width=1, border_color=T.BORDER
        )
        left_panel.pack(side="left", fill="both", expand=True)
        self._build_config_panel(left_panel)

    # ------------------------------------------------------------------
    # Active Indicators panel (right)
    # ------------------------------------------------------------------
    def _build_active_list(self, panel):
        ctk.CTkLabel(
            panel, text="Active Indicators",
            font=ctk.CTkFont(size=13, weight="bold"), text_color=T.TEXT
        ).pack(pady=(14, 8), padx=12, anchor="w")

        self._ind_list_frame = ctk.CTkScrollableFrame(
            panel, fg_color="transparent", scrollbar_button_color=T.BORDER
        )
        self._ind_list_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    # ------------------------------------------------------------------
    # Add Indicator panel (center-right)
    # ------------------------------------------------------------------
    def _build_add_panel(self, panel):
        ctk.CTkLabel(
            panel, text="Add Indicator",
            font=ctk.CTkFont(size=13, weight="bold"), text_color=T.TEXT
        ).pack(pady=(14, 8), padx=14, anchor="w")

        ctk.CTkFrame(panel, height=1, fg_color=T.BORDER).pack(fill="x", padx=14)

        # Scrollable content area so many calc params don't overflow
        scroll = ctk.CTkScrollableFrame(
            panel, fg_color="transparent", scrollbar_button_color=T.BORDER
        )
        scroll.pack(fill="both", expand=True, padx=14, pady=10)

        # ── Indicator name (autocomplete) ─────────────────────────────
        ctk.CTkLabel(
            scroll, text="Indicator Name", anchor="w",
            text_color=T.TEXT_MUTED, font=ctk.CTkFont(size=11)
        ).pack(anchor="w", pady=(0, 4))

        self._new_name_var = ctk.StringVar()
        self._new_name_entry = ctk.CTkEntry(
            scroll, textvariable=self._new_name_var,
            placeholder_text="Type to search…",
            height=34, corner_radius=8,
            fg_color=T.BG, border_color=T.BORDER,
            text_color=T.TEXT, placeholder_text_color=T.TEXT_MUTED
        )
        self._new_name_entry.pack(fill="x")
        self._new_name_var.trace_add("write", self._on_name_type)
        self._new_name_entry.bind(
            "<FocusOut>",
            lambda e: self.after(160, lambda: self._popup.hide() if self._popup else None)
        )

        # ── Dynamic fields (revealed after valid selection) ───────────
        self._add_fields_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        # Not packed yet — appears when indicator is selected

        # ── Status label ──────────────────────────────────────────────
        self._lbl_add_msg = ctk.CTkLabel(scroll, text="", font=ctk.CTkFont(size=11))
        self._lbl_add_msg.pack(anchor="w", pady=(6, 0))

        # Create popup (anchor widget set after entry is realized)
        self._popup = _SuggestionPopup(self._new_name_entry, self._select_new_indicator)

    # ------------------------------------------------------------------
    # Autocomplete handlers
    # ------------------------------------------------------------------
    def _on_name_type(self, *_):
        if self._updating_name:
            return
        text = self._new_name_var.get().strip().lower()

        # If user edited away from the confirmed name, clear selection
        if self._selected_new_ind and self._new_name_var.get().upper() != self._selected_new_ind:
            self._selected_new_ind = None
            self._add_fields_frame.pack_forget()

        if not text:
            self._popup.hide()
            return

        matches = [n for n in _ALL_INDICATORS if text in n.lower()][:18]
        self._popup.show(matches)

    def _select_new_indicator(self, name: str):
        """Called when user clicks a suggestion."""
        self._selected_new_ind = name.upper()
        self._updating_name = True
        self._new_name_entry.delete(0, "end")
        self._new_name_entry.insert(0, name.upper())
        self._updating_name = False
        self._popup.hide()
        self._build_add_fields(name)
        self._lbl_add_msg.configure(text="")

    def _build_add_fields(self, name: str):
        """Build calc-param + threshold fields for the selected indicator."""
        for w in self._add_fields_frame.winfo_children():
            w.destroy()
        self._add_param_entries = {}

        # Pull pre-defined defaults (calc params + thresholds)
        defaults = INDICATOR_DEFAULTS.get(name.upper(), {})

        # ── Calc parameters ───────────────────────────────────────────
        params = _get_ta_calc_params(name)

        if params:
            ctk.CTkLabel(
                self._add_fields_frame, text="Parameters", anchor="w",
                text_color=T.TEXT_MUTED, font=ctk.CTkFont(size=11, weight="bold")
            ).pack(anchor="w", pady=(14, 4))

            for pname, talib_default in params:
                # Prefer our curated default over talib's raw default
                value = defaults.get(pname, talib_default)
                row = ctk.CTkFrame(self._add_fields_frame, fg_color="transparent")
                row.pack(fill="x", pady=3)
                ctk.CTkLabel(
                    row, text=pname, anchor="w",
                    text_color=T.TEXT_MUTED, font=ctk.CTkFont(size=11)
                ).pack(anchor="w", pady=(0, 2))
                entry = ctk.CTkEntry(
                    row, height=32, corner_radius=8,
                    fg_color=T.BG, border_color=T.BORDER, text_color=T.TEXT
                )
                entry.insert(0, str(value))
                entry.pack(fill="x")
                self._add_param_entries[pname] = entry

        # ── Alert thresholds ──────────────────────────────────────────
        ctk.CTkFrame(self._add_fields_frame, height=1, fg_color=T.BORDER).pack(fill="x", pady=(12, 0))
        ctk.CTkLabel(
            self._add_fields_frame, text="Alert Thresholds", anchor="w",
            text_color=T.TEXT_MUTED, font=ctk.CTkFont(size=11, weight="bold")
        ).pack(anchor="w", pady=(8, 4))

        for key, label in [("buy_threshold", "Buy threshold (alert when value < this)"),
                            ("sell_threshold", "Sell threshold (alert when value > this)")]:
            row = ctk.CTkFrame(self._add_fields_frame, fg_color="transparent")
            row.pack(fill="x", pady=3)
            ctk.CTkLabel(
                row, text=label, anchor="w",
                text_color=T.TEXT_MUTED, font=ctk.CTkFont(size=11)
            ).pack(anchor="w", pady=(0, 2))
            entry = ctk.CTkEntry(
                row, height=32, corner_radius=8,
                fg_color=T.BG, border_color=T.BORDER, text_color=T.TEXT,
                placeholder_text="Optional", placeholder_text_color=T.TEXT_MUTED
            )
            preset = defaults.get(key)
            if preset is not None:
                entry.insert(0, str(preset))
            entry.pack(fill="x")
            self._add_param_entries[key] = entry

        # ── Add button ────────────────────────────────────────────────
        ctk.CTkButton(
            self._add_fields_frame, text="Add Indicator",
            height=36, corner_radius=18,
            fg_color=T.ACCENT, hover_color="#79b8ff", text_color="#000000",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._on_add_indicator
        ).pack(fill="x", pady=(14, 0))

        self._add_fields_frame.pack(fill="x")

    def _on_add_indicator(self):
        name = self._selected_new_ind
        if not name:
            self._lbl_add_msg.configure(text="Select a valid indicator.", text_color=T.DANGER)
            return

        settings = load_settings()
        indicators = settings.get("indicators", [])
        if any(i["type"] == name for i in indicators):
            self._lbl_add_msg.configure(text=f"'{name}' already exists.", text_color=T.WARNING)
            return

        new_ind: dict = {"type": name, "enabled": True}
        try:
            for key, entry in self._add_param_entries.items():
                val = entry.get().strip()
                if key in ("buy_threshold", "sell_threshold"):
                    new_ind[key] = float(val) if val else None
                else:
                    new_ind[key] = int(val) if val else 14
        except ValueError:
            self._lbl_add_msg.configure(text="Invalid number in fields.", text_color=T.DANGER)
            return

        indicators.append(new_ind)
        settings["indicators"] = indicators
        save_settings(settings)

        # Reset add panel
        self._new_name_entry.delete(0, "end")
        self._selected_new_ind = None
        self._add_fields_frame.pack_forget()
        self._lbl_add_msg.configure(text=f"'{name}' added.", text_color=T.SUCCESS)

        self._update_dropdown()
        self._load_indicator(name)
        self._refresh_indicator_list()

    # ------------------------------------------------------------------
    # Indicator config panel (left)
    # ------------------------------------------------------------------
    def _build_config_panel(self, panel):
        # ── Selector row ──────────────────────────────────────────────
        selector_row = ctk.CTkFrame(panel, fg_color="transparent")
        selector_row.pack(fill="x", padx=16, pady=(16, 12))

        ctk.CTkLabel(
            selector_row, text="Indicator:", anchor="w",
            text_color=T.TEXT_MUTED, font=ctk.CTkFont(size=12)
        ).pack(side="left", padx=(0, 8))

        self._dropdown = ctk.CTkOptionMenu(
            selector_row,
            values=_sorted_indicator_types(),
            command=self._load_indicator,
            width=160, height=34, corner_radius=8,
            fg_color=T.CARD, button_color=T.BORDER, button_hover_color=T.ACCENT,
            text_color=T.TEXT, font=ctk.CTkFont(size=13),
            dropdown_fg_color=T.CARD, dropdown_text_color=T.TEXT,
            dropdown_hover_color=T.BORDER
        )
        self._dropdown.pack(side="left")

        ctk.CTkFrame(panel, height=1, fg_color=T.BORDER).pack(fill="x", padx=16)

        # ── Two-column body ───────────────────────────────────────────
        body = ctk.CTkFrame(panel, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=12)

        # Left sub-column: calculation parameters
        calc_col = ctk.CTkFrame(body, fg_color="transparent")
        calc_col.pack(side="left", fill="both", expand=True)

        ctk.CTkLabel(
            calc_col, text="Calculation Parameters",
            font=ctk.CTkFont(size=12, weight="bold"), text_color=T.TEXT
        ).pack(anchor="w", pady=(0, 8))

        self._calc_frame = ctk.CTkScrollableFrame(
            calc_col, fg_color="transparent", scrollbar_button_color=T.BORDER
        )
        self._calc_frame.pack(fill="both", expand=True)

        # Vertical divider
        ctk.CTkFrame(body, width=1, fg_color=T.BORDER).pack(side="left", fill="y", padx=14)

        # Right sub-column: alert thresholds
        thresh_col = ctk.CTkFrame(body, fg_color="transparent")
        thresh_col.pack(side="left", fill="both", expand=True)

        ctk.CTkLabel(
            thresh_col, text="Alert Thresholds",
            font=ctk.CTkFont(size=12, weight="bold"), text_color=T.TEXT
        ).pack(anchor="w", pady=(0, 8))

        self._threshold_frame = ctk.CTkFrame(thresh_col, fg_color="transparent")
        self._threshold_frame.pack(fill="both", expand=True)

        self._macd_note = ctk.CTkLabel(
            self._threshold_frame,
            text="Note: Crossover alerts also fire\nregardless of threshold.",
            text_color=T.TEXT_MUTED, font=ctk.CTkFont(size=11), justify="left"
        )
        self._kdj_note = ctk.CTkLabel(
            self._threshold_frame,
            text="Note: K/D crossover alerts also\nfire automatically.",
            text_color=T.TEXT_MUTED, font=ctk.CTkFont(size=11), justify="left"
        )

        # ── Bottom bar ────────────────────────────────────────────────
        self._lbl_msg = ctk.CTkLabel(panel, text="", font=ctk.CTkFont(size=11))
        self._lbl_msg.pack(padx=16, pady=(0, 4), anchor="w", side="bottom")

        btn_row = ctk.CTkFrame(panel, fg_color="transparent")
        btn_row.pack(padx=16, pady=(0, 12), anchor="w", side="bottom")

        ctk.CTkButton(
            btn_row, text="Save", width=100, height=36, corner_radius=18,
            fg_color=T.ACCENT, hover_color="#79b8ff", text_color="#000000",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._on_save
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_row, text="Reset to Default", width=140, height=36, corner_radius=18,
            fg_color=T.CARD, hover_color=T.BORDER, text_color=T.TEXT_MUTED,
            font=ctk.CTkFont(size=12),
            command=self._on_reset_defaults
        ).pack(side="left")

        self._refresh_indicator_list()

    # ------------------------------------------------------------------
    # Load indicator config into both sub-columns
    # ------------------------------------------------------------------
    def _load_indicator(self, ind_type: str = None):
        if ind_type is None:
            ind_type = self._current_ind
        self._current_ind = ind_type
        self._dropdown.set(ind_type)

        settings = load_settings()
        ind_cfg = next(
            (i for i in settings.get("indicators", []) if i["type"] == ind_type),
            INDICATOR_DEFAULTS.get(
                ind_type,
                {"type": ind_type, "enabled": True, "buy_threshold": 0, "sell_threshold": 0}
            ).copy()
        )

        # ── Calc parameters (left column) ─────────────────────────────
        for w in self._calc_frame.winfo_children():
            w.destroy()
        self._calc_entries = {}
        self._calc_param_types = {}

        if ind_type in CALC_PARAMS:
            param_list = [(k, lbl, d) for k, lbl, d in CALC_PARAMS[ind_type]]
        else:
            raw = _get_ta_calc_params(ind_type)
            param_list = [(k, k.replace("_", " ").title(), d) for k, d in raw]

        if param_list:
            for key, label, default in param_list:
                row = ctk.CTkFrame(self._calc_frame, fg_color="transparent")
                row.pack(fill="x", pady=5)
                ctk.CTkLabel(
                    row, text=label, anchor="w",
                    text_color=T.TEXT_MUTED, font=ctk.CTkFont(size=11)
                ).pack(anchor="w", pady=(0, 3))
                entry = ctk.CTkEntry(
                    row, height=34, corner_radius=8,
                    fg_color=T.BG, border_color=T.BORDER, text_color=T.TEXT
                )
                value = ind_cfg.get(key, default)
                entry.insert(0, str(value))
                entry.pack(fill="x")
                self._calc_entries[key] = entry
                self._calc_param_types[key] = float if isinstance(default, float) else int
        else:
            ctk.CTkLabel(
                self._calc_frame, text="No parameters", anchor="w",
                text_color=T.TEXT_DIM, font=ctk.CTkFont(size=11)
            ).pack(anchor="w")

        # ── Alert thresholds (right column) ───────────────────────────
        for w in self._threshold_frame.winfo_children():
            w.destroy()
        self._threshold_entries = {}

        fields = THRESHOLD_FIELDS.get(ind_type, GENERIC_THRESHOLD_FIELDS)
        for key, label in fields:
            row = ctk.CTkFrame(self._threshold_frame, fg_color="transparent")
            row.pack(fill="x", pady=5)
            ctk.CTkLabel(
                row, text=label, anchor="w",
                text_color=T.TEXT_MUTED, font=ctk.CTkFont(size=11)
            ).pack(anchor="w", pady=(0, 3))
            entry = ctk.CTkEntry(
                row, height=34, corner_radius=8,
                fg_color=T.BG, border_color=T.BORDER,
                text_color=T.TEXT, placeholder_text_color=T.TEXT_MUTED,
                placeholder_text="None"
            )
            val = ind_cfg.get(key)
            if val is not None:
                entry.insert(0, str(val))
            entry.pack(fill="x")
            self._threshold_entries[key] = entry

        if ind_type == "MACD":
            self._macd_note.pack(anchor="w", pady=(10, 0))
        if ind_type == "KDJ":
            self._kdj_note.pack(anchor="w", pady=(10, 0))

    # ------------------------------------------------------------------
    # Active indicators list
    # ------------------------------------------------------------------
    def on_show(self):
        self._refresh_indicator_list()

    def _refresh_indicator_list(self):
        for w in self._ind_list_frame.winfo_children():
            w.destroy()
        settings = load_settings()
        for ind in settings.get("indicators", []):
            item = ctk.CTkFrame(
                self._ind_list_frame, fg_color=T.BG,
                corner_radius=8, border_width=1, border_color=T.BORDER
            )
            item.pack(fill="x", pady=3)

            var = ctk.BooleanVar(value=ind.get("enabled", True))
            cb = ctk.CTkCheckBox(
                item, text=ind["type"], variable=var,
                text_color=T.TEXT, font=ctk.CTkFont(size=13),
                fg_color=T.ACCENT, hover_color=T.ACCENT,
                border_color=T.BORDER, checkmark_color="#000000",
                command=lambda t=ind["type"], v=var: self._toggle_indicator(t, v.get())
            )
            cb.pack(side="left", padx=10, pady=10)

            ctk.CTkButton(
                item, text="✕", width=24, height=24, corner_radius=6,
                fg_color="transparent", hover_color=T.DANGER,
                text_color=T.TEXT_MUTED, font=ctk.CTkFont(size=11),
                command=lambda t=ind["type"]: self._remove_indicator(t)
            ).pack(side="right", padx=6)

    def _remove_indicator(self, ind_type: str):
        settings = load_settings()
        settings["indicators"] = [i for i in settings.get("indicators", []) if i["type"] != ind_type]
        save_settings(settings)
        self._update_dropdown()
        # If the removed indicator is currently displayed, switch to first available
        if self._current_ind == ind_type:
            remaining = _sorted_indicator_types()
            if remaining:
                self._load_indicator(remaining[0])
        self._refresh_indicator_list()

    def _toggle_indicator(self, ind_type: str, enabled: bool):
        settings = load_settings()
        for ind in settings.get("indicators", []):
            if ind["type"] == ind_type:
                ind["enabled"] = enabled
        save_settings(settings)

    def _update_dropdown(self):
        self._dropdown.configure(values=_sorted_indicator_types())

    # ------------------------------------------------------------------
    # Save (calc params + thresholds together)
    # ------------------------------------------------------------------
    def _on_save(self):
        ind_type = self._current_ind
        settings = load_settings()
        indicators = settings.get("indicators", [])
        existing = next((i for i in indicators if i["type"] == ind_type), None)

        if existing is None:
            existing = INDICATOR_DEFAULTS.get(
                ind_type,
                {"type": ind_type, "enabled": True}
            ).copy()
            indicators.append(existing)

        try:
            for key, entry in self._calc_entries.items():
                val = entry.get().strip()
                t = self._calc_param_types.get(key, int)
                existing[key] = t(val) if val else (0.0 if t is float else 0)
        except ValueError:
            self._lbl_msg.configure(text="Invalid value in calculation parameters.", text_color=T.DANGER)
            return

        try:
            for key, entry in self._threshold_entries.items():
                val = entry.get().strip()
                existing[key] = float(val) if val else None
        except ValueError:
            self._lbl_msg.configure(text="Invalid value in threshold fields.", text_color=T.DANGER)
            return

        existing["enabled"] = True
        settings["indicators"] = indicators
        save_settings(settings)
        self._lbl_msg.configure(text=f"{ind_type} saved.", text_color=T.SUCCESS)
        self._refresh_indicator_list()

    def _on_reset_defaults(self):
        ind_type = self._current_ind
        defaults = INDICATOR_DEFAULTS.get(ind_type)

        if defaults is None:
            # Build defaults from TA-Lib for indicators not in INDICATOR_DEFAULTS
            raw = _get_ta_calc_params(ind_type)
            defaults = {"type": ind_type, "enabled": True, "buy_threshold": None, "sell_threshold": None}
            defaults.update({k: d for k, d in raw})

        # Re-fill calc param entries
        for key, entry in self._calc_entries.items():
            entry.delete(0, "end")
            val = defaults.get(key)
            if val is not None:
                entry.insert(0, str(val))

        # Re-fill threshold entries
        for key, entry in self._threshold_entries.items():
            entry.delete(0, "end")
            val = defaults.get(key)
            if val is not None:
                entry.insert(0, str(val))

        self._lbl_msg.configure(text="Defaults restored — click Save to apply.", text_color=T.WARNING)
