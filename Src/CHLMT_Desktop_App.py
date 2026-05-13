import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import csv
from datetime import datetime
import os

DB_FILE = "chmt_schedule_desktop.sqlite"

class ScheduleApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Расписание и Записи - БПОУ ВО «ЧЛМТ»")
        self.root.geometry("900x600")
        self.root.minsize(800, 500)
        
        self.init_db()
        self.create_gui()
        self.apply_theme()
        
    def init_db(self):
        self.conn = sqlite3.connect(DB_FILE)
        self.cursor = self.conn.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                event_date TEXT NOT NULL,
                event_time TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

    def create_gui(self):
        # Панель управления (верхняя)
        control_frame = tk.Frame(self.root, padx=10, pady=10)
        control_frame.pack(fill=tk.X, side=tk.TOP)
        
        # Поиск
        tk.Label(control_frame, text="Поиск:").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(control_frame, textvariable=self.search_var, width=20)
        self.search_entry.pack(side=tk.LEFT, padx=5)
        self.search_entry.bind("<KeyRelease>", lambda event: self.load_data())
        
        # Фильтр по дате
        tk.Label(control_frame, text="Дата (ГГГГ-ММ-ДД):").pack(side=tk.LEFT, padx=5)
        self.date_filter_var = tk.StringVar()
        self.date_filter_entry = ttk.Entry(control_frame, textvariable=self.date_filter_var, width=12)
        self.date_filter_entry.pack(side=tk.LEFT, padx=5)
        self.date_filter_entry.bind("<KeyRelease>", lambda event: self.load_data())
        
        ttk.Button(control_frame, text="Сбросить", command=self.reset_filters).pack(side=tk.LEFT, padx=5)

        # Экспорт (справа)
        ttk.Button(control_frame, text="Экспорт CSV", command=self.export_csv).pack(side=tk.RIGHT, padx=5)
        
        # Основная область разделена на форму и таблицу
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Левая панель - Форма ввода
        form_frame = tk.LabelFrame(main_paned, text="Управление записью", padx=10, pady=10)
        main_paned.add(form_frame, weight=1)
        
        tk.Label(form_frame, text="Название:").grid(row=0, column=0, sticky="w", pady=5)
        self.title_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.title_var, width=30).grid(row=0, column=1, sticky="w", pady=5)
        
        tk.Label(form_frame, text="Дата (ГГГГ-ММ-ДД):").grid(row=1, column=0, sticky="w", pady=5)
        self.date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        ttk.Entry(form_frame, textvariable=self.date_var, width=15).grid(row=1, column=1, sticky="w", pady=5)
        
        tk.Label(form_frame, text="Время (ЧЧ:ММ):").grid(row=2, column=0, sticky="w", pady=5)
        self.time_var = tk.StringVar(value=datetime.now().strftime("%H:00"))
        ttk.Entry(form_frame, textvariable=self.time_var, width=10).grid(row=2, column=1, sticky="w", pady=5)
        
        tk.Label(form_frame, text="Описание:").grid(row=3, column=0, sticky="nw", pady=5)
        self.desc_text = tk.Text(form_frame, width=30, height=8)
        self.desc_text.grid(row=3, column=1, sticky="w", pady=5)
        
        btn_frame = tk.Frame(form_frame)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=15)
        
        ttk.Button(btn_frame, text="Добавить", command=self.add_record).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Обновить", command=self.update_record).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Удалить", command=self.delete_record).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Очистить", command=self.clear_form).pack(side=tk.LEFT, padx=5)
        
        # ID выбранной записи
        self.selected_id = None
        
        # Правая панель - Таблица
        tree_frame = tk.Frame(main_paned)
        main_paned.add(tree_frame, weight=3)
        
        columns = ("id", "date", "time", "title", "description")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        self.tree.heading("id", text="ID")
        self.tree.heading("date", text="Дата")
        self.tree.heading("time", text="Время")
        self.tree.heading("title", text="Название")
        self.tree.heading("description", text="Описание")
        
        self.tree.column("id", width=30)
        self.tree.column("date", width=80)
        self.tree.column("time", width=50)
        self.tree.column("title", width=150)
        self.tree.column("description", width=200)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        
        self.load_data()

    def reset_filters(self):
        self.search_var.set("")
        self.date_filter_var.set("")
        self.load_data()

    def load_data(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        search_term = f"%{self.search_var.get()}%"
        date_filter = self.date_filter_var.get()
        
        query = "SELECT id, event_date, event_time, title, description FROM schedules WHERE (title LIKE ? OR description LIKE ?)"
        params = [search_term, search_term]
        
        if date_filter:
            query += " AND event_date = ?"
            params.append(date_filter)
            
        query += " ORDER BY event_date ASC, event_time ASC"
        
        for row in self.cursor.execute(query, params):
            self.tree.insert("", tk.END, values=row)

    def add_record(self):
        title = self.title_var.get().strip()
        date = self.date_var.get().strip()
        time = self.time_var.get().strip()
        desc = self.desc_text.get("1.0", tk.END).strip()
        
        if not title or not date or not time:
            messagebox.showwarning("Ошибка", "Заполните обязательные поля: Название, Дата, Время")
            return
            
        self.cursor.execute("INSERT INTO schedules (title, description, event_date, event_time) VALUES (?, ?, ?, ?)",
                            (title, desc, date, time))
        self.conn.commit()
        self.clear_form()
        self.load_data()
        messagebox.showinfo("Успех", "Запись добавлена!")

    def on_tree_select(self, event):
        selected_items = self.tree.selection()
        if not selected_items:
            return
            
        item = self.tree.item(selected_items[0])
        values = item["values"]
        
        self.selected_id = values[0]
        self.date_var.set(values[1])
        self.time_var.set(values[2])
        self.title_var.set(values[3])
        
        self.desc_text.delete("1.0", tk.END)
        self.desc_text.insert(tk.END, values[4])

    def update_record(self):
        if not self.selected_id:
            messagebox.showwarning("Ошибка", "Выберите запись для обновления")
            return
            
        title = self.title_var.get().strip()
        date = self.date_var.get().strip()
        time = self.time_var.get().strip()
        desc = self.desc_text.get("1.0", tk.END).strip()
        
        self.cursor.execute("UPDATE schedules SET title=?, description=?, event_date=?, event_time=? WHERE id=?",
                            (title, desc, date, time, self.selected_id))
        self.conn.commit()
        self.load_data()
        messagebox.showinfo("Успех", "Запись обновлена!")

    def delete_record(self):
        if not self.selected_id:
            messagebox.showwarning("Ошибка", "Выберите запись для удаления")
            return
            
        if messagebox.askyesno("Подтверждение", "Вы уверены, что хотите удалить эту запись?"):
            self.cursor.execute("DELETE FROM schedules WHERE id=?", (self.selected_id,))
            self.conn.commit()
            self.clear_form()
            self.load_data()

    def clear_form(self):
        self.selected_id = None
        self.title_var.set("")
        self.date_var.set(datetime.now().strftime("%Y-%m-%d"))
        self.time_var.set(datetime.now().strftime("%H:00"))
        self.desc_text.delete("1.0", tk.END)

    def export_csv(self):
        filename = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not filename:
            return
            
        with open(filename, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Дата", "Время", "Название", "Описание"])
            for row in self.cursor.execute("SELECT id, event_date, event_time, title, description FROM schedules ORDER BY event_date ASC"):
                writer.writerow(row)
                
        messagebox.showinfo("Успех", "Данные успешно экспортированы!")

    def apply_theme(self):
        style = ttk.Style()
        self.root.configure(bg="white")
        style.theme_use('clam')
        style.configure(".", background="#f0f0f0", foreground="black", fieldbackground="white")
        style.configure("Treeview", background="white", foreground="black", fieldbackground="white")
        style.map("Treeview", background=[("selected", "#a6d4fa")])

if __name__ == "__main__":
    root = tk.Tk()
    app = ScheduleApp(root)
    root.mainloop()
