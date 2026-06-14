"""
Login window + main application shell.
"""
import sys
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

import db.database as DB
from utils.theme import *
from utils.widgets import section_header

from views.employees import EmployeesView
from views.products import ProductsView, CategoriesView
from views.store_products import StoreProductsView
from views.customers import CustomerCardsView
from views.checks import ChecksView
from views.statistics import StatisticsView


ctk.set_appearance_mode("light")
ctk.set_default_color_theme("green")


class LoginWindow(ctk.CTk):
    def __init__(self, accdb_path: str):
        super().__init__()
        self.title("ZLAGODA - Вхід")
        self.geometry("420x480")
        self.resizable(False, False)
        self.configure(fg_color=BG)
        DB.init(accdb_path)
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="🛒", font=("Segoe UI Emoji", 52)).pack(pady=(40, 4))
        ctk.CTkLabel(self, text="ZLAGODA", font=("Segoe UI", 28, "bold"),
                     text_color=ACCENT_LIGHT).pack()
        ctk.CTkLabel(self, text="Автоматизована інформаційна система",
                     font=FONT_SM, text_color=TEXT_DIM).pack(pady=(0, 28))

        card = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=CORNER * 2)
        card.pack(padx=48, fill="x")

        ctk.CTkLabel(card, text="ID працівника", anchor="w",
                     font=FONT_SM, text_color=TEXT_DIM).pack(anchor="w", padx=20, pady=(18, 2))
        self._id_var = tk.StringVar()
        ctk.CTkEntry(card, textvariable=self._id_var,
                     placeholder_text="наприклад E001",
                     width=300, fg_color=SURFACE2,
                     border_color=PRIMARY, text_color=TEXT).pack(padx=20)

        ctk.CTkLabel(card, text="Пароль", anchor="w",
                     font=FONT_SM, text_color=TEXT_DIM).pack(anchor="w", padx=20, pady=(12, 2))
        self._pw_var = tk.StringVar()
        self._pw_entry = ctk.CTkEntry(card, textvariable=self._pw_var,
                                      show="•", width=300,
                                      fg_color=SURFACE2, border_color=PRIMARY,
                                      text_color=TEXT)
        self._pw_entry.pack(padx=20)
        self._pw_entry.bind("<Return>", lambda _: self._login())

        ctk.CTkButton(card, text="Увійти", fg_color=PRIMARY,
                      hover_color=PRIMARY_DARK, height=40,
                      font=FONT_MD, command=self._login).pack(padx=20, pady=18, fill="x")

        ctk.CTkLabel(self,
                     text="Пароль за замовчуванням: ID малими літерами\nнаприклад e001",
                     font=("Segoe UI", 10), text_color=TEXT_DIM).pack(pady=14)

    def _login(self):
        eid = self._id_var.get().strip()
        pw = self._pw_var.get()
        if not eid or not pw:
            messagebox.showwarning("Увага", "Введіть ID та пароль", parent=self)
            return
        user = DB.authenticate(eid, pw)
        if not user:
            messagebox.showerror("Помилка", "Невірний ID або пароль", parent=self)
            return
        self.withdraw()
        app = MainApp(user, self)
        app.mainloop()


class MainApp(ctk.CTkToplevel):
    def __init__(self, user, login_win: LoginWindow):
        super().__init__()
        self.user = user
        self.login_win = login_win
        self.is_manager = user["empl_role"] == "Менеджер"

        self.title(f"ZLAGODA АІС - {user['empl_surname']} {user['empl_name']}  [{user['empl_role']}]")
        self.geometry(f"{WIN_W}x{WIN_H}")
        self.minsize(900, 600)
        self.configure(fg_color=BG)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build()

    def _build(self):
        sidebar = ctk.CTkFrame(self, fg_color=SURFACE, width=190, corner_radius=0)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        ctk.CTkLabel(sidebar, text="🛒  ZLAGODA", font=FONT_LG,
                     text_color=ACCENT_LIGHT).pack(pady=(20, 4), padx=12)
        ctk.CTkLabel(sidebar,
                     text=f"{self.user['empl_surname']} {self.user['empl_name']}\n{self.user['empl_role']}",
                     font=FONT_SM, text_color=TEXT_DIM,
                     justify="center").pack(pady=(0, 16))
        ctk.CTkFrame(sidebar, height=1, fg_color=SURFACE2).pack(fill="x", padx=12)

        self._nav_btns = {}
        self._active = tk.StringVar(value="")

        if self.is_manager:
            tabs = [
                ("employees", "👤  Працівники"),
                ("categories", "🗂  Категорії"),
                ("products", "📦  Товари"),
                ("store", "🏪  Товари у магазині"),
                ("customers", "💳  Карти клієнтів"),
                ("checks", "🧾  Чеки"),
                ("statistics", "📊  Статистика"),
            ]
        else:
            tabs = [
                ("store", "🏪  Товари у магазині"),
                ("products", "📦  Товари"),
                ("customers", "💳  Карти клієнтів"),
                ("checks", "🧾  Мої чеки"),
                ("profile", "👤  Мій профіль"),
            ]

        for key, label in tabs:
            btn = ctk.CTkButton(
                sidebar, text=label, anchor="w",
                fg_color="transparent", hover_color=SURFACE2,
                text_color=TEXT_DIM, font=FONT_MD,
                height=40, corner_radius=6,
                command=lambda k=key: self._show_tab(k))
            btn.pack(fill="x", padx=8, pady=2)
            self._nav_btns[key] = btn

        ctk.CTkFrame(sidebar, height=1, fg_color=SURFACE2).pack(fill="x", padx=12, pady=8, side="bottom")
        ctk.CTkButton(sidebar, text="🔒 Змінити пароль", anchor="w",
                      fg_color="transparent", hover_color=SURFACE2,
                      text_color=TEXT_DIM, font=FONT_SM, height=34,
                      command=self._change_password).pack(side="bottom", fill="x", padx=8, pady=2)
        ctk.CTkButton(sidebar, text="← Вийти", anchor="w",
                      fg_color="transparent", hover_color=SURFACE2,
                      text_color=TEXT_DIM, font=FONT_SM, height=34,
                      command=self._logout).pack(side="bottom", fill="x", padx=8, pady=2)

        self._content = ctk.CTkFrame(self, fg_color="transparent")
        self._content.pack(side="left", fill="both", expand=True)
        self._views: dict[str, ctk.CTkFrame] = {}
        self._current_key = None

        self._show_tab(tabs[0][0])

    def _get_view(self, key: str) -> ctk.CTkFrame:
        if key not in self._views:
            v = self._make_view(key)
            if v:
                self._views[key] = v
        return self._views.get(key)

    def _make_view(self, key: str):
        u = self.user
        mapping = {
            "employees": lambda: EmployeesView(self._content, u),
            "categories": lambda: CategoriesView(self._content, u),
            "products": lambda: ProductsView(self._content, u),
            "store": lambda: StoreProductsView(self._content, u),
            "customers": lambda: CustomerCardsView(self._content, u),
            "checks": lambda: ChecksView(self._content, u),
            "statistics": lambda: StatisticsView(self._content, u),
            "profile": lambda: self._make_profile(),
        }
        fn = mapping.get(key)
        return fn() if fn else None

    def _show_tab(self, key: str):
        if self._current_key and self._current_key in self._views:
            self._views[self._current_key].pack_forget()
        for k, btn in self._nav_btns.items():
            if k == key:
                btn.configure(fg_color=PRIMARY, text_color=SURFACE)
            else:
                btn.configure(fg_color="transparent", text_color=TEXT_DIM)
        view = self._get_view(key)
        if view:
            view.pack(fill="both", expand=True)
        self._current_key = key

    def _make_profile(self) -> ctk.CTkFrame:
        f = ctk.CTkFrame(self._content, fg_color="transparent")
        section_header(f, "👤  Мій профіль").pack(anchor="w", padx=PAD, pady=(PAD, 4))
        u = self.user
        card = ctk.CTkFrame(f, fg_color=SURFACE, corner_radius=CORNER)
        card.pack(padx=PAD, pady=8, fill="x")
        fields = [
            ("ID:", u["id_employee"]),
            ("Прізвище:", u["empl_surname"]),
            ("Ім'я:", u["empl_name"]),
            ("По батькові:", u["empl_patronymic"] or "-"),
            ("Посада:", u["empl_role"]),
            ("Зарплата:", f"{u['salary']:.2f} ₴"),
            ("Телефон:", u["phone_number"]),
            ("Адреса:", f"{u['city']}, {u['street']}"),
        ]
        for label, val in fields:
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=3)
            ctk.CTkLabel(row, text=label, width=150, anchor="w",
                         font=FONT_SM, text_color=TEXT_DIM).pack(side="left")
            ctk.CTkLabel(row, text=val, anchor="w",
                         font=FONT_MD, text_color=TEXT).pack(side="left")
        return f

    def _change_password(self):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Змінити пароль")
        dlg.configure(fg_color=SURFACE)
        dlg.grab_set()
        dlg.geometry("360x240")
        for label, show, var_attr in [("Новий пароль", "•", "_pw1"),
                                       ("Повторіть пароль", "•", "_pw2")]:
            ctk.CTkLabel(dlg, text=label, text_color=TEXT_DIM, font=FONT_SM,
                         anchor="w").pack(padx=24, pady=(14, 2), anchor="w")
            v = tk.StringVar()
            setattr(self, var_attr, v)
            ctk.CTkEntry(dlg, textvariable=v, show=show, width=300,
                         fg_color=SURFACE2, border_color=PRIMARY,
                         text_color=TEXT).pack(padx=24)

        def save():
            p1, p2 = self._pw1.get(), self._pw2.get()
            if not p1:
                messagebox.showwarning("Увага", "Введіть пароль", parent=dlg); return
            if p1 != p2:
                messagebox.showerror("Помилка", "Паролі не збігаються", parent=dlg); return
            DB.change_password(self.user["id_employee"], p1)
            messagebox.showinfo("Готово", "Пароль змінено", parent=dlg)
            dlg.destroy()

        ctk.CTkButton(dlg, text="Зберегти", fg_color=PRIMARY,
                      hover_color=PRIMARY_DARK, command=save).pack(pady=18)

    def _logout(self):
        self.destroy()
        self.login_win.deiconify()
        self.login_win._id_var.set("")
        self.login_win._pw_var.set("")

    def _on_close(self):
        if messagebox.askyesno("Вихід", "Закрити програму?"):
            self.login_win.destroy()
            sys.exit(0)
