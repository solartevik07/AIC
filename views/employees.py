"""
Employees tab - manager only.
"""
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from datetime import datetime, date

import db.database as DB
from utils.theme import *
from utils.widgets import *
from utils.reports import generate_report


COLUMNS = [
    ("id",        "ID",           70),
    ("surname",   "Прізвище",    130),
    ("name",      "Ім'я",        100),
    ("patron",    "По батькові", 120),
    ("role",      "Посада",       90),
    ("salary",    "Зарплата",     90),
    ("birth",     "Народження",  110),
    ("start",     "Початок роб.",110),
    ("phone",     "Телефон",     130),
    ("city",      "Місто",        80),
    ("street",    "Вулиця",      160),
    ("zip",       "Індекс",       70),
]


class EmployeesView(ctk.CTkFrame):
    def __init__(self, parent, current_user):
        super().__init__(parent, fg_color="transparent")
        self.user = current_user
        self._build()
        self.refresh()

    def _build(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=PAD, pady=(PAD, 4))
        section_header(top, "👤  Працівники").pack(side="left")
        search_bar(top, self._on_search, "Пошук за прізвищем або ім'ям...").pack(side="right", padx=4)

        # фільтр по ролі
        self._only_cashiers = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(top, text="Тільки касири",
                        variable=self._only_cashiers,
                        fg_color=PRIMARY, hover_color=ACCENT,
                        command=self.refresh).pack(side="right", padx=8)

        acts = ctk.CTkFrame(self, fg_color="transparent")
        acts.pack(fill="x", padx=PAD, pady=2)
        btn_add(acts, self._add).pack(side="left", padx=2)
        btn_edit(acts, self._edit).pack(side="left", padx=2)
        btn_delete(acts, self._delete).pack(side="left", padx=2)
        btn_report(acts, self._report).pack(side="left", padx=2)

        tbl_frame = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=CORNER)
        tbl_frame.pack(fill="both", expand=True, padx=PAD, pady=PAD)
        self.tree = make_table(tbl_frame, COLUMNS)
        add_scrollbars(tbl_frame, self.tree)
        self._search_str = ""

    def _on_search(self, s: str):
        self._search_str = s.lower()
        self.refresh()

    def refresh(self):
        role_filter = "AND empl_role='Касир'" if self._only_cashiers.get() else ""
        rows = DB.fetchall(
            f"SELECT id_employee,empl_surname,empl_name,empl_patronymic,"
            f"empl_role,salary,date_of_birth,date_of_start,"
            f"phone_number,city,street,zip_code FROM Employee "
            f"WHERE 1=1 {role_filter} ORDER BY CAST(SUBSTR(id_employee,2) AS INT) ASC")
        if self._search_str:
            rows = [r for r in rows
                    if self._search_str in r["empl_surname"].lower()
                    or self._search_str in r["empl_name"].lower()]
        fill_table(self.tree, rows)

    def _selected_id(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Увага", "Оберіть рядок", parent=self)
            return None
        return self.tree.item(sel[0])["values"][0]

    def _fields(self, edit=False, initial=None):
        return [
            {"key":"id_employee",   "label":"ID працівника",   "type":"entry",
             "required":True, "readonly": edit},
            {"key":"empl_surname",  "label":"Прізвище",        "type":"entry", "required":True, "alpha":True},
            {"key":"empl_name",     "label":"Ім'я",            "type":"entry", "required":True, "alpha":True},
            {"key":"empl_patronymic","label":"По батькові",    "type":"entry", "alpha":True},
            {"key":"empl_role",     "label":"Посада",          "type":"combo",
             "values":["Менеджер","Касир"], "required":True},
            {"key":"salary",        "label":"Зарплата",        "type":"number", "required":True},
            {"key":"date_of_birth", "label":"Дата народження", "type":"date",   "required":True},
            {"key":"date_of_start", "label":"Дата початку роб.","type":"date",  "required":True},
            {"key":"phone_number",  "label":"Телефон",         "type":"entry",  "required":True},
            {"key":"city",          "label":"Місто",           "type":"entry",  "required":True, "alpha":True},
            {"key":"street",        "label":"Вулиця",          "type":"entry",  "required":True},
            {"key":"zip_code",      "label":"Індекс",          "type":"entry",  "required":True},
        ]

    def _add(self):
        suggested_id = DB.next_employee_id()
        FormDialog(self, "Новий працівник", self._fields(),
                   on_save=self._save_new,
                   initial={"id_employee": suggested_id})

    def _save_new(self, data):
        # Validate age >= 18
        try:
            bd = datetime.strptime(data["date_of_birth"], "%Y-%m-%d").date()
            if (date.today() - bd).days < 18 * 365:
                raise ValueError("Вік працівника не може бути менше 18 років")
        except ValueError as e:
            if "18" in str(e):
                raise
        if len(data["phone_number"]) > 13:
            raise ValueError("Телефон не може перевищувати 13 символів")
        if float(data["salary"]) < 0:
            raise ValueError("Зарплата не може бути від'ємною")

        DB.execute(
            "INSERT INTO Employee VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (data["id_employee"], data["empl_surname"], data["empl_name"],
             data.get("empl_patronymic") or None, data["empl_role"],
             float(data["salary"]),
             data["date_of_birth"] + " 00:00:00",
             data["date_of_start"] + " 00:00:00",
             data["phone_number"], data["city"], data["street"], data["zip_code"])
        )
        # Create default login
        import hashlib
        ph = hashlib.sha256(data["id_employee"].lower().encode()).hexdigest()
        DB.execute("INSERT OR IGNORE INTO Auth VALUES (?,?)",
                   (data["id_employee"], ph))
        self.refresh()

    def _edit(self):
        eid = self._selected_id()
        if not eid:
            return
        row = DB.fetchone("SELECT * FROM Employee WHERE id_employee=?", (eid,))
        if not row:
            return
        init = {
            "id_employee":    row["id_employee"],
            "empl_surname":   row["empl_surname"],
            "empl_name":      row["empl_name"],
            "empl_patronymic":row["empl_patronymic"] or "",
            "empl_role":      row["empl_role"],
            "salary":         str(row["salary"]),
            "date_of_birth":  str(row["date_of_birth"])[:10],
            "date_of_start":  str(row["date_of_start"])[:10],
            "phone_number":   row["phone_number"],
            "city":           row["city"],
            "street":         row["street"],
            "zip_code":       row["zip_code"],
        }
        FormDialog(self, "Редагувати працівника", self._fields(edit=True, initial=init),
                   on_save=lambda d: self._save_edit(eid, d), initial=init)

    def _save_edit(self, eid, data):
        if len(data["phone_number"]) > 13:
            raise ValueError("Телефон не може перевищувати 13 символів")
        DB.execute(
            "UPDATE Employee SET empl_surname=?,empl_name=?,empl_patronymic=?,"
            "empl_role=?,salary=?,date_of_birth=?,date_of_start=?,"
            "phone_number=?,city=?,street=?,zip_code=? WHERE id_employee=?",
            (data["empl_surname"], data["empl_name"],
             data.get("empl_patronymic") or None, data["empl_role"],
             float(data["salary"]),
             data["date_of_birth"] + " 00:00:00",
             data["date_of_start"] + " 00:00:00",
             data["phone_number"], data["city"], data["street"],
             data["zip_code"], eid)
        )
        self.refresh()

    def _delete(self):
        eid = self._selected_id()
        if not eid:
            return
        if eid == self.user["id_employee"]:
            messagebox.showerror("Помилка", "Не можна видалити свій власний акаунт")
            return
        if confirm_delete(self, eid):
            checks = DB.fetchone(
                "SELECT COUNT(*) as n FROM [Check] WHERE id_employee=?", (eid,))
            if checks and checks["n"] > 0:
                messagebox.showerror(
                    "Неможливо видалити",
                    f"Працівник {eid} має {checks['n']} чек(ів) у системі.\n"
                    "Видалення заборонено - спочатку видаліть пов'язані чеки.",
                    parent=self)
                return
            try:
                DB.execute("DELETE FROM Auth WHERE id_employee=?", (eid,))
                DB.execute("DELETE FROM Employee WHERE id_employee=?", (eid,))
                self.refresh()
            except Exception as e:
                messagebox.showerror("Помилка", str(e), parent=self)

    def _report(self):
        rows = DB.fetchall(
            "SELECT id_employee,empl_surname,empl_name,empl_patronymic,"
            "empl_role,salary,phone_number,city,street,zip_code "
            "FROM Employee ORDER BY CAST(SUBSTR(id_employee,2) AS INT) ASC")
        generate_report("Список працівників",
                        ["ID","Прізвище","Ім'я","По батькові",
                         "Посада","Зарплата","Телефон","Місто","Вулиця","Індекс"],
                        rows, self)
