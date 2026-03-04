import customtkinter as ctk
from ui.home_page import HomePage
from ui.stock_settings_page import StockSettingsPage
from ui.indicator_settings_page import IndicatorSettingsPage


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Stock Tracker")
        self.geometry("1200x700")
        self.minsize(900, 600)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self._build_layout()

    def _build_layout(self):
        # Left sidebar
        self.sidebar = ctk.CTkFrame(self, width=160, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        ctk.CTkLabel(self.sidebar, text="Stock\nTracker", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(24, 32))

        self._nav_buttons = {}
        nav_items = [("Home", "home"), ("Stocks", "stocks"), ("Indicators", "indicators")]
        for label, key in nav_items:
            btn = ctk.CTkButton(
                self.sidebar, text=label, width=130,
                fg_color="transparent", hover_color=("gray70", "gray30"),
                anchor="w", command=lambda k=key: self.show_page(k)
            )
            btn.pack(pady=4, padx=12)
            self._nav_buttons[key] = btn

        # Main content area
        self.content = ctk.CTkFrame(self, corner_radius=0, fg_color=("gray90", "gray15"))
        self.content.pack(side="left", fill="both", expand=True)

        self._pages = {}
        self._pages["home"] = HomePage(self.content, self)
        self._pages["stocks"] = StockSettingsPage(self.content, self)
        self._pages["indicators"] = IndicatorSettingsPage(self.content, self)

        self.show_page("home")

    def show_page(self, key: str):
        for page in self._pages.values():
            page.pack_forget()
        self._pages[key].pack(fill="both", expand=True)
        # Highlight active nav button
        for k, btn in self._nav_buttons.items():
            if k == key:
                btn.configure(fg_color=("gray75", "gray35"))
            else:
                btn.configure(fg_color="transparent")
        # Notify page it's being shown
        if hasattr(self._pages[key], "on_show"):
            self._pages[key].on_show()
