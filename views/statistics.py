"""
Statistics tab - manager queries: totals, product sales counts, etc.
"""
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from datetime import date

import db.database as DB
from utils.theme import *
from utils.widgets import *
from utils.reports import generate_report


class StatisticsView(ctk.CTkFrame):
    def __init__(self, parent, current_user):
        super().__init__(parent, fg_color="transparent")
        self.user = current_user
        self._build()

    def _build(self):
        section_header(self, "📊  Статистика та запити").pack(
            anchor="w", padx=PAD, pady=(PAD, 4))

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=PAD, pady=4)

        self._result_frame = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=CORNER)
        self._result_frame.pack(fill="both", expand=False, padx=PAD, pady=(4, PAD))
        self._result_cols: list = []
        self._result_rows: list = []
        self._result_title = ""

        def section(title):
            f = ctk.CTkFrame(scroll, fg_color=SURFACE2, corner_radius=CORNER)
            f.pack(fill="x", pady=6)
            ctk.CTkLabel(f, text=title, font=FONT_MD,
                         text_color=ACCENT_LIGHT, anchor="w").pack(anchor="w", padx=12, pady=(8, 4))
            return f

        s1 = section("1. Загальна сума продажів касира за період")
        r1 = ctk.CTkFrame(s1, fg_color="transparent"); r1.pack(fill="x", padx=12, pady=4)
        cashiers = DB.fetchall("SELECT id_employee,empl_surname FROM Employee WHERE empl_role='Касир'")
        c_vals = [f"{r['id_employee']} - {r['empl_surname']}" for r in cashiers]
        self._s1_cashier = tk.StringVar(value=c_vals[0] if c_vals else "")
        ctk.CTkComboBox(r1, variable=self._s1_cashier, values=c_vals, width=220,
                        fg_color=SURFACE, border_color=PRIMARY, text_color=TEXT,
                        button_color=PRIMARY, dropdown_fg_color=SURFACE2).pack(side="left", padx=4)
        today = date.today().isoformat()
        self._s1_from = tk.StringVar(value="2024-01-01")
        self._s1_to = tk.StringVar(value=today)
        ctk.CTkLabel(r1, text="з", text_color=TEXT_DIM, font=FONT_SM).pack(side="left", padx=4)
        ctk.CTkEntry(r1, textvariable=self._s1_from, width=110,
                     fg_color=SURFACE, border_color=PRIMARY, text_color=TEXT).pack(side="left", padx=2)
        ctk.CTkLabel(r1, text="по", text_color=TEXT_DIM, font=FONT_SM).pack(side="left", padx=4)
        ctk.CTkEntry(r1, textvariable=self._s1_to, width=110,
                     fg_color=SURFACE, border_color=PRIMARY, text_color=TEXT).pack(side="left", padx=2)
        ctk.CTkButton(r1, text="Порахувати", fg_color=PRIMARY, hover_color=PRIMARY_DARK,
                      width=110, command=self._q1).pack(side="left", padx=8)

        s2 = section("2. Загальна сума продажів ВСІХ касирів за період")
        r2 = ctk.CTkFrame(s2, fg_color="transparent"); r2.pack(fill="x", padx=12, pady=4)
        self._s2_from = tk.StringVar(value="2024-01-01")
        self._s2_to = tk.StringVar(value=today)
        ctk.CTkLabel(r2, text="з", text_color=TEXT_DIM, font=FONT_SM).pack(side="left", padx=4)
        ctk.CTkEntry(r2, textvariable=self._s2_from, width=110,
                     fg_color=SURFACE, border_color=PRIMARY, text_color=TEXT).pack(side="left", padx=2)
        ctk.CTkLabel(r2, text="по", text_color=TEXT_DIM, font=FONT_SM).pack(side="left", padx=4)
        ctk.CTkEntry(r2, textvariable=self._s2_to, width=110,
                     fg_color=SURFACE, border_color=PRIMARY, text_color=TEXT).pack(side="left", padx=2)
        ctk.CTkButton(r2, text="Порахувати", fg_color=PRIMARY, hover_color=PRIMARY_DARK,
                      width=110, command=self._q2).pack(side="left", padx=8)

        s3 = section("3. Кількість одиниць певного товару, проданого за період")
        r3 = ctk.CTkFrame(s3, fg_color="transparent"); r3.pack(fill="x", padx=12, pady=4)
        prods = DB.fetchall("SELECT id_product,product_name FROM Product ORDER BY product_name")
        p_vals = [f"{r['id_product']} - {r['product_name']}" for r in prods]
        self._s3_prod = tk.StringVar(value=p_vals[0] if p_vals else "")
        ctk.CTkComboBox(r3, variable=self._s3_prod, values=p_vals, width=260,
                        fg_color=SURFACE, border_color=PRIMARY, text_color=TEXT,
                        button_color=PRIMARY, dropdown_fg_color=SURFACE2).pack(side="left", padx=4)
        self._s3_from = tk.StringVar(value="2024-01-01")
        self._s3_to = tk.StringVar(value=today)
        ctk.CTkLabel(r3, text="з", text_color=TEXT_DIM, font=FONT_SM).pack(side="left", padx=4)
        ctk.CTkEntry(r3, textvariable=self._s3_from, width=110,
                     fg_color=SURFACE, border_color=PRIMARY, text_color=TEXT).pack(side="left", padx=2)
        ctk.CTkLabel(r3, text="по", text_color=TEXT_DIM, font=FONT_SM).pack(side="left", padx=4)
        ctk.CTkEntry(r3, textvariable=self._s3_to, width=110,
                     fg_color=SURFACE, border_color=PRIMARY, text_color=TEXT).pack(side="left", padx=2)
        ctk.CTkButton(r3, text="Порахувати", fg_color=PRIMARY, hover_color=PRIMARY_DARK,
                      width=110, command=self._q3).pack(side="left", padx=8)

        s4 = section("4. Знайти телефон та адресу працівника за прізвищем")
        r4 = ctk.CTkFrame(s4, fg_color="transparent"); r4.pack(fill="x", padx=12, pady=4)
        self._s4_name = tk.StringVar()
        ctk.CTkEntry(r4, textvariable=self._s4_name, width=200, placeholder_text="Прізвище...",
                     fg_color=SURFACE, border_color=PRIMARY, text_color=TEXT).pack(side="left", padx=4)
        ctk.CTkButton(r4, text="Знайти", fg_color=PRIMARY, hover_color=PRIMARY_DARK,
                      width=90, command=self._q4).pack(side="left", padx=8)

        s5 = section("5. Постійні клієнти з певним відсотком знижки")
        r5 = ctk.CTkFrame(s5, fg_color="transparent"); r5.pack(fill="x", padx=12, pady=4)
        pcts = sorted(set(str(r["percent"]) for r in
                          DB.fetchall("SELECT DISTINCT percent FROM Customer_Card")))
        self._s5_pct = tk.StringVar(value=pcts[0] if pcts else "5")
        ctk.CTkComboBox(r5, variable=self._s5_pct, values=pcts, width=100,
                        fg_color=SURFACE, border_color=PRIMARY, text_color=TEXT,
                        button_color=PRIMARY, dropdown_fg_color=SURFACE2).pack(side="left", padx=4)
        ctk.CTkButton(r5, text="Показати", fg_color=PRIMARY, hover_color=PRIMARY_DARK,
                      width=100, command=self._q5).pack(side="left", padx=8)

        self._result_frame.pack(fill="both", expand=True, padx=PAD, pady=(0, PAD))
        rf_top = ctk.CTkFrame(self._result_frame, fg_color="transparent")
        rf_top.pack(fill="x", padx=8, pady=4)
        self._res_title = ctk.CTkLabel(rf_top, text="Результат",
                                       font=FONT_MD, text_color=TEXT_DIM)
        self._res_title.pack(side="left")
        ctk.CTkButton(rf_top, text="🖨 Звіт", fg_color=SURFACE2,
                      hover_color=SURFACE, text_color=TEXT_DIM,
                      border_color=ACCENT_LIGHT, border_width=1,
                      width=90, command=self._export).pack(side="right", padx=4)

        tbl_f = ctk.CTkFrame(self._result_frame, fg_color=SURFACE2, corner_radius=CORNER)
        tbl_f.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.res_tree = make_table(tbl_f, [("x", "-", 300)], height=6)
        add_scrollbars(tbl_f, self.res_tree)

    def _show(self, title, cols, rows):
        self._result_title = title
        self._result_cols = cols
        self._result_rows = rows
        self.res_tree["columns"] = [c[0] for c in cols]
        for c in cols:
            self.res_tree.heading(c[0], text=c[1])
            self.res_tree.column(c[0], width=c[2], anchor="w")
        fill_table(self.res_tree, rows)
        self._res_title.configure(text=title)

    def _q1(self):
        cid = self._s1_cashier.get().split(" - ")[0]
        df = self._s1_from.get() + " 00:00:00"
        dt = self._s1_to.get() + " 23:59:59"
        row = DB.fetchone(
            "SELECT COALESCE(SUM(sum_total),0) as total FROM [Check] "
            "WHERE id_employee=? AND print_date BETWEEN ? AND ?", (cid, df, dt))
        self._show(f"Сума продажів касира {cid}",
                   [("total", "Загальна сума", 300)],
                   [[f"{row['total']:.2f} ₴"]])

    def _q2(self):
        df = self._s2_from.get() + " 00:00:00"
        dt = self._s2_to.get() + " 23:59:59"
        rows = DB.fetchall(
            "SELECT e.empl_surname||' '||e.empl_name as emp,"
            "COALESCE(SUM(c.sum_total),0) as total "
            "FROM Employee e LEFT JOIN [Check] c ON e.id_employee=c.id_employee "
            "AND c.print_date BETWEEN ? AND ? "
            "WHERE e.empl_role='Касир' GROUP BY e.id_employee ORDER BY total DESC",
            (df, dt))
        grand = sum(r["total"] for r in rows)
        data = [[r["emp"], f"{r['total']:.2f} ₴"] for r in rows]
        data.append(["РАЗОМ", f"{grand:.2f} ₴"])
        self._show("Сума продажів по касирах",
                   [("emp", "Касир", 280), ("total", "Сума", 200)], data)

    def _q3(self):
        pid_str = self._s3_prod.get().split(" - ")[0]
        df = self._s3_from.get() + " 00:00:00"
        dt = self._s3_to.get() + " 23:59:59"
        row = DB.fetchone(
            "SELECT COALESCE(SUM(s.product_number),0) as total "
            "FROM Sale s JOIN [Check] c ON s.check_number=c.check_number "
            "JOIN Store_Product sp ON s.UPC=sp.UPC "
            "WHERE sp.id_product=? AND c.print_date BETWEEN ? AND ?",
            (int(pid_str), df, dt))
        pname = DB.fetchone("SELECT product_name FROM Product WHERE id_product=?", (int(pid_str),))
        self._show(f"Продано «{pname['product_name']}»",
                   [("qty", "Кількість одиниць", 300)],
                   [[str(row["total"]) + " од."]])

    def _q4(self):
        surname = self._s4_name.get().strip()
        if not surname:
            messagebox.showwarning("Увага", "Введіть прізвище", parent=self); return
        rows = DB.fetchall(
            "SELECT empl_surname,empl_name,phone_number,city,street,zip_code "
            "FROM Employee WHERE empl_surname LIKE ? ORDER BY empl_surname",
            (f"%{surname}%",))
        self._show(f"Пошук за прізвищем «{surname}»",
                   [("s", "Прізвище", 120), ("n", "Ім'я", 100),
                    ("p", "Телефон", 130), ("c", "Місто", 80),
                    ("st", "Вулиця", 160), ("z", "Індекс", 70)], rows)

    def _q5(self):
        pct = int(self._s5_pct.get())
        rows = DB.fetchall(
            "SELECT cust_surname,cust_name,phone_number,percent "
            "FROM Customer_Card WHERE percent=? ORDER BY cust_surname", (pct,))
        self._show(f"Клієнти зі знижкою {pct}%",
                   [("s", "Прізвище", 160), ("n", "Ім'я", 120),
                    ("p", "Телефон", 130), ("pct", "Знижка %", 80)], rows)

    def _export(self):
        if not self._result_rows:
            messagebox.showinfo("Порожньо", "Немає даних для звіту", parent=self); return
        cols_h = [c[1] for c in self._result_cols]
        generate_report(self._result_title, cols_h, self._result_rows, self)
