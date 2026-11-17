# ШІ: Claude (Opus 5.5) – каркас класу HotelService (конструктор, сигнатури методів частини 1).
# Змінено: Реалізовано CRUD бронювань, перевірку конфліктів дат та автоматичне збереження з відкатом змін. CRUD гостей, пошук, фільтрацію, сортування, імпорт та експорт JSON.
import logging
import threading
import time
from contextlib import contextmanager
from datetime import date
from pathlib import Path

from model.booking import Booking
from model.guest import Guest
from model.room import Room, create_room
from service.overlap_checker import OverlapChecker
from service.repository import HotelRepository
from service.xml_report import OccupancyReport

logger = logging.getLogger(__name__)

class OperationCancelled(Exception):
    """Фонову операцію скасував користувач."""

class HotelService:
    """Бізнес-логіка готелю: CRUD, перевірки, пошук. Дані зберігаються автоматично."""
    SORT_KEYS = {
        "check_in": lambda b: b.check_in,
        "price": lambda b: b.calculate_total(),
        "room_number": lambda b: b.room.number,
    }

    def __init__(self, repository: HotelRepository, checker: OverlapChecker):
        self.__repository = repository
        self.__checker = checker
        self.__lock = threading.Lock()
        self.__rooms, self.__guests, self.__bookings = repository.load()

    def get_rooms(self) -> list[Room]:
        """Повертає список усіх номерів."""
        with self.__lock:
            return list(self.__rooms.values())

    def get_guests(self) -> list[Guest]:
        """Повертає список усіх гостей."""
        with self.__lock:
            return list(self.__guests.values())

    def get_bookings(self) -> list[Booking]:
        """Повертає список усіх бронювань."""
        with self.__lock:
            return list(self.__bookings.values())

    def create_booking(self, guest_phone: str, room_number: int, guests_count: int,
                       check_in: date, check_out: date) -> Booking:
        """Створює нове бронювання."""
        with self.__lock, self.__transaction():
            new_id = max(self.__bookings, default=0) + 1
            booking = Booking(new_id, self.__get_guest(guest_phone), self.__get_room(room_number),
                              guests_count, check_in, check_out)
            self.__check_free(booking)
            self.__bookings[new_id] = booking
        logger.info("Створено бронювання №%s для гостя %s, номер %s.", new_id, guest_phone, room_number)
        return booking

    def update_booking(self, booking_id: int, guest_phone: str, room_number: int,
                       guests_count: int, check_in: date, check_out: date) -> Booking:
        """Змінює існуюче бронювання (створює новий об'єкт з тим самим id)."""
        with self.__lock, self.__transaction():
            self.__get_booking(booking_id)
            booking = Booking(booking_id, self.__get_guest(guest_phone), self.__get_room(room_number),
                              guests_count, check_in, check_out)
            self.__check_free(booking, exclude_id=booking_id)
            self.__bookings[booking_id] = booking
        logger.info("Змінено бронювання №%s.", booking_id)
        return booking

    def cancel_booking(self, booking_id: int) -> None:
        """Скасовує (видаляє) бронювання."""
        with self.__lock, self.__transaction():
            self.__get_booking(booking_id)
            del self.__bookings[booking_id]
        logger.info("Видалено бронювання №%s.", booking_id)

    def add_guest(self, phone: str, last_name: str, first_name: str,
                  middle_name: str = "", email: str = "") -> Guest:
        """Додає нового гостя."""
        with self.__lock, self.__transaction():
            guest = Guest(phone, last_name, first_name, middle_name, email)
            if guest.phone in self.__guests:
                raise ValueError(f"Гість з телефоном {guest.phone} вже існує.")
            self.__guests[guest.phone] = guest
        logger.info("Додано гостя %s (%s).", guest.full_name, guest.phone)
        return guest

    def update_guest(self, phone: str, last_name: str, first_name: str,
                     middle_name: str = "", email: str = "") -> Guest:
        """Змінює дані гостя і замінює його в усіх його бронюваннях."""
        with self.__lock, self.__transaction():
            self.__get_guest(phone)
            guest = Guest(phone, last_name, first_name, middle_name, email)
            self.__guests[phone] = guest
            for b in self.__bookings_of(phone):
                self.__bookings[b.booking_id] = Booking(
                    b.booking_id, guest, b.room, b.guests_count, b.check_in, b.check_out)
        logger.info("Змінено дані гостя %s (%s).", guest.full_name, guest.phone)
        return guest

    def delete_guest(self, phone: str) -> None:
        """Видаляє гостя, якщо він не має бронювань."""
        with self.__lock, self.__transaction():
            self.__get_guest(phone)
            bookings = self.__bookings_of(phone)
            if bookings:
                ids = ", ".join(f"№{b.booking_id}" for b in bookings)
                raise ValueError(f"Неможливо видалити гостя. Він має бронювання: {ids}.")
            del self.__guests[phone]
        logger.info("Видалено гостя %s.", phone)

    def add_room(self, room_type: str, number: int, capacity: int, price_per_night: float) -> Room:
        """Додає новий номер."""
        with self.__lock, self.__transaction():
            room = create_room(room_type, number, capacity, price_per_night)
            if room.number in self.__rooms:
                raise ValueError(f"Номер {room.number} вже існує.")
            self.__rooms[room.number] = room
        logger.info("Додано номер %s (%s).", room.number, room.room_type)
        return room

    def update_room(self, room_type: str, number: int, capacity: int, price_per_night: float) -> Room:
        """Змінює номер і замінює його в усіх бронюваннях цього номера."""
        with self.__lock, self.__transaction():
            self.__get_room(number)
            room = create_room(room_type, number, capacity, price_per_night)
            bookings = self.__bookings_in_room(number)
            most_guests = max((b.guests_count for b in bookings), default=0)
            if most_guests > room.capacity:
                raise ValueError(f"Є бронювання на {most_guests} гостей, місткість не може бути меншою.")
            self.__rooms[number] = room
            for b in bookings:
                self.__bookings[b.booking_id] = Booking(
                    b.booking_id, b.guest, room, b.guests_count, b.check_in, b.check_out)
        logger.info("Змінено номер %s.", number)
        return room

    def delete_room(self, number: int) -> None:
        """Видаляє номер, якщо на нього немає бронювань."""
        with self.__lock, self.__transaction():
            self.__get_room(number)
            bookings = self.__bookings_in_room(number)
            if bookings:
                ids = ", ".join(f"№{b.booking_id}" for b in bookings)
                raise ValueError(f"Неможливо видалити номер. На нього є бронювання: {ids}.")
            del self.__rooms[number]
        logger.info("Видалено номер %s.", number)

    def filter_rooms(self, room_type: str | None = None, check_in: date | None = None,
                     check_out: date | None = None) -> list[Room]:
        """Повертає номери вибраного типу, вільні на всі дати періоду."""
        if (check_in is None) != (check_out is None):
            raise ValueError("Вкажіть обидві дати: заїзд і виїзд.")
        if check_in and check_out <= check_in:
            raise ValueError("Дата виїзду має бути пізніше дати заїзду.")
        room_type = (room_type or "").strip().casefold()

        with self.__lock:
            rooms = [r for r in self.__rooms.values()
                     if not room_type or room_type in (r.TYPE, r.room_type.casefold())]
            if check_in is None:
                return rooms
            return [r for r in rooms if not self.__checker.find_conflicts(
                r.number, check_in, check_out, self.__bookings)]

    def search_guests(self, text: str) -> list[Guest]:
        """Шукає гостей за ПІБ або телефоном. Порядок слів не важливий."""
        words = (text or "").strip().casefold().split()
        with self.__lock:
            return [g for g in self.__guests.values()
                    if all(word in g.full_name.casefold() or word in g.phone for word in words)]

    def search_bookings(self, text: str) -> list[Booking]:
        """Шукає бронювання за прізвищем, ім'ям або телефоном гостя."""
        query = (text or "").strip().casefold()
        with self.__lock:
            return [b for b in self.__bookings.values()
                    if query in b.guest.full_name.casefold() or query in b.guest.phone]

    def filter_bookings(self, room_type: str | None = None, date_from: date | None = None,
                        date_to: date | None = None, room_number: int | None = None) -> list[Booking]:
        """Фільтрує бронювання за типом номера, номером кімнати та періодом дат."""
        if date_from and date_to and date_from >= date_to:
            raise ValueError("Кінцева дата має бути пізніше початкової.")
        room_type = (room_type or "").strip().casefold()

        with self.__lock:
            return [b for b in self.__bookings.values()
                    if (not room_type or room_type in (b.room.TYPE, b.room.room_type.casefold()))
                    and (room_number is None or b.room.number == room_number)
                    and (date_from is None or b.check_out > date_from)
                    and (date_to is None or b.check_in < date_to)]

    def sort_bookings(self, bookings: list[Booking], key: str, reverse: bool = False) -> list[Booking]:
        """Сортує передані бронювання за датою заїзду, вартістю або номером кімнати."""
        if key not in self.SORT_KEYS:
            raise ValueError(f"Невідомий параметр сортування. Доступні: {', '.join(self.SORT_KEYS)}.")
        return sorted(bookings, key=self.SORT_KEYS[key], reverse=reverse)

    def import_from_file(self, path: str | Path, cancel_event: threading.Event | None = None) -> None:
        """Замінює всі дані готелю даними з вибраного JSON-файлу.

        Скасування перевіряється після читання файлу і під час перевірки конфліктів.
        Якщо скасовано всередині транзакції, дані повертаються до попереднього стану.
        """
        path = Path(path)
        if not path.is_file():
            raise FileNotFoundError(f"Файл {path} не знайдено.")
        rooms, guests, bookings = self.__repository.load(path)
        self.__check_cancel(cancel_event)

        with self.__lock, self.__transaction():
            self.__rooms, self.__guests, self.__bookings = rooms, guests, bookings
            self.__check_import_conflicts(bookings, cancel_event)
        logger.info("Дані успішно імпортовано з файлу %s.", path)

    @staticmethod
    def __check_cancel(cancel_event: threading.Event | None) -> None:
        """Зупиняє операцію, якщо користувач натиснув «Скасувати»."""
        if cancel_event is not None and cancel_event.is_set():
            raise OperationCancelled("Операцію скасовано користувачем.")

    def export_to_file(self, path: str | Path) -> None:
        """Експортує всі дані готелю у вибраний JSON-файл."""
        with self.__lock:
            HotelRepository(Path(path)).save(self.__rooms, self.__guests, self.__bookings)
        logger.info("Дані успішно експортовано у файл %s.", path)

    def export_occupancy_report(self, path: str | Path,
                                start_date: date, end_date: date) -> None:
        """Створює XML-звіт про завантаженість номерів."""
        with self.__lock:
            OccupancyReport.save(
                list(self.__rooms.values()),
                list(self.__bookings.values()),
                start_date, end_date, path)
        logger.info("XML-звіт збережено у файл %s.", path)

    @contextmanager
    def __transaction(self):
        """Зберігає зміни у файл; якщо виникла помилка – повертає дані до стану перед зміною."""
        backup = (dict(self.__rooms), dict(self.__guests), dict(self.__bookings))
        try:
            yield
            self.__repository.save(self.__rooms, self.__guests, self.__bookings)
        except Exception:
            self.__rooms, self.__guests, self.__bookings = backup
            raise

    def __check_import_conflicts(self, bookings: dict[int, Booking],
                                 cancel_event: threading.Event | None = None) -> None:
        """Перевіряє перетини дат імпортованих бронювань у кількох потоках."""
        started = time.perf_counter()
        conflicts = self.__checker.find_all_conflicts(bookings, cancel_event=cancel_event)
        self.__check_cancel(cancel_event)
        logger.info("Перевірка перетинів: %s бронювань за %.3f с.",
                    len(bookings), time.perf_counter() - started)
        if conflicts:
            first, second = min(conflicts, key=lambda pair: pair[0].room.number)
            raise ValueError(
                f"Номер {first.room.number} зайнятий на ці дати "
                f"(бронювання №{first.booking_id} та №{second.booking_id}).")

    def __check_free(self, booking: Booking, exclude_id: int | None = None) -> None:
        """Перевіряє, що номер вільний на дати бронювання."""
        conflicts = self.__checker.find_conflicts(
            booking.room.number, booking.check_in, booking.check_out, self.__bookings, exclude_id)
        if conflicts:
            ids = ", ".join(f"№{b.booking_id}" for b in conflicts)
            raise ValueError(f"Номер {booking.room.number} зайнятий на ці дати (бронювання {ids}).")

    def __bookings_of(self, phone: str) -> list[Booking]:
        """Повертає бронювання гостя."""
        return [b for b in self.__bookings.values() if b.guest.phone == phone]

    def __bookings_in_room(self, number: int) -> list[Booking]:
        """Повертає бронювання номера."""
        return [b for b in self.__bookings.values() if b.room.number == number]

    def __get_booking(self, booking_id: int) -> Booking:
        """Знаходить бронювання за id."""
        booking = self.__bookings.get(booking_id)
        if booking is None:
            raise ValueError(f"Бронювання №{booking_id} не знайдено.")
        return booking

    def __get_guest(self, phone: str) -> Guest:
        """Знаходить гостя за номером телефону."""
        guest = self.__guests.get(phone)
        if guest is None:
            raise ValueError(f"Гостя з телефоном {phone} не знайдено.")
        return guest

    def __get_room(self, number: int) -> Room:
        """Знаходить номер за його номером."""
        room = self.__rooms.get(number)
        if room is None:
            raise ValueError(f"Номер {number} не знайдено.")
        return room