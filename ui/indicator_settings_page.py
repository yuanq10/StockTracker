import customtkinter as ctk
from storage.settings_manager import load_settings, save_settings

INDICATOR_TYPES = ["CCI", "MACD", "KDJ"]

# Threshold field definitions per indicator
THRESHOLD_FIELDS = {
    "CCI": [
        ("buy_threshold", "Buy threshold (lower bound, e.g. -100)"),
        ("sell_threshold", "Sell threshold (upper bound, e.g. 100)"),
    ],
    "MACD": [
        ("buy_threshold", "Upper bound — alert when histogram < this (e.g. 0.5)"),
        ("sell_threshold", "Lower bound — alert when histogram > this (e.g. -0.5)"),
    ],
    "KDJ": [
        ("buy_threshold", "Oversold threshold for J (e.g. 20) — alert when J < this"),
        ("sell_threshold", "Overbought threshold for J (e.g. 80) — alert when J > this"),
    ],
}

# Calculation params per indicator
CALC_PARAMS = {
    "CCI": [("period", "Period", 20)],
    "MACD": [("fast", "Fast EMA", 12), ("slow", "Slow EMA", 26), ("signal", "Signal EMA", 9)],
    "KDJ": [("period", "Period", 9), ("k_smooth", "K smooth", 3), ("d_smooth", "D smooth", 3)],
}

INDICATOR_DEFAULTS = {
    "CCI":  {"type": "CCI",  "enabled": True, "period": 20, "buy_threshold": -100, "sell_threshold": 100},
    "MACD": {"type": "MACD", "enabled": True, "fast": 12, "slow": 26, "signal": 9, "buy_threshold": 0.5, "sell_threshold": -0.5},
    "KDJ":  {"type": "KDJ",  "enabled": True, "period": 9, "k_smooth": 3, "d_smooth": 3, "buy_threshold": 20, "sell_threshold": 80},
}


class IndicatorSettingsPage(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, corner_radius=0, fg_color="transparent")
        self._app = app
        self._threshold_entries = {}
        self._build_ui()
        self._load_indicator("CCI")

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _build_ui(self):
        # ── Top bar ──────────────────────────────────────────────────
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(12, 0))
        ctk.CTkLabel(top, text="Indicator Settings", font=ctk.CTkFont(size=20, weight="bold")).pack(side="left")

        # ── Main area ────────────────────────────────────────────────
        mid = ctk.CTkFrame(self, fg_color="transparent")
        mid.pack(fill="both", expand=True, padx=16, pady=12)

        # Right: my indicators list
        right_panel = ctk.CTkFrame(mid, width=220)
        right_panel.pack(side="right", fill="y", padx=(8, 0))
        right_panel.pack_propagate(False)
        ctk.CTkLabel(right_panel, text="My Indicators", font=ctk.CTkFont(weight="bold")).pack(pady=(10, 4), padx=8)
        self._ind_list_frame = ctk.CTkScrollableFrame(right_panel)
        self._ind_list_frame.pack(fill="both", expand=True, padx=4, pady=4)

        # Left: config panel
        left_panel = ctk.CTkFrame(mid)
        left_panel.pack(side="left", fill="both", expand=True)

        # Dropdown
        row = ctk.CTkFrame(left_panel, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(16, 8))
        ctk.CTkLabel(row, text="Indicator:", width=100, anchor="w").pack(side="left")
        self._dropdown = ctk.CTkOptionMenu(row, values=INDICATOR_TYPES, command=self._load_indicator, width=140)
        self._dropdown.pack(side="left")

        # Dynamic threshold area
        self._threshold_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        self._threshold_frame.pack(fill="x", padx=16, pady=8)

        # MACD note (shown alongside threshold fields)
        self._macd_note = ctk.CTkLabel(
            self._threshold_frame,
            text="Crossover alerts also fire regardless of threshold.",
            text_color="gray", font=ctk.CTkFont(size=11), justify="left"
        )

        # KDJ note
        self._kdj_note = ctk.CTkLabel(
            self._threshold_frame,
            text="K/D crossover alerts also fire automatically (K above D = buy, K below D = sell).",
            text_color="gray", font=ctk.CTkFont(size=11), justify="left"
        )

        # Status message
        self._lbl_msg = ctk.CTkLabel(left_panel, text="", text_color="gray")
        self._lbl_msg.pack(padx=16, pady=4, anchor="w")

        # Bottom buttons
        btn_row = ctk.CTkFrame(left_panel, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=16, side="bottom")
        ctk.CTkButton(btn_row, text="Save", width=100, command=self._on_save).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_row, text="Advanced Settings", width=160,
                      fg_color="gray40", hover_color="gray30",
                      command=self._on_advanced).pack(side="left")

        self._refresh_indicator_list()

    # ------------------------------------------------------------------
    # Indicator dropdown → populate fields
    # ------------------------------------------------------------------
    def _load_indicator(self, ind_type: str = None):
        if ind_type is None:
            ind_type = self._dropdown.get()
        self._dropdown.set(ind_type)
        settings = load_settings()
        ind_cfg = next((i for i in settings.get("indicators", []) if i["type"] == ind_type),
                       INDICATOR_DEFAULTS[ind_type].copy())

        # Clear threshold frame widgets
        for w in self._threshold_frame.winfo_children():
            w.grid_forget()
            w.pack_forget()

        self._threshold_entries = {}
        fields = THRESHOLD_FIELDS[ind_type]

        for key, label in fields:
            row = ctk.CTkFrame(self._threshold_frame, fg_color="transparent")
            row.pack(fill="x", pady=4)
            ctk.CTkLabel(row, text=f"{label}:", width=320, anchor="w").pack(side="left")
            entry = ctk.CTkEntry(row, width=110)
            entry.insert(0, str(ind_cfg.get(key, "")))
            entry.pack(side="left")
            self._threshold_entries[key] = entry

        if ind_type == "MACD":
            self._macd_note.pack(anchor="w", pady=(2, 0))
        else:
            self._macd_note.pack_forget()

        if ind_type == "KDJ":
            self._kdj_note.pack(anchor="w", pady=(2, 0))
        else:
            self._kdj_note.pack_forget()

    # ------------------------------------------------------------------
    # Indicators list
    # ------------------------------------------------------------------
    def on_show(self):
        self._refresh_indicator_list()

    def _refresh_indicator_list(self):
        for w in self._ind_list_frame.winfo_children():
            w.destroy()
        settings = load_settings()
        for ind in settings.get("indicators", []):
            row = ctk.CTkFrame(self._ind_list_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)
            var = ctk.BooleanVar(value=ind.get("enabled", True))
            cb = ctk.CTkCheckBox(
                row, text=ind["type"], variable=var,
                command=lambda t=ind["type"], v=var: self._toggle_indicator(t, v.get())
            )
            cb.pack(side="left", padx=4)

    def _toggle_indicator(self, ind_type: str, enabled: bool):
        settings = load_settings()
        for ind in settings.get("indicators", []):
            if ind["type"] == ind_type:
                ind["enabled"] = enabled
        save_settings(settings)

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------
    def _on_save(self):
        ind_type = self._dropdown.get()
        settings = load_settings()
        indicators = settings.get("indicators", [])
        existing = next((i for i in indicators if i["type"] == ind_type), None)

        if existing is None:
            existing = INDICATOR_DEFAULTS[ind_type].copy()
            indicators.append(existing)

        # Read threshold entries
        try:
            for key, entry in self._threshold_entries.items():
                val = entry.get().strip()
                existing[key] = float(val) if val else 0
        except ValueError:
            self._lbl_msg.configure(text="Invalid number in threshold fields.", text_color="red")
            return

        existing["enabled"] = True
        settings["indicators"] = indicators
        save_settings(settings)
        self._lbl_msg.configure(text=f"{ind_type} saved.", text_color="green")
        self._refresh_indicator_list()

    # ------------------------------------------------------------------
    # Advanced settings modal
    # ------------------------------------------------------------------
    def _on_advanced(self):
        ind_type = self._dropdown.get()
        settings = load_settings()
        ind_cfg = next((i for i in settings.get("indicators", []) if i["type"] == ind_type),
                       INDICATOR_DEFAULTS[ind_type].copy())
        AdvancedModal(self, ind_type, ind_cfg, self._on_advanced_save)

    def _on_advanced_save(self, ind_type: str, new_params: dict):
        settings = load_settings()
        indicators = settings.get("indicators", [])
        existing = next((i for i in indicators if i["type"] == ind_type), None)
        if existing is None:
            existing = INDICATOR_DEFAULTS[ind_type].copy()
            indicators.append(existing)
        existing.update(new_params)
        settings["indicators"] = indicators
        save_settings(settings)
        self._lbl_msg.configure(text=f"{ind_type} calc params saved.", text_color="green")


# ------------------------------------------------------------------
# Advanced Settings Modal
# ------------------------------------------------------------------
class AdvancedModal(ctk.CTkToplevel):
    def __init__(self, parent, ind_type: str, ind_cfg: dict, on_save):
        super().__init__(parent)
        self.title(f"{ind_type} — Advanced Settings")
        self.geometry("360x260")
        self.resizable(False, False)
        self.grab_set()
        self._ind_type = ind_type
        self._on_save = on_save
        self._entries = {}

        ctk.CTkLabel(self, text=f"{ind_type} Calculation Parameters",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(16, 8), padx=16, anchor="w")

        params = CALC_PARAMS[ind_type]
        for key, label, default in params:
            row = ctk.CTkFrame(self, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=4)
            ctk.CTkLabel(row, text=f"{label}:", width=120, anchor="w").pack(side="left")
            entry = ctk.CTkEntry(row, width=100)
            entry.insert(0, str(ind_cfg.get(key, default)))
            entry.pack(side="left")
            self._entries[key] = entry

        self._lbl_err = ctk.CTkLabel(self, text="", text_color="red")
        self._lbl_err.pack(pady=4)

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(pady=8)
        ctk.CTkButton(btn_row, text="Save", width=90, command=self._save).pack(side="left", padx=4)
        ctk.CTkButton(btn_row, text="Cancel", width=90, fg_color="gray40",
                      command=self.destroy).pack(side="left", padx=4)

    def _save(self):
        new_params = {}
        try:
            for key, entry in self._entries.items():
                val = entry.get().strip()
                new_params[key] = int(val) if val else 0
        except ValueError:
            self._lbl_err.configure(text="Enter whole numbers only.")
            return
        self._on_save(self._ind_type, new_params)
        self.destroy()
