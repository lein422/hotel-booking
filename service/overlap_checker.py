import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

from model.booking import Booking

DEFAULT_WORKERS = os.cpu_count() or 1

class OverlapChecker:
    """Перевіряє перетин дат бронювань."""

    @staticmethod
    def periods_overlap(a_in: date, a_out: date, b_in: date, b_out: date) -> bool:
        """Перевіряє, чи перетинаються два періоди."""
        return a_in < b_out and b_in < a_out

    def find_conflicts(
            self,
            room_number: int,
            check_in: date,
            check_out: date,
            bookings: dict[int, Booking],
            exclude_id: int | None = None
    ) -> list[Booking]:
        """Знаходить бронювання, які конфліктують із заданим періодом."""
        conflicts = []

        for booking in bookings.values():
            if booking.booking_id == exclude_id:
                continue

            if booking.room.number != room_number:
                continue

            if self.periods_overlap(booking.check_in, booking.check_out, check_in, check_out):
                conflicts.append(booking)

        return conflicts

    @staticmethod
    def group_by_room(bookings: dict[int, Booking]) -> dict[int, list[Booking]]:
        """Розкладає бронювання по номерах кімнат."""
        groups = {}
        for booking in bookings.values():
            groups.setdefault(booking.room.number, []).append(booking)
        return groups

    @staticmethod
    def find_room_conflict(room_bookings: list[Booking]) -> tuple[Booking, Booking] | None:
        """Шукає перший перетин дат у бронюваннях одного номера."""
        latest = None
        for booking in sorted(room_bookings, key=lambda item: item.check_in):
            if latest is not None and booking.check_in < latest.check_out:
                return latest, booking
            if latest is None or booking.check_out > latest.check_out:
                latest = booking
        return None

    def find_all_conflicts(self, bookings: dict[int, Booking], workers: int = DEFAULT_WORKERS,
                           cancel_event: threading.Event | None = None) -> list[tuple[Booking, Booking]]:
        """Перевіряє всі номери. Один потік – по черзі, кілька – через пул потоків."""
        groups = list(self.group_by_room(bookings).values())
        if workers <= 1:
            return self.__check_sequential(groups, cancel_event)
        return self.__check_parallel(groups, workers, cancel_event)

    def __check_sequential(self, groups: list[list[Booking]],
                           cancel_event: threading.Event | None) -> list[tuple[Booking, Booking]]:
        """Однопотоковий режим: номери перевіряються один за одним."""
        conflicts = []
        for group in groups:
            if cancel_event is not None and cancel_event.is_set():
                break
            conflict = self.find_room_conflict(group)
            if conflict:
                conflicts.append(conflict)
        return conflicts

    def __check_parallel(self, groups: list[list[Booking]], workers: int,
                         cancel_event: threading.Event | None) -> list[tuple[Booking, Booking]]:
        """Багатопотоковий режим: кожен номер – окрема задача в пулі.

        Потоки лише читають бронювання, а список conflicts заповнює тільки цей потік,
        тому блокування тут не потрібне.
        """
        conflicts = []
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="overlap") as pool:
            futures = [pool.submit(self.find_room_conflict, group) for group in groups]
            for future in as_completed(futures):
                if cancel_event is not None and cancel_event.is_set():
                    pool.shutdown(wait=False, cancel_futures=True)
                    break
                conflict = future.result()
                if conflict:
                    conflicts.append(conflict)
        return conflicts
