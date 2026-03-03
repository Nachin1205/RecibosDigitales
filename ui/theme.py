import tkinter as tk
from tkinter import ttk


COLORS = {
    "bg": "#F4F6F8",
    "panel": "#FFFFFF",
    "panel_alt": "#0F172A",
    "panel_alt_soft": "#1E293B",
    "text": "#0F172A",
    "text_soft": "#475569",
    "text_on_dark": "#E2E8F0",
    "primary": "#0B6E4F",
    "primary_soft": "#D7F5EA",
    "warning": "#B45309",
    "danger": "#B91C1C",
    "success": "#166534",
    "border": "#D7DEE6",
}


def apply_theme(root: tk.Misc):
    root.configure(bg=COLORS["bg"])

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass

    style.configure(".", font=("Segoe UI", 10), foreground=COLORS["text"])
    style.configure("TFrame", background=COLORS["bg"])
    style.configure("Content.TFrame", background=COLORS["bg"])
    style.configure("Panel.TFrame", background=COLORS["panel"])
    style.configure("Sidebar.TFrame", background=COLORS["panel_alt"])
    style.configure("Topbar.TFrame", background=COLORS["panel"])
    style.configure("Card.TFrame", background=COLORS["panel"])

    style.configure("TLabel", background=COLORS["bg"], foreground=COLORS["text"])
    style.configure("Panel.TLabel", background=COLORS["panel"], foreground=COLORS["text"])
    style.configure("Sidebar.TLabel", background=COLORS["panel_alt"], foreground=COLORS["text_on_dark"])
    style.configure("Muted.TLabel", background=COLORS["panel"], foreground=COLORS["text_soft"])
    style.configure("Title.TLabel", background=COLORS["panel"], foreground=COLORS["text"], font=("Segoe UI Semibold", 14))
    style.configure("Kpi.TLabel", background=COLORS["panel"], foreground=COLORS["text"], font=("Segoe UI Semibold", 18))

    style.configure("TButton", padding=(10, 6))
    style.configure("Primary.TButton", background=COLORS["primary"], foreground="#FFFFFF", borderwidth=0, padding=(12, 7))
    style.map("Primary.TButton", background=[("active", "#0A5A42"), ("pressed", "#084A36")], foreground=[("disabled", "#E2E8F0")])

    style.configure("Secondary.TButton", background="#EEF2F6", foreground=COLORS["text"], borderwidth=1, relief="solid")
    style.map("Secondary.TButton", background=[("active", "#E2E8F0")])

    style.configure("Nav.TButton", background=COLORS["panel_alt"], foreground=COLORS["text_on_dark"], anchor="w", padding=(14, 10), borderwidth=0)
    style.map("Nav.TButton", background=[("active", COLORS["panel_alt_soft"])])
    style.configure("NavActive.TButton", background=COLORS["primary"], foreground="#FFFFFF", anchor="w", padding=(14, 10), borderwidth=0)

    style.configure("TEntry", fieldbackground="#FFFFFF", bordercolor=COLORS["border"], lightcolor=COLORS["border"], darkcolor=COLORS["border"], padding=6)
    style.configure("TCombobox", fieldbackground="#FFFFFF", padding=5)

    style.configure("TNotebook", background=COLORS["bg"], borderwidth=0)
    style.configure("TNotebook.Tab", padding=(12, 8))

    style.configure("Treeview", rowheight=26, fieldbackground="#FFFFFF", background="#FFFFFF")
    style.configure("Treeview.Heading", font=("Segoe UI Semibold", 10))


class ToastManager:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.active = []

    def show(self, title: str, message: str, level: str = "info", duration_ms: int = 3200):
        palette = {
            "info": ("#1D4ED8", "#DBEAFE"),
            "success": ("#166534", "#DCFCE7"),
            "warning": ("#B45309", "#FEF3C7"),
            "error": ("#B91C1C", "#FEE2E2"),
        }
        fg, bg = palette.get(level, palette["info"])

        toast = tk.Toplevel(self.root)
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        toast.configure(bg=bg)

        box = tk.Frame(toast, bg=bg, bd=1, relief="solid", highlightthickness=0)
        box.pack(fill="both", expand=True)

        tk.Label(box, text=title, bg=bg, fg=fg, font=("Segoe UI Semibold", 10), anchor="w").pack(fill="x", padx=10, pady=(8, 0))
        tk.Label(box, text=message, bg=bg, fg="#111827", font=("Segoe UI", 9), justify="left", anchor="w", wraplength=320).pack(fill="x", padx=10, pady=(2, 8))

        toast.update_idletasks()
        w = toast.winfo_width()
        h = toast.winfo_height()
        screen_w = toast.winfo_screenwidth()
        screen_h = toast.winfo_screenheight()
        idx = len(self.active)
        x = screen_w - w - 20
        y = screen_h - h - 50 - (idx * (h + 8))
        toast.geometry(f"{w}x{h}+{x}+{y}")

        self.active.append(toast)

        def _close(t=toast):
            if t in self.active:
                self.active.remove(t)
            try:
                t.destroy()
            except Exception:
                pass

        toast.after(duration_ms, _close)


def make_notifier(toast_manager: ToastManager):
    def _notify(level: str, title: str, message: str):
        toast_manager.show(title=title, message=message, level=level)
    return _notify
