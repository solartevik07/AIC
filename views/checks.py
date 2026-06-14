"""
Checks tab - cashier creates checks, manager views/deletes all.
"""
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from datetime import datetime, date

import db.database as DB
from utils.theme import *
from utils.widgets import *
from utils.reports import generate_report


CHECK_COLS = [
    ("num",   "Номер чеку", 120),
    ("emp",   "Касир",      160),
    ("card",  "Карта",      130),
    ("date",  "Дата",       150),
    ("total", "Сума",        90),
    ("vat",   "ПДВ",         80),
]

SALE_COLS = [
    ("upc",   "UPC",       130),
    ("name",  "Назва",     200),
    ("qty",   "К-сть",      70),
    ("price", "Ціна/од.",   90),
    ("sum",   "Сума",       90),
]


class ChecksView(ctk.CTkFrame):
    def __init__(self, parent, current_user):
        super().__init__(parent, fg_color="transparent")
        self.user = current_user
        self.is_manager = current_user["empl_role"] == "Менеджер"
        self._build()
        self.refresh()

    def _build(self):
        pane = tk.PanedWindow(self, orient="vertical",
                              bg=BG, sashwidth=6, sashrelief="flat")
        pane.pack(fill="both", expand=True)

        top_frame = ctk.CTkFrame(pane, fg_color="transparent")
        bot_frame = ctk.CTkFrame(pane, fg_color="transparent")
        pane.add(top_frame, minsize=200)
        pane.add(bot_frame, minsize=120)

        hdr = ctk.CTkFrame(top_frame, fg_color="transparent")
        hdr.pack(fill="x", padx=PAD, pady=(PAD, 4))
        section_header(hdr, "🧾  Чеки").pack(side="left")

        # date filter
        today = date.today().isoformat()
        self._date_from = tk.StringVar(value=today)
        self._date_to = tk.StringVar(value=today)
        ctk.CTkLabel(hdr, text="по", text_color=TEXT_DIM, font=FONT_SM).pack(side="right", padx=2)
        ctk.CTkEntry(hdr, textvariable=self._date_to, width=110,
                     fg_color=SURFACE2, border_color=PRIMARY, text_color=TEXT).pack(side="right", padx=2)
        ctk.CTkLabel(hdr, text="з", text_color=TEXT_DIM, font=FONT_SM).pack(side="right", padx=2)
        ctk.CTkEntry(hdr, textvariable=self._date_from, width=110,
                     fg_color=SURFACE2, border_color=PRIMARY, text_color=TEXT).pack(side="right", padx=2)
        ctk.CTkButton(hdr, text="Фільтр", fg_color=PRIMARY, hover_color=PRIMARY_DARK,
                      width=80, command=self.refresh).pack(side="right", padx=4)

        # cashier filter (manager only)
        if self.is_manager:
            cashiers = DB.fetchall(
                "SELECT id_employee,empl_surname FROM Employee WHERE empl_role='Касир'")
            vals = ["Всі касири"] + [f"{r['id_employee']} - {r['empl_surname']}" for r in cashiers]
            self._cashier_var = tk.StringVar(value="Всі касири")
            ctk.CTkComboBox(hdr, variable=self._cashier_var, values=vals, width=200,
                            fg_color=SURFACE2, border_color=PRIMARY, text_color=TEXT,
                            button_color=PRIMARY, dropdown_fg_color=SURFACE2,
                            command=lambda _: self.refresh()).pack(side="right", padx=4)

        acts = ctk.CTkFrame(top_frame, fg_color="transparent")
        acts.pack(fill="x", padx=PAD, pady=2)
        if not self.is_manager:
            btn_add(acts, self._create_check).pack(side="left", padx=2)
        if self.is_manager:
            btn_delete(acts, self._delete).pack(side="left", padx=2)
            btn_report(acts, self._report).pack(side="left", padx=2)
            self._total_lbl = ctk.CTkLabel(acts, text="", text_color=ACCENT_LIGHT, font=FONT_MD)
            self._total_lbl.pack(side="left", padx=16)

        tbl_frame = ctk.CTkFrame(top_frame, fg_color=SURFACE, corner_radius=CORNER)
        tbl_frame.pack(fill="both", expand=True, padx=PAD, pady=(2, PAD))
        self.tree = make_table(tbl_frame, CHECK_COLS)
        add_scrollbars(tbl_frame, self.tree)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        hdr2 = ctk.CTkFrame(bot_frame, fg_color="transparent")
        hdr2.pack(fill="x", padx=PAD, pady=(4, 2))
        section_header(hdr2, "📋  Склад чеку").pack(side="left")
        self._check_info = ctk.CTkLabel(hdr2, text="", text_color=TEXT_DIM, font=FONT_SM)
        self._check_info.pack(side="left", padx=12)

        tbl2 = ctk.CTkFrame(bot_frame, fg_color=SURFACE, corner_radius=CORNER)
        tbl2.pack(fill="both", expand=True, padx=PAD, pady=(0, PAD))
        self.sale_tree = make_table(tbl2, SALE_COLS)
        add_scrollbars(tbl2, self.sale_tree)

    def refresh(self):
        df = self._date_from.get().strip() or "2000-01-01"
        dt = self._date_to.get().strip() or "2099-12-31"
        df += " 00:00:00"; dt += " 23:59:59"

        if self.is_manager and hasattr(self, "_cashier_var"):
            cv = self._cashier_var.get()
            if cv != "Всі касири":
                cid = cv.split(" - ")[0]
                rows = DB.fetchall(
                    "SELECT c.check_number,"
                    "e.empl_surname||' '||e.empl_name as emp,"
                    "c.card_number,c.print_date,c.sum_total,c.vat "
                    "FROM [Check] c JOIN Employee e ON c.id_employee=e.id_employee "
                    "WHERE c.id_employee=? AND c.print_date BETWEEN ? AND ? "
                    "ORDER BY CAST(SUBSTR(c.check_number,3) AS INT) DESC", (cid, df, dt))
            else:
                rows = DB.fetchall(
                    "SELECT c.check_number,"
                    "e.empl_surname||' '||e.empl_name as emp,"
                    "c.card_number,c.print_date,c.sum_total,c.vat "
                    "FROM [Check] c JOIN Employee e ON c.id_employee=e.id_employee "
                    "WHERE c.print_date BETWEEN ? AND ? "
                    "ORDER BY CAST(SUBSTR(c.check_number,3) AS INT) DESC", (df, dt))
        else:
            rows = DB.fetchall(
                "SELECT c.check_number,"
                "e.empl_surname||' '||e.empl_name as emp,"
                "c.card_number,c.print_date,c.sum_total,c.vat "
                "FROM [Check] c JOIN Employee e ON c.id_employee=e.id_employee "
                "WHERE c.id_employee=? AND c.print_date BETWEEN ? AND ? "
                "ORDER BY CAST(SUBSTR(c.check_number,3) AS INT) DESC",
                (self.user["id_employee"], df, dt))

        fill_table(self.tree, rows)
        if self.is_manager and hasattr(self, "_total_lbl"):
            total = sum(r["sum_total"] for r in rows)
            self._total_lbl.configure(text=f"Загальна сума: {total:.2f} ₴")
        self.sale_tree.delete(*self.sale_tree.get_children())

    def _on_select(self, _):
        sel = self.tree.selection()
        if not sel:
            return
        cnum = self.tree.item(sel[0])["values"][0]
        self._load_sales(cnum)

    def _load_sales(self, check_number: str):
        rows = DB.fetchall(
            "SELECT s.UPC,p.product_name,s.product_number,s.selling_price,"
            "s.product_number*s.selling_price as line_total "
            "FROM Sale s JOIN Store_Product sp ON s.UPC=sp.UPC "
            "JOIN Product p ON sp.id_product=p.id_product "
            "WHERE s.check_number=?", (check_number,))
        fill_table(self.sale_tree, rows)
        chk = DB.fetchone("SELECT sum_total,vat FROM [Check] WHERE check_number=?",
                          (check_number,))
        if chk:
            self._check_info.configure(
                text=f"Чек {check_number}  |  Сума: {chk['sum_total']:.2f} ₴  |  ПДВ: {chk['vat']:.2f} ₴")

    def _create_check(self):
        CheckCreateDialog(self, self.user, on_done=self.refresh)

    def _selected_check(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Увага", "Оберіть чек", parent=self)
            return None
        return self.tree.item(sel[0])["values"][0]

    def _delete(self):
        cnum = self._selected_check()
        if cnum is None:
            return
        if confirm_delete(self, cnum):
            try:
                DB.execute("DELETE FROM [Check] WHERE check_number=?", (cnum,))
                self.refresh()
            except Exception as e:
                messagebox.showerror("Помилка", str(e), parent=self)

    def _report(self):
        df = (self._date_from.get().strip() or "2000-01-01") + " 00:00:00"
        dt = (self._date_to.get().strip() or "2099-12-31") + " 23:59:59"
        rows = DB.fetchall(
            "SELECT c.check_number,e.empl_surname,c.card_number,"
            "c.print_date,c.sum_total,c.vat "
            "FROM [Check] c JOIN Employee e ON c.id_employee=e.id_employee "
            "WHERE c.print_date BETWEEN ? AND ? ORDER BY CAST(SUBSTR(c.check_number,3) AS INT) DESC",
            (df, dt))
        total = sum(r["sum_total"] for r in rows)
        generate_report(f"Чеки за період {self._date_from.get()} - {self._date_to.get()}",
                        ["Чек", "Касир", "Карта", "Дата", "Сума", "ПДВ"],
                        rows, self,
                        extra_info=f"Загалом: {total:.2f} ₴")


class CheckCreateDialog(ctk.CTkToplevel):
    def __init__(self, parent, user, on_done):
        super().__init__(parent)
        self.title("Новий чек")
        self.configure(fg_color=SURFACE)
        self.grab_set()
        self.resizable(True, True)
        self.geometry("780x580")
        self.user = user
        self.on_done = on_done
        self._items: list[dict] = []  # {upc, name, price, qty}
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="🧾  Новий чек", font=FONT_LG,
                     text_color=ACCENT_LIGHT).pack(pady=(14, 4), padx=20, anchor="w")

        card_row = ctk.CTkFrame(self, fg_color="transparent")
        card_row.pack(fill="x", padx=20, pady=4)
        ctk.CTkLabel(card_row, text="Карта клієнта:", width=130,
                     text_color=TEXT_DIM, font=FONT_SM).pack(side="left")
        cards = DB.fetchall("SELECT card_number,cust_surname FROM Customer_Card ORDER BY cust_surname")
        card_vals = ["- без карти -"] + [f"{r['card_number']} - {r['cust_surname']}" for r in cards]
        self._card_var = tk.StringVar(value="- без карти -")
        ctk.CTkComboBox(card_row, variable=self._card_var, values=card_vals,
                        width=300, fg_color=SURFACE2, border_color=PRIMARY,
                        text_color=TEXT, button_color=PRIMARY,
                        dropdown_fg_color=SURFACE2).pack(side="left", padx=8)

        add_row = ctk.CTkFrame(self, fg_color=SURFACE2, corner_radius=CORNER)
        add_row.pack(fill="x", padx=20, pady=6)
        ctk.CTkLabel(add_row, text="Товар:", text_color=TEXT_DIM,
                     font=FONT_SM).pack(side="left", padx=8)
        prods = DB.fetchall(
            "SELECT sp.UPC,p.product_name,sp.selling_price,sp.products_number "
            "FROM Store_Product sp JOIN Product p ON sp.id_product=p.id_product "
            "WHERE sp.products_number>0 ORDER BY p.product_name")
        prod_vals = [f"{r['UPC']} | {r['product_name']} | {r['selling_price']:.2f}₴" for r in prods]
        self._prod_var = tk.StringVar()
        self._prod_cb = ctk.CTkComboBox(add_row, variable=self._prod_var,
                                        values=prod_vals, width=340,
                                        fg_color=SURFACE2, border_color=PRIMARY,
                                        text_color=TEXT, button_color=PRIMARY,
                                        dropdown_fg_color=BG)
        self._prod_cb.pack(side="left", padx=4)
        ctk.CTkLabel(add_row, text="К-сть:", text_color=TEXT_DIM,
                     font=FONT_SM).pack(side="left", padx=(12, 2))
        self._qty_var = tk.StringVar(value="1")
        ctk.CTkEntry(add_row, textvariable=self._qty_var, width=60,
                     fg_color=BG, border_color=PRIMARY, text_color=TEXT).pack(side="left", padx=4)
        ctk.CTkButton(add_row, text="＋", fg_color=PRIMARY,
                      hover_color=PRIMARY_DARK, width=40,
                      command=self._add_item).pack(side="left", padx=8)

        tbl_frame = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=CORNER)
        tbl_frame.pack(fill="both", expand=True, padx=20, pady=4)
        self.tree = make_table(tbl_frame, [
            ("upc", "UPC", 120), ("name", "Назва", 220),
            ("qty", "К-сть", 60), ("price", "Ціна", 80), ("sum", "Сума", 90)], height=8)
        add_scrollbars(tbl_frame, self.tree)

        tot_row = ctk.CTkFrame(self, fg_color="transparent")
        tot_row.pack(fill="x", padx=20, pady=4)
        self._total_lbl = ctk.CTkLabel(tot_row, text="Сума: 0.00 ₴",
                                       font=FONT_LG, text_color=ACCENT_LIGHT)
        self._total_lbl.pack(side="right", padx=12)
        self._vat_lbl = ctk.CTkLabel(tot_row, text="ПДВ: 0.00 ₴",
                                     font=FONT_MD, text_color=TEXT_DIM)
        self._vat_lbl.pack(side="right", padx=12)
        ctk.CTkButton(tot_row, text="✕ Видалити рядок", fg_color=DANGER,
                      hover_color="#CC2E25", width=150,
                      command=self._remove_item).pack(side="left")

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(4, 16))
        ctk.CTkButton(btn_row, text="Скасувати", fg_color=SURFACE2,
                      hover_color=SURFACE, text_color=TEXT_DIM,
                      command=self.destroy, width=120).pack(side="right", padx=4)
        ctk.CTkButton(btn_row, text="💾 Зберегти чек", fg_color=PRIMARY,
                      hover_color=PRIMARY_DARK, command=self._save, width=160).pack(side="right", padx=4)

    def _add_item(self):
        val = self._prod_var.get().strip()
        if not val:
            messagebox.showwarning("Увага", "Оберіть товар", parent=self); return
        try:
            qty = int(self._qty_var.get())
        except ValueError:
            messagebox.showwarning("Увага", "Введіть ціле число", parent=self); return
        if qty <= 0:
            messagebox.showwarning("Увага", "Кількість має бути > 0", parent=self); return

        upc = val.split(" | ")[0]
        sp = DB.fetchone(
            "SELECT sp.UPC,p.product_name,sp.selling_price,sp.products_number "
            "FROM Store_Product sp JOIN Product p ON sp.id_product=p.id_product "
            "WHERE sp.UPC=?", (upc,))
        if not sp:
            messagebox.showerror("Помилка", "Товар не знайдено", parent=self); return
        if qty > sp["products_number"]:
            messagebox.showwarning("Увага",
                f"Недостатньо товару. Наявно: {sp['products_number']} од.", parent=self)
            return

        # якщо товар вже є - збільшуємо кількість
        for item in self._items:
            if item["upc"] == upc:
                item["qty"] += qty
                self._refresh_items(); return

        self._items.append({
            "upc": upc,
            "name": sp["product_name"],
            "price": sp["selling_price"],
            "qty": qty,
        })
        self._refresh_items()

    def _remove_item(self):
        sel = self.tree.selection()
        if not sel:
            return
        val = str(self.tree.item(sel[0])["values"][0])
        # Treeview strips leading zeros - match by integer value
        self._items = [i for i in self._items if str(int(i["upc"])) != str(int(val))]
        self._refresh_items()

    def _refresh_items(self):
        fill_table(self.tree, [
            (i["upc"], i["name"], i["qty"], f"{i['price']:.2f}₴",
             f"{i['qty']*i['price']:.2f}₴")
            for i in self._items])
        total = sum(i["qty"] * i["price"] for i in self._items)
        # apply card discount
        card_val = self._card_var.get()
        if card_val != "- без карти -":
            card_num = card_val.split(" - ")[0]
            row = DB.fetchone("SELECT percent FROM Customer_Card WHERE card_number=?", (card_num,))
            if row:
                total *= (1 - row["percent"] / 100)
        vat = round(total * 0.2, 4)
        self._total_lbl.configure(text=f"Сума: {total:.2f} ₴")
        self._vat_lbl.configure(text=f"ПДВ: {vat:.2f} ₴")
        return total, vat

    def _save(self):
        if not self._items:
            messagebox.showwarning("Увага", "Додайте хоча б один товар", parent=self); return

        total, vat = self._refresh_items()
        check_num = DB.next_check_number()
        card_val = self._card_var.get()
        card_num = None if card_val == "- без карти -" else card_val.split(" - ")[0]
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            DB.execute('INSERT INTO [Check] VALUES (?,?,?,?,?,?)',
                       (check_num, self.user["id_employee"], card_num,
                        now, round(total, 4), round(vat, 4)))
            for item in self._items:
                DB.execute("INSERT INTO Sale VALUES (?,?,?,?)",
                           (item["upc"], check_num, item["qty"], item["price"]))
                # зменшуємо залишок на складі
                DB.execute("UPDATE Store_Product SET products_number=products_number-? WHERE UPC=?",
                           (item["qty"], item["upc"]))
            messagebox.showinfo("Готово", f"Чек {check_num} збережено!\nСума: {total:.2f} ₴",
                                parent=self)
            self.on_done()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Помилка", str(e), parent=self)
