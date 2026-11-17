# ШІ: Claude (Opus 5.5) – каркас абстрактного класу Room і властивість number.
# Змінено: додано TYPE та перевірку обов'язкових полів під час відновлення з JSON.
import math
from abc import ABC, abstractmethod

class Room(ABC):
    """Абстрактний номер готелю."""

    MAX_CAPACITY = 6
    TYPE = ""

    def __init__(self, number: int, capacity: int, price_per_night: float):
        if not isinstance(number, int) or isinstance(number, bool) or number <= 0:
            raise ValueError("Номер кімнати має бути додатним цілим числом.")
        self.__number = number
        self.capacity = capacity
        self.price_per_night = price_per_night

    @property
    def number(self) -> int:
        return self.__number

    @property
    def capacity(self) -> int:
        return self.__capacity

    @capacity.setter
    def capacity(self, value: int) -> None:
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("Місткість має бути цілим числом")
        if not 1 <= value <= self.MAX_CAPACITY:
            raise ValueError(f"Місткість має бути від 1 до {self.MAX_CAPACITY}")
        self.__capacity = value

    @property
    def price_per_night(self) -> float:
        return self.__price_per_night

    @price_per_night.setter
    def price_per_night(self, value: float) -> None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("Ціна має бути числом")
        if not math.isfinite(value) or value <= 0:
            raise ValueError("Ціна за ніч має бути додатним скінченним числом")
        self.__price_per_night = float(value)

    @property
    @abstractmethod
    def room_type(self) -> str:
        """Назва типу номера."""

    @abstractmethod
    def calculate_price(self, nights: int) -> float:
        """Вартість проживання за nights ночей."""

    @staticmethod
    def _check_nights(nights: int) -> None:
        """Перевіряє, що кількість ночей – ціле число більше 0."""
        if not isinstance(nights, int) or isinstance(nights, bool) or nights <= 0:
            raise ValueError("Кількість ночей має бути цілим числом більше 0")

    def to_dict(self) -> dict:
        return {
            "number": self.number,
            "type": self.TYPE,
            "capacity": self.capacity,
            "price_per_night": self.price_per_night
        }

    def __str__(self) -> str:
        return (
            f"№{self.number} ({self.room_type}), "
            f"місткість: {self.capacity}, "
            f"{self.price_per_night:.2f} грн/ніч" )

class StandardRoom(Room):
    """Стандартний номер: ціна залежить від кількості ночей."""

    TYPE = "standard"

    @property
    def room_type(self) -> str:
        return "Стандарт"

    def calculate_price(self, nights: int) -> float:
        self._check_nights(nights)
        return self.price_per_night * nights

class FamilyRoom(Room):
    """Сімейний номер: знижка 10% при проживанні від 7 ночей."""

    TYPE = "family"
    DISCOUNT_MIN_NIGHTS = 7
    DISCOUNT_RATE = 0.10

    @property
    def room_type(self) -> str:
        return "Сімейний"

    def calculate_price(self, nights: int) -> float:
        self._check_nights(nights)
        total = self.price_per_night * nights

        if nights >= self.DISCOUNT_MIN_NIGHTS:
            total *= (1 - self.DISCOUNT_RATE)

        return round(total, 2)

class Suite(Room):
    """Люкс: до вартості кожної ночі додається сніданок."""

    TYPE = "suite"
    BREAKFAST_PRICE = 300

    @property
    def room_type(self) -> str:
        return "Люкс"

    def calculate_price(self, nights: int) -> float:
        self._check_nights(nights)
        return (self.price_per_night + self.BREAKFAST_PRICE) * nights

ROOM_CLASSES = {"standard": StandardRoom, "family": FamilyRoom, "suite": Suite}
ROOM_TYPE_NAMES = {"standard": "Стандарт", "family": "Сімейний", "suite": "Люкс"}


def create_room(room_type: str, number: int, capacity: int, price_per_night: float) -> Room:
    """Створює номер потрібного класу за кодом типу або його назвою."""
    names = {name.casefold(): code for code, name in ROOM_TYPE_NAMES.items()}
    code = names.get(str(room_type).strip().casefold(), room_type)
    room_class = ROOM_CLASSES.get(code)
    if room_class is None:
        raise ValueError("Невідомий тип номера")
    return room_class(number=number, capacity=capacity, price_per_night=price_per_night)


def room_from_dict(data: dict) -> Room:
    if not isinstance(data, dict):
        raise ValueError("Запис номера має бути об'єктом JSON")

    required = ("number", "type", "capacity", "price_per_night")

    for key in required:
        if key not in data:
            raise ValueError(f"Відсутній обов'язковий ключ: {key}")

    if data["type"] not in ROOM_CLASSES:
        raise ValueError("Невідомий тип номера")

    return create_room(data["type"], data["number"], data["capacity"], data["price_per_night"])