# ШІ: Claude (Opus 5.5) – каркас класу Booking для роботи з бронюваннями.
# Змінено: додано booking_id, відновлення з JSON та перевірку даних під час редагування.
from datetime import date

from model.guest import Guest
from model.room import Room
from model.billable import Billable

class Booking(Billable):
    """Клас для зберігання інформації про бронювання номера."""

    def __init__(
        self,
        booking_id: int,
        guest: Guest,
        room: Room,
        guests_count: int,
        check_in: date,
        check_out: date):
        if not isinstance(booking_id, int) or isinstance(booking_id, bool) or booking_id <= 0:
            raise ValueError("ID бронювання має бути додатним цілим числом.")

        self.__booking_id = booking_id
        self.__guests_count = 0
        self.guest = guest
        self.room = room
        self.guests_count = guests_count
        self.set_dates(check_in, check_out)

    @property
    def booking_id(self) -> int:
        return self.__booking_id

    @property
    def guest(self) -> Guest:
        return self.__guest

    @guest.setter
    def guest(self, value: Guest):
        if not isinstance(value, Guest):
            raise ValueError("Потрібно передати об'єкт класу Guest.")

        self.__guest = value

    @property
    def room(self) -> Room:
        return self.__room

    @room.setter
    def room(self, value: Room):
        if not isinstance(value, Room):
            raise ValueError("Потрібно передати об'єкт класу Room.")

        if self.__guests_count > value.capacity:
            raise ValueError("Кількість гостей перевищує місткість номера.")
        self.__room = value

    @property
    def guests_count(self) -> int:
        return self.__guests_count

    @guests_count.setter
    def guests_count(self, value: int):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("Кількість гостей має бути цілим числом.")

        if value < 1 or value > self.room.capacity:
            raise ValueError(f"Кількість гостей має бути від 1 до {self.room.capacity}.")
        self.__guests_count = value

    @property
    def check_in(self) -> date:
        return self.__check_in

    @property
    def check_out(self) -> date:
        return self.__check_out

    def set_dates(self, check_in: date, check_out: date):
        """Встановлює дати заїзду та виїзду."""

        if type(check_in) is not date:
            raise ValueError("Дата заїзду має бути типу date.")

        if type(check_out) is not date:
            raise ValueError("Дата виїзду має бути типу date.")

        if check_out <= check_in:
            raise ValueError("Дата виїзду має бути пізніше дати заїзду.")
        self.__check_in = check_in
        self.__check_out = check_out

    @property
    def nights(self) -> int:
        return (self.check_out - self.check_in).days

    def calculate_total(self) -> float:
        """Розраховує загальну вартість бронювання."""

        return self.room.calculate_price(self.nights)

    def to_dict(self) -> dict:
        """Перетворює бронювання на словник для збереження в JSON."""

        return {
            "id": self.booking_id,
            "guest_phone": self.guest.phone,
            "room_number": self.room.number,
            "guests_count": self.guests_count,
            "check_in": self.check_in.isoformat(),
            "check_out": self.check_out.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict, guests: dict, rooms: dict):
        """Створює бронювання зі словника."""
        if not isinstance(data, dict):
            raise ValueError("Дані бронювання мають бути словником.")

        required_fields = {"id", "guest_phone", "room_number", "check_in", "check_out"}
        missing_fields = required_fields - data.keys()

        if "guests_count" not in data and "guest_count" not in data:
            missing_fields.add("guests_count")

        if missing_fields:
            raise ValueError(f"У даних бронювання відсутні поля: {', '.join(sorted(missing_fields))}.")

        guest = guests.get(data["guest_phone"])
        if guest is None:
            raise ValueError(f"Гостя з телефоном {data['guest_phone']} не знайдено.")

        room = rooms.get(data["room_number"])
        if room is None:
            raise ValueError(f"Номер {data['room_number']} не знайдено.")

        guests_count = data.get("guests_count", data.get("guest_count"))

        try:
            check_in = date.fromisoformat(data["check_in"])
            check_out = date.fromisoformat(data["check_out"])
        except (TypeError, ValueError):
            raise ValueError("Неправильний формат дат бронювання.")

        return cls(
            booking_id=data["id"],
            guest=guest,
            room=room,
            guests_count=guests_count,
            check_in=check_in,
            check_out=check_out)

    def __str__(self) -> str:
        return (f"Бронювання №{self.booking_id}: "
            f"{self.guest}, номер {self.room.number}, "
            f"гостей: {self.guests_count}, "
            f"з {self.check_in} до {self.check_out}, "
            f"вартість: {self.calculate_total():.2f} грн")