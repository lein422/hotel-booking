import tkinter as tk
from tkinter import ttk, messagebox

class BaseForm:
    """Базове вікно форми: поля, кнопки і збереження."""

    def __init__(self, parent, title: str, on_save) -> None:
        """Створює модальне вікно і запам'ятовує функцію збереження."""
        self.window = tk.Toplevel(parent)
        self.window.title(title)
        self.window.transient(parent)
        self.window.grab_set()
        self.on_save = on_save
        self.frame = ttk.Frame(self.window, padding=15)
        self.frame.pack(fill="both", expand=True)
        self.entries = {}
        self.row = 0

    def add_entry(self, key: str, label: str, value: str = "", readonly: bool = False):
        """Додає текстове поле з підписом."""
        ttk.Label(self.frame, text=label).grid(row=self.row, column=0, sticky="w", pady=5, padx=(0, 10))
        entry = ttk.Entry(self.frame, width=32)
        entry.grid(row=self.row, column=1, sticky="ew", pady=5)
        entry.insert(0, value)
        if readonly:
            entry.configure(state="readonly")
        self.entries[key] = entry
        self.row += 1
        return entry

    def add_combo(self, key: str, label: str, values, value: str = ""):
        """Додає випадний список; без значення вибирає перший елемент."""
        ttk.Label(self.frame, text=label).grid(row=self.row, column=0, sticky="w", pady=5, padx=(0, 10))
        combo = ttk.Combobox(self.frame, values=values, state="readonly", width=29)
        combo.grid(row=self.row, column=1, sticky="ew", pady=5)
        if value:
            combo.set(value)
        elif values:
            combo.current(0)
        self.entries[key] = combo
        self.row += 1
        return combo

    def add_buttons(self):
        """Додає кнопки «Зберегти» і «Скасувати»."""
        buttons = ttk.Frame(self.frame)
        buttons.grid(row=self.row, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(buttons, text="Зберегти", command=self.save).pack(side="left", padx=5)
        ttk.Button(buttons, text="Скасувати", command=self.window.destroy).pack(side="left", padx=5)
        self.frame.columnconfigure(1, weight=1)

    def values(self) -> dict:
        """Збирає дані з полів. Похідні форми доповнюють цей метод."""
        return {key: widget.get().strip() for key, widget in self.entries.items()}

    def save(self):
        """Передає дані на збереження; при помилці лишає форму відкритою."""
        try:
            self.on_save(**self.values())
        except (ValueError, KeyError) as error:
            messagebox.showerror("Помилка введення", str(error), parent=self.window)
            return
        self.window.destroy()


class GuestForm(BaseForm):
    """Форма додавання або редагування гостя."""

    def __init__(self, parent, on_save, guest=None):
        """Будує поля; при редагуванні телефон не можна змінити."""
        super().__init__(parent, "Редагування гостя" if guest else "Додавання гостя", on_save)
        self.is_edit = guest is not None
        self.add_entry("phone", "Телефон:", guest[0] if guest else "", readonly=self.is_edit)
        self.add_entry("last_name", "Прізвище:", guest[1] if guest else "")
        self.add_entry("first_name", "Ім'я:", guest[2] if guest else "")
        self.add_entry("middle_name", "По батькові:", guest[3] if guest else "")
        self.add_entry("email", "Email:", guest[4] if guest else "")
        self.add_buttons()

    def values(self) -> dict:
        """Додає ознаку редагування до даних форми."""
        values = super().values()
        values["editing"] = self.is_edit
        return values

class RoomForm(BaseForm):
    """Форма додавання або редагування номера."""

    def __init__(self, parent, on_save, type_names, room=None):
        """Будує поля; при редагуванні номер кімнати не можна змінити."""
        super().__init__(parent, "Редагування номера" if room else "Додавання номера", on_save)
        self.is_edit = room is not None
        self.add_combo("room_type", "Тип:", type_names, room[1] if room else "")
        self.add_entry("number", "Номер кімнати:", room[0] if room else "", readonly=self.is_edit)
        self.add_entry("capacity", "Місткість:", room[2] if room else "2")
        self.add_entry("price", "Ціна за ніч, грн:", room[3] if room else "")
        self.add_buttons()

    def values(self) -> dict:
        """Додає ознаку редагування до даних форми."""
        values = super().values()
        values["editing"] = self.is_edit
        return values


class BookingForm(BaseForm):
    """Форма додавання або редагування бронювання."""

    def __init__(self, parent, on_save, guests, rooms, booking=None):
        """Будує поля; при редагуванні вибирає гостя і номер з бронювання."""
        title = "Редагування бронювання" if booking else "Додавання бронювання"
        super().__init__(parent, title, on_save)
        self.booking_id = booking[0] if booking else None
        guest_values = [f"{guest[0]} | {guest[1]} {guest[2]}" for guest in guests]
        self.guest_lookup = {value.split(" | ", 1)[0]: value for value in guest_values}
        selected_guest = self.guest_lookup.get(booking[2], "") if booking else ""
        self.add_combo("guest", "Гість:", guest_values, selected_guest)
        room_values = [f"{number} | {description}" for number, description in rooms]
        selected_room = self.__find_room(room_values, booking[3]) if booking else ""
        self.add_combo("room", "Номер:", room_values, selected_room)
        self.add_entry("guests_count", "Кількість гостей:", booking[5] if booking else "1")
        self.add_entry("check_in", "Дата заїзду:", booking[6] if booking else "")
        self.add_entry("check_out", "Дата виїзду:", booking[7] if booking else "")
        self.add_buttons()

    @staticmethod
    def __find_room(room_values: list[str], number: str) -> str:
        """Шукає рядок списку для номера кімнати."""
        return next((value for value in room_values if value.startswith(f"{number} | ")), "")

    def values(self) -> dict:
        """Перетворює вибір у списках на телефон гостя і номер кімнати."""
        values = super().values()
        values["guest_phone"] = values.pop("guest").split(" | ", 1)[0]
        values["room_number"] = values.pop("room").split(" | ", 1)[0]
        values["booking_id"] = self.booking_id
        return values
