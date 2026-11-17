# ШІ: Claude (Opus 5.5) – приклад властивості з валідацією для Guest.
# Змінено: додано перевірку типів даних та виправлено перевірку імені.
import re

NAME_MAX_LEN = 50
NAME_PATTERN = re.compile(r"[A-Za-zА-Яа-яІіЇїЄєҐґ][A-Za-zА-Яа-яІіЇїЄєҐґ'ʼ\- ]*")

class Guest:
    """Гість готелю. Ідентифікується за номером телефону."""

    def __init__(self, phone: str, last_name: str, first_name: str,
                 middle_name: str = "", email: str = ""):
        self.__phone = self._validate_phone(phone)
        self.last_name = last_name
        self.first_name = first_name
        self.middle_name = middle_name
        self.email = email

    @property
    def phone(self) -> str:
        return self.__phone

    @staticmethod
    def _validate_phone(value: str) -> str:
        if value is not None and not isinstance(value, str):
            raise ValueError("Телефон має бути рядком")

        value = (value or "").strip()
        if not re.fullmatch(r"\+380\d{9}", value):
            raise ValueError("Неправильний формат телефону")
        return value

    @property
    def last_name(self) -> str:
        return self.__last_name

    @last_name.setter
    def last_name(self, value: str) -> None:
        self.__last_name = self._validate_name(value, "Прізвище")

    @property
    def first_name(self) -> str:
        return self.__first_name

    @first_name.setter
    def first_name(self, value: str) -> None:
        self.__first_name = self._validate_name(value, "Ім'я")

    @property
    def middle_name(self) -> str:
        return self.__middle_name

    @middle_name.setter
    def middle_name(self, value: str) -> None:
        if value is None or (isinstance(value, str) and not value.strip()):
            self.__middle_name = ""
        else:
            self.__middle_name = self._validate_name(value, "По батькові")

    @property
    def email(self) -> str:
        return self.__email

    @email.setter
    def email(self, value: str) -> None:
        if value is not None and not isinstance(value, str):
            raise ValueError("Email має бути рядком")

        value = (value or "").strip()
        if value and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            raise ValueError("Неправильний формат email")
        self.__email = value

    @staticmethod
    def _validate_name(value: str, field: str) -> str:
        if value is not None and not isinstance(value, str):
            raise ValueError(f"{field}: очікується рядок")

        value = (value or "").strip()
        if not value:
            raise ValueError(f"{field} не може бути порожнім")
        if len(value) > NAME_MAX_LEN:
            raise ValueError(f"{field}: не більше {NAME_MAX_LEN} символів")
        if not NAME_PATTERN.fullmatch(value):
            raise ValueError(f"{field} містить недопустимі символи")
        return value

    @property
    def full_name(self) -> str:
        parts = (self.last_name, self.first_name, self.middle_name)
        return " ".join(part for part in parts if part)

    def to_dict(self) -> dict:
        return {
            "phone": self.phone,
            "last_name": self.last_name,
            "first_name": self.first_name,
            "middle_name": self.middle_name,
            "email": self.email
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Guest":
        if not isinstance(data, dict):
            raise ValueError("Запис гостя має бути об'єктом JSON")

        required = ("phone", "last_name", "first_name")
        for key in required:
            if key not in data:
                raise ValueError(f"Відсутній обов'язковий ключ: {key}")

        return cls(
            phone=data["phone"],
            last_name=data["last_name"],
            first_name=data["first_name"],
            middle_name=data.get("middle_name", ""),
            email=data.get("email", "")
        )

    def __str__(self) -> str:
        return f"{self.full_name} ({self.phone})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, Guest):
            return NotImplemented
        return self.phone == other.phone

    def __hash__(self) -> int:
        return hash(self.phone)
