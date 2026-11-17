# ШІ: Claude (Opus 5.5) – основна структура вікна MainWindow: таблиці, меню та елементи керування.
# Змінено: самостійно доповнено CRUD-операції, пошук, фільтрацію, сортування, форми редагування, обробку помилок і відображення стану фонових операцій.
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

from view.forms import BookingForm, GuestForm, RoomForm

POLL_INTERVAL_MS = 100
ALL_TYPES = "Усі"
BOOKING_COLUMNS = ("id", "guest", "phone", "room", "type", "guests", "check_in", "check_out", "nights", "price")
BOOKING_HEADINGS = ("ID", "Гість", "Телефон", "Номер", "Тип", "Гостей", "Заїзд", "Виїзд", "Ночей", "Вартість")
SORT_KEYS = {"check_in": "check_in", "price": "price", "room": "room_number"}


class MainWindow:
    """Головне вікно: таблиці бронювань, гостей і номерів, меню файлів."""

    def __init__(self, root: tk.Tk, controller) -> None:
        """Будує вікно, заповнює таблиці і запускає опитування черги."""
        self.root = root
        self.controller = controller
        self.sort_state = {}
        self.sort_key = None
        self.sort_reverse = False
        self.root.title("Бронювання номерів у готелі")
        self.root.geometry("1200x720")
        self.root.minsize(900, 550)
        self.__create_menu()
        self.__create_tables()
        self.__create_status()
        self.__refresh_tables()
        self.root.after(POLL_INTERVAL_MS, self.__poll_messages)

    def __create_menu(self) -> None:
        """Створює меню «Файл» з імпортом і експортом."""
        self.menu = tk.Menu(self.root)
        file_menu = tk.Menu(self.menu, tearoff=0)
        file_menu.add_command(label="Імпорт JSON", command=self.__import_json)
        file_menu.add_command(label="Експорт JSON", command=self.__export_json)
        file_menu.add_command(label="Звіт XML", command=self.__export_xml)
        self.menu.add_cascade(label="Файл", menu=file_menu)
        self.root.config(menu=self.menu)
        self.file_menu = file_menu

    def __create_tables(self) -> None:
        """Створює вкладки з таблицями і кнопками."""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        self.booking_frame = ttk.Frame(self.notebook)
        self.guest_frame = ttk.Frame(self.notebook)
        self.room_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.booking_frame, text="Бронювання")
        self.notebook.add(self.guest_frame, text="Гості")
        self.notebook.add(self.room_frame, text="Номери")

        self.__create_booking_controls()
        self.booking_table = self.__create_table(
            self.booking_frame, BOOKING_COLUMNS, BOOKING_HEADINGS, sortable=True)
        self.__create_crud_buttons(
            self.booking_frame, self.__add_booking, self.__edit_booking, self.__delete_booking)

        self.__create_guest_controls()
        self.__create_crud_buttons(
            self.guest_frame, self.__add_guest, self.__edit_guest, self.__delete_guest)
        self.guest_table = self.__create_table(
            self.guest_frame, ("phone", "last_name", "first_name", "middle_name", "email"),
            ("Телефон", "Прізвище", "Ім'я", "По батькові", "Email"))

        self.__create_room_controls()
        self.room_table = self.__create_table(
            self.room_frame, ("number", "type", "capacity", "price"),
            ("Номер", "Тип", "Місткість", "Ціна за ніч"))
        self.__create_crud_buttons(
            self.room_frame, self.__add_room, self.__edit_room, self.__delete_room)

    def __create_guest_controls(self) -> None:
        """Створює поле пошуку гостя за ПІБ або телефоном."""
        frame = ttk.LabelFrame(self.guest_frame, text="Пошук гостя", padding=8)
        frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(frame, text="ПІБ або телефон:").grid(row=0, column=0, padx=4, pady=3)
        self.guest_search_var = tk.StringVar()
        entry = ttk.Entry(frame, textvariable=self.guest_search_var, width=30)
        entry.grid(row=0, column=1, padx=4, pady=3)
        entry.bind("<Return>", lambda event: self.__safe_call(self.__refresh_guests))
        ttk.Button(frame, text="Знайти", command=lambda: self.__safe_call(self.__refresh_guests)).grid(
            row=0, column=2, padx=4)
        ttk.Button(frame, text="Скинути", command=self.__reset_guest_search).grid(row=0, column=3, padx=4)

    def __create_room_controls(self) -> None:
        """Створює фільтр номерів за типом і вільними датами."""
        frame = ttk.LabelFrame(self.room_frame, text="Вільні номери", padding=8)
        frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(frame, text="Тип номера:").grid(row=0, column=0, padx=4, pady=3)
        self.room_type_var = tk.StringVar(value=ALL_TYPES)
        ttk.Combobox(frame, textvariable=self.room_type_var, values=self.__type_values(),
                     state="readonly", width=13).grid(row=0, column=1, padx=4, pady=3)
        ttk.Label(frame, text="Заїзд:").grid(row=0, column=2, padx=4, pady=3)
        self.room_from_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.room_from_var, width=12).grid(row=0, column=3, padx=4, pady=3)
        ttk.Label(frame, text="Виїзд:").grid(row=0, column=4, padx=4, pady=3)
        self.room_to_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.room_to_var, width=12).grid(row=0, column=5, padx=4, pady=3)
        ttk.Button(frame, text="Показати", command=lambda: self.__safe_call(self.__refresh_rooms)).grid(
            row=0, column=6, padx=4)
        ttk.Button(frame, text="Скинути", command=self.__reset_room_filters).grid(row=0, column=7, padx=4)

    def __type_values(self) -> tuple:
        """Список типів для фільтрів: «Усі» і типи з моделі."""
        return (ALL_TYPES, *self.controller.get_room_type_names())

    def __refresh_guests(self) -> None:
        """Показує гостей з урахуванням пошуку."""
        self.__fill_table(self.guest_table, self.controller.get_guest_rows(self.guest_search_var.get()))

    def __reset_guest_search(self) -> None:
        """Очищає пошук гостей."""
        self.guest_search_var.set("")
        self.__safe_call(self.__refresh_guests)

    def __refresh_rooms(self) -> None:
        """Показує номери за типом; якщо вказано дати – лише вільні."""
        room_type = self.room_type_var.get()
        rows = self.controller.get_room_rows(
            None if room_type == ALL_TYPES else room_type,
            self.room_from_var.get(), self.room_to_var.get())
        self.__fill_table(self.room_table, rows)

    def __reset_room_filters(self) -> None:
        """Очищає фільтр номерів."""
        self.room_type_var.set(ALL_TYPES)
        self.room_from_var.set("")
        self.room_to_var.set("")
        self.__safe_call(self.__refresh_rooms)

    def __open_room_form(self, number: str | None = None) -> None:
        """Відкриває форму номера; дані для редагування бере з контролера."""
        room = self.controller.get_room_row(number) if number else None
        RoomForm(self.root, self.__save_room, self.controller.get_room_type_names(), room)

    def __add_room(self) -> None:
        """Відкриває форму нового номера."""
        self.__safe_call(self.__open_room_form)

    def __edit_room(self) -> None:
        """Відкриває форму редагування вибраного номера."""
        number = self.__selected_key(self.room_table, "номер")
        if number:
            self.__safe_call(self.__open_room_form, number)

    def __save_room(self, room_type, number, capacity, price, editing=False):
        """Зберігає номер з форми і оновлює таблиці."""
        self.__ensure_idle()
        if editing:
            self.controller.update_room(room_type, number, capacity, price)
        else:
            self.controller.add_room(room_type, number, capacity, price)
        self.__refresh_tables()

    def __delete_room(self) -> None:
        """Видаляє вибраний номер після підтвердження."""
        number = self.__selected_key(self.room_table, "номер")
        if number and messagebox.askyesno("Підтвердження", f"Видалити номер {number}?", parent=self.root):
            self.__safe_call(self.__remove_room, number)

    def __remove_room(self, number: str) -> None:
        """Видаляє номер і оновлює таблиці."""
        self.controller.delete_room(number)
        self.__refresh_tables()

    def __create_booking_controls(self) -> None:
        """Створює поля пошуку і фільтрації бронювань."""
        frame = ttk.LabelFrame(self.booking_frame, text="Пошук і фільтрація", padding=8)
        frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(frame, text="Пошук:").grid(row=0, column=0, padx=4, pady=3)
        self.search_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.search_var, width=20).grid(row=0, column=1, padx=4, pady=3)
        ttk.Label(frame, text="Тип номера:").grid(row=0, column=2, padx=4, pady=3)
        self.type_var = tk.StringVar(value=ALL_TYPES)
        type_combo = ttk.Combobox(frame, textvariable=self.type_var, values=self.__type_values(),
                                  state="readonly", width=13)
        type_combo.grid(row=0, column=3, padx=4, pady=3)
        ttk.Label(frame, text="Дата з:").grid(row=0, column=4, padx=4, pady=3)
        self.date_from_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.date_from_var, width=12).grid(row=0, column=5, padx=4, pady=3)
        ttk.Label(frame, text="Дата по:").grid(row=0, column=6, padx=4, pady=3)
        self.date_to_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.date_to_var, width=12).grid(row=0, column=7, padx=4, pady=3)
        ttk.Button(frame, text="Застосувати", command=self.__apply_filters).grid(row=0, column=8, padx=4)
        ttk.Button(frame, text="Скинути", command=self.__reset_filters).grid(row=0, column=9, padx=4)

    def __create_table(self, parent, columns: tuple, headings: tuple, sortable: bool = False) -> ttk.Treeview:
        """Створює таблицю зі смугою прокрутки."""
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True, padx=5, pady=5)
        table = ttk.Treeview(frame, columns=columns, show="headings")
        for column, heading in zip(columns, headings):
            table.heading(column, text=heading)
            if sortable:
                table.heading(column, command=lambda key=column: self.__sort_bookings(key))
            table.column(column, width=110, anchor="center")
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=table.yview)
        table.configure(yscrollcommand=scrollbar.set)
        table.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        return table

    @staticmethod
    def __create_crud_buttons(parent, add_command, edit_command, delete_command) -> None:
        """Додає кнопки «Додати», «Редагувати», «Видалити»."""
        frame = ttk.Frame(parent)
        frame.pack(fill="x", padx=5, pady=(0, 5))
        ttk.Button(frame, text="Додати", command=add_command).pack(side="left", padx=3)
        ttk.Button(frame, text="Редагувати", command=edit_command).pack(side="left", padx=3)
        ttk.Button(frame, text="Видалити", command=delete_command).pack(side="left", padx=3)

    def __create_status(self) -> None:
        """Створює рядок стану й індикатор виконання."""
        frame = ttk.Frame(self.root, padding=(10, 0, 10, 10))
        frame.pack(fill="x")
        self.status_label = ttk.Label(frame, text="Готово")
        self.status_label.pack(fill="x")
        self.cancel_button = ttk.Button(frame, text="Скасувати", command=self.__cancel_task, state="disabled")
        self.cancel_button.pack(side="right", pady=(5, 0))
        self.progress = ttk.Progressbar(frame, mode="indeterminate")
        self.progress.pack(fill="x", expand=True, pady=(5, 0), padx=(0, 5))

    def __refresh_tables(self) -> None:
        """Оновлює всі таблиці з поточними фільтрами."""
        for refresh in (self.__refresh_guests, self.__refresh_rooms, self.__refresh_bookings):
            try:
                refresh()
            except ValueError as error:
                messagebox.showerror("Помилка фільтра", str(error), parent=self.root)

    @staticmethod
    def __fill_table(table, rows) -> None:
        """Заповнює таблицю. Ключ рядка (iid) – перша колонка: ID або телефон."""
        table.delete(*table.get_children())
        for row in rows:
            table.insert("", "end", iid=str(row[0]), values=row)

    def __current_filters(self) -> dict:
        """Збирає фільтри і сортування з полів вікна."""
        room_type = self.type_var.get()
        return {
            "search_text": self.search_var.get(),
            "room_type": None if room_type == ALL_TYPES else room_type,
            "date_from": self.date_from_var.get(),
            "date_to": self.date_to_var.get(),
            "sort_key": self.sort_key,
            "reverse": self.sort_reverse,
        }

    def __refresh_bookings(self) -> None:
        """Показує бронювання з урахуванням фільтрів і сортування."""
        rows = self.controller.get_booking_rows(**self.__current_filters())
        self.__fill_table(self.booking_table, rows)

    def __apply_filters(self) -> None:
        """Застосовує фільтри з полів."""
        self.__safe_call(self.__refresh_bookings)

    def __reset_filters(self) -> None:
        """Очищає фільтри і сортування."""
        self.search_var.set("")
        self.type_var.set(ALL_TYPES)
        self.date_from_var.set("")
        self.date_to_var.set("")
        self.sort_key = None
        self.sort_reverse = False
        self.__safe_call(self.__refresh_bookings)

    def __sort_bookings(self, column: str) -> None:
        """Сортує за колонкою; повторне натискання змінює напрям."""
        if column not in SORT_KEYS:
            return
        reverse = self.sort_state.get(column, False)
        self.sort_state[column] = not reverse
        self.sort_key = SORT_KEYS[column]
        self.sort_reverse = reverse
        self.__safe_call(self.__refresh_bookings)

    def __selected_key(self, table, label: str) -> str | None:
        """Повертає ключ виділеного рядка або None, якщо нічого не вибрано."""
        selected = table.selection()
        if not selected:
            messagebox.showwarning("Увага", f"Спочатку виберіть {label}.", parent=self.root)
            return None
        return selected[0]

    def __ensure_idle(self) -> None:
        """Не дає змінювати дані, поки працює фонова задача."""
        if self.controller.is_busy():
            raise ValueError("Зачекайте завершення фонової операції.")

    def __open_booking_form(self, booking_id: str | None = None) -> None:
        """Відкриває форму бронювання; дані для редагування бере з контролера."""
        booking = self.controller.get_booking_row(booking_id) if booking_id else None
        BookingForm(self.root, self.__save_booking, self.controller.get_guest_rows(),
                    self.controller.get_room_options(), booking)

    def __add_booking(self) -> None:
        """Відкриває форму нового бронювання."""
        self.__safe_call(self.__open_booking_form)

    def __edit_booking(self) -> None:
        """Відкриває форму редагування вибраного бронювання."""
        booking_id = self.__selected_key(self.booking_table, "бронювання")
        if booking_id:
            self.__safe_call(self.__open_booking_form, booking_id)

    def __save_booking(self, guest_phone, room_number, guests_count, check_in, check_out, booking_id=None):
        """Зберігає бронювання з форми і оновлює таблиці."""
        self.__ensure_idle()
        if booking_id:
            self.controller.update_booking(booking_id, guest_phone, room_number, guests_count, check_in, check_out)
        else:
            self.controller.create_booking(guest_phone, room_number, guests_count, check_in, check_out)
        self.__refresh_tables()

    def __delete_booking(self) -> None:
        """Видаляє вибране бронювання після підтвердження."""
        booking_id = self.__selected_key(self.booking_table, "бронювання")
        if booking_id and messagebox.askyesno(
                "Підтвердження", f"Видалити бронювання №{booking_id}?", parent=self.root):
            self.__safe_call(self.__remove_booking, booking_id)

    def __remove_booking(self, booking_id: str) -> None:
        """Скасовує бронювання і оновлює таблиці."""
        self.controller.cancel_booking(booking_id)
        self.__refresh_tables()

    def __open_guest_form(self, phone: str | None = None) -> None:
        """Відкриває форму гостя; дані для редагування бере з контролера."""
        guest = self.controller.get_guest_row(phone) if phone else None
        GuestForm(self.root, self.__save_guest, guest)

    def __add_guest(self) -> None:
        """Відкриває форму нового гостя."""
        self.__safe_call(self.__open_guest_form)

    def __edit_guest(self) -> None:
        """Відкриває форму редагування вибраного гостя."""
        phone = self.__selected_key(self.guest_table, "гостя")
        if phone:
            self.__safe_call(self.__open_guest_form, phone)

    def __save_guest(self, phone, last_name, first_name, middle_name, email, editing=False):
        """Зберігає гостя з форми і оновлює таблиці."""
        self.__ensure_idle()
        if editing:
            self.controller.update_guest(phone, last_name, first_name, middle_name, email)
        else:
            self.controller.add_guest(phone, last_name, first_name, middle_name, email)
        self.__refresh_tables()

    def __delete_guest(self) -> None:
        """Видаляє вибраного гостя після підтвердження."""
        phone = self.__selected_key(self.guest_table, "гостя")
        if phone:
            self.__safe_call(self.__confirm_delete_guest, phone)

    def __confirm_delete_guest(self, phone: str) -> None:
        """Питає підтвердження з ім'ям гостя і видаляє його."""
        guest = self.controller.get_guest_row(phone)
        name = " ".join(part for part in guest[1:4] if part)
        if messagebox.askyesno("Підтвердження", f"Видалити гостя {name}?", parent=self.root):
            self.controller.delete_guest(phone)
            self.__refresh_tables()

    def __set_menu_state(self, state: str) -> None:
        """Вмикає або вимикає пункти меню «Файл»."""
        for index in range(self.file_menu.index("end") + 1):
            self.file_menu.entryconfigure(index, state=state)

    def __finish_task(self, status: str) -> None:
        """Зупиняє індикатор і повертає меню після фонової задачі."""
        self.progress.stop()
        self.cancel_button.config(state="disabled")
        self.__set_menu_state("normal")
        self.status_label.config(text=status)

    def __cancel_task(self) -> None:
        """Просить контролер зупинити фонову задачу."""
        self.controller.cancel_task()
        self.cancel_button.config(state="disabled")
        self.status_label.config(text="Скасування...")

    def __poll_messages(self) -> None:
        """Забирає повідомлення фонового потоку з черги і оновлює вікно.

        Віджети змінюються лише тут, у головному потоці, через after().
        """
        for message_type, message in self.controller.poll_messages():
            if message_type == "start":
                self.progress.start(10)
                self.status_label.config(text=f"Виконується: {message}")
                self.__set_menu_state("disabled")
                if self.controller.can_cancel():
                    self.cancel_button.config(state="normal")
            elif message_type == "done":
                self.__finish_task(message)
                self.__refresh_tables()
            elif message_type == "cancelled":
                self.__finish_task(message)
            elif message_type == "error":
                self.__finish_task("Помилка виконання")
                messagebox.showerror("Помилка", message, parent=self.root)
        self.root.after(POLL_INTERVAL_MS, self.__poll_messages)

    def __safe_call(self, function, *args, **kwargs) -> None:
        """Викликає дію в головному потоці і показує помилку замість падіння.

        Фоновий потік тут не створюється: його запускає контролер у start_import / start_export_*.
        """
        if self.controller.is_busy():
            messagebox.showwarning("Увага", "Зачекайте завершення операції.", parent=self.root)
            return
        try:
            function(*args, **kwargs)
        except (ValueError, OSError) as error:
            messagebox.showerror("Помилка", str(error), parent=self.root)

    def __import_json(self) -> None:
        """Вибирає файл і запускає імпорт у фоновому потоці."""
        path = filedialog.askopenfilename(title="Імпорт JSON", filetypes=[("JSON файли", "*.json")])
        if path:
            self.__safe_call(self.controller.start_import, path)

    def __export_json(self) -> None:
        """Вибирає файл і запускає експорт JSON у фоновому потоці."""
        path = filedialog.asksaveasfilename(
            title="Експорт JSON", defaultextension=".json", filetypes=[("JSON файли", "*.json")])
        if path:
            self.__safe_call(self.controller.start_export_json, path)

    def __export_xml(self) -> None:
        """Питає період і файл, запускає XML-звіт у фоновому потоці."""
        start = simpledialog.askstring("Звіт XML", "Дата початку (ДД.ММ.РРРР):", parent=self.root)
        if start is None:
            return
        end = simpledialog.askstring("Звіт XML", "Дата завершення (ДД.ММ.РРРР):", parent=self.root)
        if end is None:
            return
        path = filedialog.asksaveasfilename(
            title="Збереження XML", defaultextension=".xml", filetypes=[("XML файли", "*.xml")])
        if path:
            self.__safe_call(self.controller.start_export_xml, path, start, end)