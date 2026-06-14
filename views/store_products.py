"""
Store Products tab - товари у магазині.
"""
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

import db.database as DB
from utils.theme import *
from utils.widgets import *
from utils.reports import generate_report


COLUMNS = [
    ("upc",   "UPC",          130),
    ("upc_p", "UPC акц.",     110),
    ("name",  "Назва товару", 180),
    ("price", "Ціна",          80),
    ("qty",   "К-сть",         70),
    ("promo", "Акційний",      80),
]


class StoreProductsView(ctk.CTkFrame):
    def __init__(self, parent, current_user):
        super().__init__(parent, fg_color="transparent")
        self.user = current_user
        self.is_manager = current_user["empl_role"] == "Менеджер"
        self._build()
        self.refresh()

    def _build(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=PAD, pady=(PAD, 4))
        section_header(top, "🏪  Товари у магазині").pack(side="left")

        # filters
        self._promo_var = tk.StringVar(value="Всі")
        ctk.CTkSegmentedButton(top, values=["Всі","Звичайні","Акційні"],
                               variable=self._promo_var,
                               fg_color=SURFACE2, selected_color=PRIMARY,
                               unselected_color=SURFACE2,
                               command=lambda _: self.refresh()).pack(side="right", padx=4)
        search_bar(top, self._on_search, "Пошук за назвою або UPC...").pack(side="right", padx=4)

        acts = ctk.CTkFrame(self, fg_color="transparent")
        acts.pack(fill="x", padx=PAD, pady=2)
        if self.is_manager:
            btn_add(acts,    self._add).pack(side="left", padx=2)
            btn_edit(acts,   self._edit).pack(side="left", padx=2)
            btn_delete(acts, self._delete).pack(side="left", padx=2)
            btn_report(acts, self._report).pack(side="left", padx=2)
        # UPC lookup for cashier
        ctk.CTkButton(acts, text="🔍 За UPC", fg_color=SURFACE2,
                      hover_color=SURFACE, text_color=TEXT_DIM,
                      border_color=PRIMARY, border_width=1,
                      command=self._upc_lookup, width=100).pack(side="left", padx=2)

        tbl_frame = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=CORNER)
        tbl_frame.pack(fill="both", expand=True, padx=PAD, pady=PAD)
        self.tree = make_table(tbl_frame, COLUMNS)
        add_scrollbars(tbl_frame, self.tree)
        self._search_str = ""

    def _on_search(self, s): self._search_str = s.lower(); self.refresh()

    def _base_query(self):
        promo = self._promo_var.get()
        promo_filter = ""
        if promo == "Акційні":
            promo_filter = "AND sp.promotional_product=1"
        elif promo == "Звичайні":
            promo_filter = "AND sp.promotional_product=0"
        return (
            "SELECT sp.UPC, sp.UPC_prom, p.product_name, sp.selling_price, "
            "sp.products_number, sp.promotional_product "
            "FROM Store_Product sp JOIN Product p ON sp.id_product=p.id_product "
            f"WHERE 1=1 {promo_filter} ORDER BY CAST(sp.UPC AS INT) ASC"
        )

    def refresh(self):
        rows = DB.fetchall(self._base_query())
        if self._search_str:
            rows = [r for r in rows
                    if self._search_str in r["product_name"].lower()
                    or self._search_str in r["UPC"].lower()]
        # Format for display
        display = []
        for r in rows:
            promo_str = "✓ Акція" if r["promotional_product"] else ""
            display.append((r["UPC"], r["UPC_prom"] or "", r["product_name"],
                            f"{r['selling_price']:.2f}₴",
                            r["products_number"], promo_str))
        self.tree.delete(*self.tree.get_children())
        for i, row in enumerate(display):
            tag = "promo" if row[5] else ("even" if i % 2 == 0 else "odd")
            self.tree.insert("", "end", values=row, tags=(tag,))

    def _selected_upc(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Увага","Оберіть рядок",parent=self); return None
        val = self.tree.item(sel[0])["values"][0]
        # Treeview strips leading zeros from numeric strings → look up by int value
        row = DB.fetchone(
            "SELECT UPC FROM Store_Product WHERE CAST(UPC AS INT)=CAST(? AS INT)", (val,))
        return row["UPC"] if row else str(val)

    def _product_values(self):
        rows = DB.fetchall("SELECT id_product,product_name FROM Product ORDER BY product_name")
        return [f"{r['id_product']} - {r['product_name']}" for r in rows]

    def _upc_values_for_promo(self):
        rows = DB.fetchall("SELECT UPC FROM Store_Product WHERE promotional_product=0")
        return [r["UPC"] for r in rows]

    def _fields(self, edit=False):
        return [
            {"key":"UPC",           "label":"UPC",            "type":"entry","required":True,"readonly":edit},
            {"key":"UPC_prom",      "label":"UPC акційного",  "type":"combo",
             "values":[""] + self._upc_values_for_promo()},
            {"key":"id_product",    "label":"Товар",          "type":"combo",
             "values":self._product_values(), "required":True},
            {"key":"selling_price", "label":"Ціна продажу",  "type":"number","required":True},
            {"key":"products_number","label":"Кількість",     "type":"number","required":True},
            {"key":"promotional_product","label":"Акційний",  "type":"check"},
        ]

    def _parse_prod(self, val):
        return int(str(val).split(" - ")[0])

    def _add(self):
        FormDialog(self,"Новий товар у магазині",self._fields(),
                   on_save=self._save_new)

    @staticmethod
    def _pad_upc(raw: str) -> str:
        raw = raw.strip()
        if not raw.isdigit():
            raise ValueError("UPC має містити лише цифри")
        if len(raw) > 12:
            raise ValueError(f"UPC занадто довгий ({len(raw)} цифр, максимум 12)")
        return raw.zfill(12)

    def _save_new(self, data):
        promo = bool(data.get("promotional_product"))
        price = float(data["selling_price"])
        if price < 0: raise ValueError("Ціна не може бути від'ємною")
        qty = int(data["products_number"])
        if qty < 0: raise ValueError("Кількість не може бути від'ємною")
        upc = self._pad_upc(data["UPC"])
        upc_prom = data.get("UPC_prom") or None
        if promo and upc_prom:
            # recalculate price from base
            base = DB.fetchone("SELECT selling_price FROM Store_Product WHERE UPC=?", (upc_prom,))
            if base:
                price = round(base["selling_price"] * 0.8, 2)
        DB.execute("INSERT INTO Store_Product VALUES (?,?,?,?,?,?)",
                   (upc, upc_prom,
                    self._parse_prod(data["id_product"]),
                    price, qty, 1 if promo else 0))
        self.refresh()

    def _edit(self):
        upc = self._selected_upc()
        if upc is None: return
        row = DB.fetchone("SELECT * FROM Store_Product WHERE UPC=?",(upc,))
        if row is None: return
        prod = DB.fetchone("SELECT product_name FROM Product WHERE id_product=?",(row["id_product"],))
        prod_name = prod["product_name"] if prod else str(row["id_product"])
        init = {
            "UPC":              row["UPC"],
            "UPC_prom":         row["UPC_prom"] or "",
            "id_product":       f"{row['id_product']} - {prod_name}",
            "selling_price":    str(row["selling_price"]),
            "products_number":  str(row["products_number"]),
            "promotional_product": bool(row["promotional_product"]),
        }
        FormDialog(self,"Редагувати товар у магазині",self._fields(edit=True),
                   on_save=lambda d: self._save_edit(upc,d), initial=init)

    def _save_edit(self, upc, data):
        price = float(data["selling_price"])
        qty   = int(data["products_number"])
        if price < 0: raise ValueError("Ціна не може бути від'ємною")
        if qty < 0:   raise ValueError("Кількість не може бути від'ємною")
        DB.execute(
            "UPDATE Store_Product SET UPC_prom=?,id_product=?,selling_price=?,"
            "products_number=?,promotional_product=? WHERE UPC=?",
            (data.get("UPC_prom") or None,
             self._parse_prod(data["id_product"]),
             price, qty, 1 if data.get("promotional_product") else 0, upc))
        self.refresh()

    def _delete(self):
        upc = self._selected_upc()
        if upc is None: return
        if confirm_delete(self, upc):
            try: DB.execute("DELETE FROM Store_Product WHERE UPC=?",(upc,)); self.refresh()
            except Exception as e: messagebox.showerror("Помилка",str(e),parent=self)

    def _upc_lookup(self):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Пошук за UPC")
        dlg.configure(fg_color=SURFACE)
        dlg.grab_set()
        ctk.CTkLabel(dlg,text="Введіть UPC:",text_color=TEXT_DIM,font=FONT_SM).pack(padx=20,pady=(16,4))
        var = tk.StringVar()
        e = ctk.CTkEntry(dlg,textvariable=var,width=200,fg_color=SURFACE2,
                         border_color=PRIMARY,text_color=TEXT)
        e.pack(padx=20,pady=4)
        def search():
            dlg.destroy()
            self._show_upc_info(var.get().strip())
        ctk.CTkButton(dlg,text="Знайти",fg_color=PRIMARY,
                      hover_color=PRIMARY_DARK,command=search).pack(pady=12)
        e.focus()

    def _show_upc_info(self, upc: str):
        if not upc: return
        row = DB.fetchone(
            "SELECT sp.UPC,sp.selling_price,sp.products_number,sp.promotional_product,"
            "p.product_name,p.characteristics "
            "FROM Store_Product sp JOIN Product p ON sp.id_product=p.id_product "
            "WHERE sp.UPC=?", (upc,))
        if not row:
            messagebox.showinfo("Не знайдено", f"UPC «{upc}» не знайдено", parent=self)
            return
        info = (f"UPC:             {row['UPC']}\n"
                f"Назва:           {row['product_name']}\n"
                f"Характеристики: {row['characteristics']}\n"
                f"Ціна продажу:   {row['selling_price']:.2f} ₴\n"
                f"Кількість:      {row['products_number']} од.\n"
                f"Акційний:       {'Так' if row['promotional_product'] else 'Ні'}")
        messagebox.showinfo(f"Товар: {row['product_name']}", info, parent=self)

    def _report(self):
        promo = self._promo_var.get()
        rows = DB.fetchall(
            "SELECT sp.UPC,p.product_name,sp.selling_price,sp.products_number,"
            "sp.promotional_product FROM Store_Product sp "
            "JOIN Product p ON sp.id_product=p.id_product ORDER BY CAST(sp.UPC AS INT) ASC")
        title_map = {"Всі":"Всі товари у магазині",
                     "Акційні":"Акційні товари","Звичайні":"Звичайні товари"}
        generate_report(title_map.get(promo,"Товари у магазині"),
                        ["UPC","Назва","Ціна","К-сть","Акційний"],
                        [[r["UPC"],r["product_name"],f"{r['selling_price']:.2f}₴",
                          r["products_number"],"Так" if r["promotional_product"] else "Ні"]
                         for r in rows], self)
