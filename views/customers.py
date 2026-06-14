"""
Customer Cards tab - available to both manager and cashier.
"""
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

import db.database as DB
from utils.theme import *
from utils.widgets import *
from utils.reports import generate_report


COLUMNS = [
    ("card",    "№ Карти",      130),
    ("surname", "Прізвище",     120),
    ("name",    "Ім'я",         100),
    ("patron",  "По батькові",  120),
    ("phone",   "Телефон",      130),
    ("city",    "Місто",         80),
    ("street",  "Вулиця",       160),
    ("zip",     "Індекс",        70),
    ("pct",     "Знижка %",      80),
]


class CustomerCardsView(ctk.CTkFrame):
    def __init__(self, parent, current_user):
        super().__init__(parent, fg_color="transparent")
        self.user = current_user
        self.is_manager = current_user["empl_role"] == "Менеджер"
        self._build()
        self.refresh()

    def _build(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=PAD, pady=(PAD, 4))
        section_header(top, "💳  Карти клієнтів").pack(side="left")

        # percent filter
        self._pct_var = tk.StringVar(value="Всі")
        pcts = ["Всі"] + sorted(set(
            str(r["percent"]) for r in DB.fetchall("SELECT DISTINCT percent FROM Customer_Card")))
        ctk.CTkComboBox(top, variable=self._pct_var, values=pcts, width=120,
                        fg_color=SURFACE2, border_color=PRIMARY, text_color=TEXT,
                        button_color=PRIMARY, dropdown_fg_color=SURFACE2,
                        command=lambda _: self.refresh()).pack(side="right", padx=4)
        ctk.CTkLabel(top, text="Знижка %:", text_color=TEXT_DIM,
                     font=FONT_SM).pack(side="right", padx=(8,2))
        search_bar(top, self._on_search, "Пошук за прізвищем...").pack(side="right", padx=4)

        acts = ctk.CTkFrame(self, fg_color="transparent")
        acts.pack(fill="x", padx=PAD, pady=2)
        # Both can add/edit customer cards
        btn_add(acts,    self._add).pack(side="left", padx=2)
        btn_edit(acts,   self._edit).pack(side="left", padx=2)
        if self.is_manager:
            btn_delete(acts, self._delete).pack(side="left", padx=2)
            btn_report(acts, self._report).pack(side="left", padx=2)

        tbl_frame = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=CORNER)
        tbl_frame.pack(fill="both", expand=True, padx=PAD, pady=PAD)
        self.tree = make_table(tbl_frame, COLUMNS)
        add_scrollbars(tbl_frame, self.tree)
        self._search_str = ""

    def _on_search(self, s): self._search_str = s.lower(); self.refresh()

    def refresh(self):
        pct = self._pct_var.get()
        if pct == "Всі":
            rows = DB.fetchall(
                "SELECT card_number,cust_surname,cust_name,cust_patronymic,"
                "phone_number,city,street,zip_code,percent "
                "FROM Customer_Card ORDER BY CAST(SUBSTR(card_number,3) AS INT) ASC")
        else:
            rows = DB.fetchall(
                "SELECT card_number,cust_surname,cust_name,cust_patronymic,"
                "phone_number,city,street,zip_code,percent "
                "FROM Customer_Card WHERE percent=? ORDER BY CAST(SUBSTR(card_number,3) AS INT) ASC", (int(pct),))
        if self._search_str:
            rows = [r for r in rows if self._search_str in r["cust_surname"].lower()]
        fill_table(self.tree, rows)

    def _selected_card(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Увага","Оберіть рядок",parent=self); return None
        return self.tree.item(sel[0])["values"][0]

    def _fields(self, edit=False):
        return [
            {"key":"card_number",    "label":"Номер карти",    "type":"entry","required":True,"readonly":edit},
            {"key":"cust_surname",   "label":"Прізвище",       "type":"entry","required":True,"alpha":True},
            {"key":"cust_name",      "label":"Ім'я",           "type":"entry","required":True,"alpha":True},
            {"key":"cust_patronymic","label":"По батькові",    "type":"entry","alpha":True},
            {"key":"phone_number",   "label":"Телефон",        "type":"entry","required":True},
            {"key":"city",           "label":"Місто",          "type":"entry","alpha":True},
            {"key":"street",         "label":"Вулиця",         "type":"entry"},
            {"key":"zip_code",       "label":"Індекс",         "type":"entry"},
            {"key":"percent",        "label":"Знижка %",       "type":"combo",
             "values":["1","5","10","15","20"], "required":True},
        ]

    def _add(self):
        FormDialog(self,"Нова карта клієнта",self._fields(),
                   on_save=self._save_new,
                   initial={"card_number": DB.next_card_number()})

    def _save_new(self, data):
        if len(data["phone_number"]) > 13:
            raise ValueError("Телефон не може перевищувати 13 символів")
        if int(data["percent"]) < 0:
            raise ValueError("Відсоток не може бути від'ємним")
        DB.execute("INSERT INTO Customer_Card VALUES (?,?,?,?,?,?,?,?,?)",
                   (data["card_number"], data["cust_surname"], data["cust_name"],
                    data.get("cust_patronymic") or None, data["phone_number"],
                    data.get("city") or None, data.get("street") or None,
                    data.get("zip_code") or None, int(data["percent"])))
        self.refresh()

    def _edit(self):
        card = self._selected_card()
        if card is None: return
        row = DB.fetchone("SELECT * FROM Customer_Card WHERE card_number=?",(card,))
        init = {k: (str(row[k]) if row[k] is not None else "") for k in row.keys()}
        FormDialog(self,"Редагувати картку клієнта",self._fields(edit=True),
                   on_save=lambda d: self._save_edit(card,d), initial=init)

    def _save_edit(self, card, data):
        if len(data["phone_number"]) > 13:
            raise ValueError("Телефон не може перевищувати 13 символів")
        DB.execute(
            "UPDATE Customer_Card SET cust_surname=?,cust_name=?,cust_patronymic=?,"
            "phone_number=?,city=?,street=?,zip_code=?,percent=? WHERE card_number=?",
            (data["cust_surname"], data["cust_name"],
             data.get("cust_patronymic") or None, data["phone_number"],
             data.get("city") or None, data.get("street") or None,
             data.get("zip_code") or None, int(data["percent"]), card))
        self.refresh()

    def _delete(self):
        card = self._selected_card()
        if card is None: return
        if confirm_delete(self, card):
            try: DB.execute("DELETE FROM Customer_Card WHERE card_number=?",(card,)); self.refresh()
            except Exception as e: messagebox.showerror("Помилка",str(e),parent=self)

    def _report(self):
        rows = DB.fetchall(
            "SELECT card_number,cust_surname,cust_name,cust_patronymic,"
            "phone_number,city,percent FROM Customer_Card ORDER BY CAST(SUBSTR(card_number,3) AS INT) ASC")
        generate_report("Список карток клієнтів",
                        ["Карта","Прізвище","Ім'я","По батькові",
                         "Телефон","Місто","Знижка %"], rows, self)
