"""
Products tab (manager + cashier) and Categories tab (manager only).
"""
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

import db.database as DB
from utils.theme import *
from utils.widgets import *
from utils.reports import generate_report


class CategoriesView(ctk.CTkFrame):
    def __init__(self, parent, current_user):
        super().__init__(parent, fg_color="transparent")
        self.user = current_user
        self._build()
        self.refresh()

    def _build(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=PAD, pady=(PAD, 4))
        section_header(top, "🗂  Категорії").pack(side="left")
        search_bar(top, self._on_search, "Пошук за назвою категорії...").pack(side="right")

        acts = ctk.CTkFrame(self, fg_color="transparent")
        acts.pack(fill="x", padx=PAD, pady=2)
        btn_add(acts,    self._add).pack(side="left", padx=2)
        btn_edit(acts,   self._edit).pack(side="left", padx=2)
        btn_delete(acts, self._delete).pack(side="left", padx=2)
        btn_report(acts, self._report).pack(side="left", padx=2)

        cols = [("num","№",60),("name","Назва категорії",300)]
        tbl_frame = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=CORNER)
        tbl_frame.pack(fill="both", expand=True, padx=PAD, pady=PAD)
        self.tree = make_table(tbl_frame, cols)
        add_scrollbars(tbl_frame, self.tree)
        self._search_str = ""

    def _on_search(self, s): self._search_str = s.lower(); self.refresh()

    def refresh(self):
        rows = DB.fetchall("SELECT category_number,category_name FROM Category ORDER BY category_number ASC")
        if self._search_str:
            rows = [r for r in rows if self._search_str in r["category_name"].lower()]
        fill_table(self.tree, rows)

    def _selected_id(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Увага","Оберіть рядок",parent=self); return None
        return self.tree.item(sel[0])["values"][0]

    def _fields(self, edit=False):
        return [
            {"key":"category_number","label":"Номер категорії","type":"number","required":True,"readonly":edit},
            {"key":"category_name",  "label":"Назва",          "type":"entry", "required":True, "alpha":True},
        ]

    def _add(self):
        row = DB.fetchone("SELECT MAX(category_number) as m FROM Category")
        FormDialog(self,"Нова категорія",self._fields(),
                   on_save=self._save_new,
                   initial={"category_number": (row["m"] or 0)+1})

    def _save_new(self, data):
        DB.execute("INSERT INTO Category VALUES (?,?)",
                   (int(data["category_number"]), data["category_name"]))
        self.refresh()

    def _edit(self):
        cid = self._selected_id()
        if cid is None: return
        row = DB.fetchone("SELECT * FROM Category WHERE category_number=?",(cid,))
        FormDialog(self,"Редагувати категорію",self._fields(edit=True),
                   on_save=lambda d: self._save_edit(cid,d),
                   initial={"category_number":row["category_number"],"category_name":row["category_name"]})

    def _save_edit(self, cid, data):
        DB.execute("UPDATE Category SET category_name=? WHERE category_number=?",
                   (data["category_name"], cid))
        self.refresh()

    def _delete(self):
        cid = self._selected_id()
        if cid is None: return
        if confirm_delete(self, str(cid)):
            try: DB.execute("DELETE FROM Category WHERE category_number=?",(cid,)); self.refresh()
            except Exception as e: messagebox.showerror("Помилка",str(e),parent=self)

    def _report(self):
        rows = DB.fetchall("SELECT category_number,category_name FROM Category ORDER BY category_name")
        generate_report("Список категорій",["№ категорії","Назва"],rows,self)


class ProductsView(ctk.CTkFrame):
    def __init__(self, parent, current_user):
        super().__init__(parent, fg_color="transparent")
        self.user = current_user
        self.is_manager = current_user["empl_role"] == "Менеджер"
        self._build()
        self.refresh()

    def _build(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=PAD, pady=(PAD, 4))
        section_header(top, "📦  Товари").pack(side="left")

        # category filter
        cats = DB.fetchall("SELECT category_name FROM Category ORDER BY category_name")
        cat_names = ["Всі категорії"] + [r["category_name"] for r in cats]
        self._cat_var = tk.StringVar(value="Всі категорії")
        ctk.CTkComboBox(top, variable=self._cat_var, values=cat_names, width=200,
                        fg_color=SURFACE2, border_color=PRIMARY,
                        dropdown_fg_color=SURFACE2, text_color=TEXT,
                        button_color=PRIMARY,
                        command=lambda _: self.refresh()).pack(side="right", padx=4)
        ctk.CTkLabel(top, text="Категорія:", text_color=TEXT_DIM,
                     font=FONT_SM).pack(side="right", padx=(8,2))
        search_bar(top, self._on_search, "Пошук за назвою товару...").pack(side="right", padx=4)

        acts = ctk.CTkFrame(self, fg_color="transparent")
        acts.pack(fill="x", padx=PAD, pady=2)
        if self.is_manager:
            btn_add(acts,    self._add).pack(side="left", padx=2)
            btn_edit(acts,   self._edit).pack(side="left", padx=2)
            btn_delete(acts, self._delete).pack(side="left", padx=2)
            btn_report(acts, self._report).pack(side="left", padx=2)

        cols = [
            ("id",    "ID",           50),
            ("cat",   "Категорія",   140),
            ("name",  "Назва",       200),
            ("chars", "Характеристики",200),
        ]
        tbl_frame = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=CORNER)
        tbl_frame.pack(fill="both", expand=True, padx=PAD, pady=PAD)
        self.tree = make_table(tbl_frame, cols)
        add_scrollbars(tbl_frame, self.tree)
        self._search_str = ""

    def _on_search(self, s): self._search_str = s.lower(); self.refresh()

    def refresh(self):
        cat = self._cat_var.get()
        if cat == "Всі категорії":
            rows = DB.fetchall(
                "SELECT p.id_product,c.category_name,p.product_name,p.characteristics "
                "FROM Product p JOIN Category c ON p.category_number=c.category_number "
                "ORDER BY p.id_product ASC")
        else:
            rows = DB.fetchall(
                "SELECT p.id_product,c.category_name,p.product_name,p.characteristics "
                "FROM Product p JOIN Category c ON p.category_number=c.category_number "
                "WHERE c.category_name=? ORDER BY p.id_product ASC", (cat,))
        if self._search_str:
            rows = [r for r in rows if self._search_str in r["product_name"].lower()]
        fill_table(self.tree, rows)

    def _selected_id(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Увага","Оберіть рядок",parent=self); return None
        return self.tree.item(sel[0])["values"][0]

    def _cat_values(self):
        rows = DB.fetchall("SELECT category_number,category_name FROM Category ORDER BY category_number ASC")
        return [f"{r['category_number']} - {r['category_name']}" for r in rows]

    def _fields(self, edit=False):
        return [
            {"key":"id_product",     "label":"ID товару",      "type":"number","required":True,"readonly":edit},
            {"key":"category_number","label":"Категорія",       "type":"combo",
             "values": self._cat_values(), "required":True},
            {"key":"product_name",   "label":"Назва товару",   "type":"entry", "required":True, "alpha":True},
            {"key":"characteristics","label":"Характеристики", "type":"entry", "required":True},
        ]

    def _parse_cat(self, val):
        return int(str(val).split(" - ")[0])

    def _add(self):
        FormDialog(self,"Новий товар",self._fields(),
                   on_save=self._save_new,
                   initial={"id_product": DB.next_product_id()})

    def _save_new(self, data):
        DB.execute("INSERT INTO Product VALUES (?,?,?,?)",
                   (int(data["id_product"]), self._parse_cat(data["category_number"]),
                    data["product_name"], data["characteristics"]))
        self.refresh()

    def _edit(self):
        pid = self._selected_id()
        if pid is None: return
        row = DB.fetchone("SELECT * FROM Product WHERE id_product=?",(pid,))
        cat_name = DB.fetchone("SELECT category_name FROM Category WHERE category_number=?",
                               (row["category_number"],))["category_name"]
        init = {
            "id_product":     str(row["id_product"]),
            "category_number":f"{row['category_number']} - {cat_name}",
            "product_name":   row["product_name"],
            "characteristics":row["characteristics"],
        }
        FormDialog(self,"Редагувати товар",self._fields(edit=True),
                   on_save=lambda d: self._save_edit(pid,d), initial=init)

    def _save_edit(self, pid, data):
        DB.execute("UPDATE Product SET category_number=?,product_name=?,characteristics=? "
                   "WHERE id_product=?",
                   (self._parse_cat(data["category_number"]),
                    data["product_name"], data["characteristics"], pid))
        self.refresh()

    def _delete(self):
        pid = self._selected_id()
        if pid is None: return
        if confirm_delete(self, str(pid)):
            try: DB.execute("DELETE FROM Product WHERE id_product=?",(pid,)); self.refresh()
            except Exception as e: messagebox.showerror("Помилка",str(e),parent=self)

    def _report(self):
        rows = DB.fetchall(
            "SELECT p.id_product,c.category_name,p.product_name,p.characteristics "
            "FROM Product p JOIN Category c ON p.category_number=c.category_number "
            "ORDER BY p.id_product ASC")
        generate_report("Список товарів",
                        ["ID","Категорія","Назва","Характеристики"],rows,self)
