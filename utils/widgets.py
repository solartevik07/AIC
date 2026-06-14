"""
Reusable UI components.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
from utils.theme import *
try:
    from tkcalendar import DateEntry
    HAS_CAL = True
except ImportError:
    HAS_CAL = False


def make_table(parent, columns: list[tuple[str, str, int]], height=18) -> ttk.Treeview:
    """columns = [(col_id, heading, width), ...]"""
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Z.Treeview",
                    background=SURFACE,
                    foreground=TEXT,
                    fieldbackground=SURFACE,
                    rowheight=ROW_HEIGHT,
                    font=("Segoe UI", 11),
                    borderwidth=0)
    style.configure("Z.Treeview.Heading",
                    background=PRIMARY_DARK,
                    foreground=SURFACE,
                    font=("Segoe UI", 11, "bold"),
                    relief="flat")
    style.map("Z.Treeview",
              background=[("selected", PRIMARY)],
              foreground=[("selected", TEXT)])
    style.map("Z.Treeview.Heading",
              background=[("active", PRIMARY)])

    col_ids = [c[0] for c in columns]
    headings = {c[0]: c[1] for c in columns}
    tree = ttk.Treeview(parent, columns=col_ids, show="headings",
                        style="Z.Treeview", height=height)

    sort_state = {"col": None, "reverse": False}

    def sort_by(col):
        items = [(tree.set(k, col), k) for k in tree.get_children("")]
        def sort_key(x):
            try:
                return (0, float(x[0]))
            except (ValueError, TypeError):
                return (1, str(x[0]).lower())
        rev = sort_state["reverse"] if sort_state["col"] == col else False
        items.sort(key=sort_key, reverse=rev)
        for i, (_, k) in enumerate(items):
            tree.move(k, "", i)
        for c in col_ids:
            tree.heading(c, text=headings[c])
        arrow = " ↑" if not rev else " ↓"
        tree.heading(col, text=headings[col] + arrow)
        sort_state["col"] = col
        sort_state["reverse"] = not rev

    for cid, heading, w in columns:
        tree.heading(cid, text=heading, command=lambda c=cid: sort_by(c))
        tree.column(cid, width=w, minwidth=40, anchor="w")

    tree.tag_configure("promo", background=PROMO_BG, foreground=PROMO_FG)
    tree.tag_configure("odd", background=SURFACE2)
    tree.tag_configure("even", background=SURFACE)
    return tree


def add_scrollbars(parent, tree: ttk.Treeview) -> ttk.Treeview:
    vsb = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
    hsb = ttk.Scrollbar(parent, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")
    parent.grid_rowconfigure(0, weight=1)
    parent.grid_columnconfigure(0, weight=1)
    return tree


def fill_table(tree: ttk.Treeview, rows):
    tree.delete(*tree.get_children())
    for i, row in enumerate(rows):
        vals = list(row) if not hasattr(row, "keys") else [row[k] for k in row.keys()]
        tag = "even" if i % 2 == 0 else "odd"
        if "promotional_product" in (row.keys() if hasattr(row, "keys") else []):
            if row["promotional_product"]:
                tag = "promo"
        tree.insert("", "end", values=vals, tags=(tag,))


class FormDialog(ctk.CTkToplevel):
    """
    Modal dialog that renders a form from a field spec list.
    fields = [
      {"key": "id", "label": "ID", "type": "entry", "required": True},
      {"key": "role", "label": "Посада", "type": "combo", "values": ["Менеджер","Касир"]},
      {"key": "promo", "label": "Акційний", "type": "check"},
      {"key": "date", "label": "Дата", "type": "date"},
    ]
    """

    def __init__(self, parent, title: str, fields: list[dict], on_save, initial: dict = None):
        super().__init__(parent)
        self.title(title)
        self.resizable(True, True)
        self.configure(fg_color=SURFACE)
        self.grab_set()
        self.geometry("560x500")

        self._fields = fields
        self._on_save = on_save
        self._vars: dict[str, tk.Variable] = {}
        self._widgets: dict[str, tk.Widget] = {}

        ctk.CTkLabel(self, text=title, font=FONT_LG,
                     text_color=ACCENT_LIGHT).pack(pady=(18, 6), padx=24)

        scroll = ctk.CTkScrollableFrame(self, fg_color=SURFACE,
                                        scrollbar_button_color=PRIMARY)
        scroll.pack(fill="both", expand=True, padx=18, pady=6)

        for f in fields:
            row = ctk.CTkFrame(scroll, fg_color="transparent")
            row.pack(fill="x", pady=4)
            ctk.CTkLabel(row, text=f["label"], width=180,
                         anchor="w", text_color=TEXT_DIM,
                         font=FONT_SM).pack(side="left")

            ftype = f.get("type", "entry")
            key = f["key"]
            iv = (initial or {}).get(key, "")

            def _val_alpha(s):  # block digits
                return not any(c.isdigit() for c in s)
            def _val_number(s):  # digits, dot, minus only
                return all(c in "0123456789.-" for c in s)

            vcmd_alpha = (self.register(_val_alpha), "%S")
            vcmd_number = (self.register(_val_number), "%S")

            if ftype == "entry":
                var = tk.StringVar(value=str(iv) if iv else "")
                w = ctk.CTkEntry(row, textvariable=var, width=320,
                                 fg_color=SURFACE2, border_color=PRIMARY,
                                 text_color=TEXT)
                if f.get("readonly"):
                    w.configure(state="disabled")
                elif f.get("alpha"):
                    w.configure(validate="key", validatecommand=vcmd_alpha)
                w.pack(side="left", padx=(8, 0))
                self._vars[key] = var

            elif ftype == "combo":
                var = tk.StringVar(value=str(iv) if iv else "")
                vals = f.get("values", [])
                cb = ctk.CTkComboBox(row, values=vals, width=320,
                                     fg_color=SURFACE2, border_color=PRIMARY,
                                     button_color=PRIMARY,
                                     dropdown_fg_color=SURFACE2,
                                     text_color=TEXT,
                                     state="readonly")
                cb.set(str(iv) if iv else (vals[0] if vals else ""))
                cb.pack(side="left", padx=(8, 0))
                self._vars[key] = var
                self._widgets[key] = cb

            elif ftype == "check":
                var = tk.BooleanVar(value=bool(iv))
                cb = ctk.CTkCheckBox(row, text="", variable=var,
                                     fg_color=PRIMARY, hover_color=ACCENT)
                cb.pack(side="left", padx=(8, 0))
                self._vars[key] = var

            elif ftype == "date":
                date_val = str(iv)[:10] if iv else ""
                if HAS_CAL:
                    import datetime
                    try:
                        parsed = datetime.date.fromisoformat(date_val) if date_val else datetime.date.today()
                    except ValueError:
                        parsed = datetime.date.today()
                    de = DateEntry(row, width=18,
                                   year=parsed.year, month=parsed.month, day=parsed.day,
                                   date_pattern="yyyy-mm-dd",
                                   background=PRIMARY_DARK, foreground=TEXT,
                                   selectbackground=PRIMARY, selectforeground=TEXT,
                                   headersbackground=PRIMARY_DARK, headersforeground=ACCENT_LIGHT,
                                   weekendbackground=SURFACE2, weekendforeground=TEXT,
                                   othermonthforeground=TEXT_DIM,
                                   normalbackground=SURFACE2, normalforeground=TEXT,
                                   font=("Segoe UI", 11))
                    de.pack(side="left", padx=(8, 0))
                    self._widgets[key] = de
                    var = tk.StringVar(value=date_val)
                    self._vars[key] = var
                else:
                    var = tk.StringVar(value=date_val)
                    e = ctk.CTkEntry(row, textvariable=var, width=200,
                                     placeholder_text="РРРР-ММ-ДД",
                                     fg_color=SURFACE2, border_color=PRIMARY,
                                     text_color=TEXT)
                    e.pack(side="left", padx=(8, 0))
                    self._vars[key] = var

            elif ftype == "number":
                var = tk.StringVar(value=str(iv) if iv else "0")
                e = ctk.CTkEntry(row, textvariable=var, width=320,
                                 fg_color=SURFACE2, border_color=PRIMARY,
                                 text_color=TEXT,
                                 validate="key", validatecommand=vcmd_number)
                e.pack(side="left", padx=(8, 0))
                self._vars[key] = var

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=18, pady=(6, 18))
        ctk.CTkButton(btn_row, text="Скасувати", fg_color=SURFACE2,
                      hover_color=SURFACE, text_color=TEXT_DIM,
                      command=self.destroy, width=120).pack(side="right", padx=4)
        ctk.CTkButton(btn_row, text="Зберегти", fg_color=PRIMARY,
                      hover_color=PRIMARY_DARK, text_color=TEXT,
                      command=self._save, width=120).pack(side="right", padx=4)

        self.after(50, self._center)

    def _center(self):
        self.update_idletasks()
        pw = self.master.winfo_rootx() + self.master.winfo_width() // 2
        ph = self.master.winfo_rooty() + self.master.winfo_height() // 2
        w, h = self.winfo_width(), self.winfo_height()
        self.geometry(f"+{pw - w//2}+{ph - h//2}")

    def _save(self):
        data = {}
        for f in self._fields:
            if f.get("readonly"):
                continue
            key = f["key"]
            # CTkComboBox doesn't always update StringVar, read from widget directly
            if key in self._widgets:
                v = self._widgets[key].get()
            else:
                v = self._vars[key].get()
            if f.get("required") and not str(v).strip():
                messagebox.showerror("Помилка", f"Поле «{f['label']}» є обов'язковим")
                return
            data[key] = v
        try:
            self._on_save(data)
            self.destroy()
        except Exception as e:
            messagebox.showerror("Помилка збереження", str(e))


def confirm_delete(parent, name: str = "") -> bool:
    msg = f"Видалити «{name}»?" if name else "Підтвердіть видалення."
    return messagebox.askyesno("Підтвердження", msg, parent=parent)


def section_header(parent, text: str) -> ctk.CTkLabel:
    return ctk.CTkLabel(parent, text=text, font=FONT_LG,
                        text_color=ACCENT_LIGHT, anchor="w")


def search_bar(parent, on_change, placeholder="Пошук...") -> ctk.CTkEntry:
    e = ctk.CTkEntry(parent, placeholder_text=placeholder,
                     placeholder_text_color=TEXT_DIM,
                     width=280, fg_color=SURFACE2, border_color=PRIMARY,
                     text_color=TEXT)
    e.bind("<KeyRelease>", lambda _: on_change(e.get()))
    return e


def btn_add(parent, cmd):
    return ctk.CTkButton(parent, text="＋ Додати", fg_color=PRIMARY,
                         hover_color=PRIMARY_DARK, command=cmd, width=110)

def btn_edit(parent, cmd):
    return ctk.CTkButton(parent, text="✎ Редагувати", fg_color=SURFACE2,
                         hover_color=SURFACE, text_color=ACCENT_LIGHT,
                         border_color=PRIMARY, border_width=1,
                         command=cmd, width=130)

def btn_delete(parent, cmd):
    return ctk.CTkButton(parent, text="✕ Видалити", fg_color=DANGER,
                         hover_color="#CC2E25", command=cmd, width=110)

def btn_report(parent, cmd):
    return ctk.CTkButton(parent, text="🖨 Звіт", fg_color=SURFACE2,
                         hover_color=SURFACE, text_color=TEXT_DIM,
                         border_color=ACCENT_LIGHT, border_width=1,
                         command=cmd, width=100)

def btn_filter(parent, cmd, label="Фільтр"):
    return ctk.CTkButton(parent, text=f"⚙ {label}", fg_color=SURFACE2,
                         hover_color=SURFACE, text_color=TEXT_DIM,
                         border_color=PRIMARY, border_width=1,
                         command=cmd, width=110)
