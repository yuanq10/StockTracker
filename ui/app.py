import customtkinter as ctk
from ui.home_page import HomePage
from ui.stock_settings_page import StockSettingsPage
from ui.indicator_settings_page import IndicatorSettingsPage
import ui.theme as T


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Stock Tracker")
        self.geometry("1200x700")
        self.minsize(900, 600)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.configure(fg_color=T.SURFACE)
        self._build_layout()

    def _build_layout(self):
        # Pack bottom elements first so content fills remaining space

        # ── Bottom separator ──────────────────────────────────────────
        ctk.CTkFrame(self, height=1, corner_radius=0, fg_color=T.BORDER).pack(
            side="bottom", fill="x"
        )

        # ── Bottom nav bar ────────────────────────────────────────────
        nav_bar = ctk.CTkFrame(self, height=52, corner_radius=0, fg_color=T.BG)
        nav_bar.pack(side="bottom", fill="x")
        nav_bar.pack_propagate(False)

        # Even 3-column grid for nav items
        nav_bar.grid_columnconfigure(0, weight=1)
        nav_bar.grid_columnconfigure(1, weight=1)
        nav_bar.grid_columnconfigure(2, weight=1)
        nav_bar.grid_rowconfigure(0, weight=1)

        self._nav_buttons = {}
        self._nav_indicators = {}
        nav_items = [("Home", "home"), ("Stocks", "stocks"), ("Indicators", "indicators")]
        for i, (label, key) in enumerate(nav_items):
            col = ctk.CTkFrame(nav_bar, fg_color="transparent")
            col.grid(row=0, column=i, sticky="nsew")

            # Top accent bar (active indicator)
            ind = ctk.CTkFrame(col, height=2, corner_radius=0, fg_color="transparent")
            ind.pack(side="top", fill="x")

            btn = ctk.CTkButton(
                col, text=label, height=36, corner_radius=8,
                fg_color="transparent", hover_color=T.CARD,
                text_color=T.TEXT_MUTED, font=ctk.CTkFont(size=13),
                command=lambda k=key: self.show_page(k)
            )
            btn.pack(expand=True, fill="x", padx=8, pady=4)

            self._nav_buttons[key] = btn
            self._nav_indicators[key] = ind

        # ── Main content area ─────────────────────────────────────────
        self.content = ctk.CTkFrame(self, corner_radius=0, fg_color=T.SURFACE)
        self.content.pack(side="top", fill="both", expand=True)

        self._pages = {}
        self._pages["home"] = HomePage(self.content, self)
        self._pages["stocks"] = StockSettingsPage(self.content, self)
        self._pages["indicators"] = IndicatorSettingsPage(self.content, self)

        self.show_page("home")

    def show_page(self, key: str):
        for page in self._pages.values():
            page.pack_forget()
        self._pages[key].pack(fill="both", expand=True)

        for k, btn in self._nav_buttons.items():
            if k == key:
                btn.configure(fg_color=T.CARD, text_color=T.ACCENT)
                self._nav_indicators[k].configure(fg_color=T.ACCENT)
            else:
                btn.configure(fg_color="transparent", text_color=T.TEXT_MUTED)
                self._nav_indicators[k].configure(fg_color="transparent")

        if hasattr(self._pages[key], "on_show"):
            self._pages[key].on_show()
