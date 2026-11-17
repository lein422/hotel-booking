"""Вимірює T1 і Tn для перевірки перетинів дат на великому наборі бронювань.
Запуск з кореня проєкту: python tools/benchmark.py
Спершу створіть тестовий файл: python tools/generate_data.py
"""
import os
import statistics
import sys
import sysconfig
import time
from pathlib import Path

BASE_PATH = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_PATH))

from service.overlap_checker import OverlapChecker
from service.repository import HotelRepository

TEST_PATH = BASE_PATH / "data" / "hotel_test.json"
RUNS = 5
THREAD_COUNTS = (1, 2, 4, 8)

def measure(checker: OverlapChecker, bookings: dict, workers: int) -> float:
    """Повертає середній час перевірки за RUNS запусків."""
    times = []
    for _ in range(RUNS):
        started = time.perf_counter()
        checker.find_all_conflicts(bookings, workers=workers)
        times.append(time.perf_counter() - started)
    return statistics.mean(times)

def gil_enabled() -> bool:
    """Показує, чи працює GIL у цьому інтерпретаторі."""
    check = getattr(sys, "_is_gil_enabled", None)
    return check() if check else True

def main() -> None:
    if not TEST_PATH.is_file():
        print(f"Немає файлу {TEST_PATH}. Спершу запустіть tools/generate_data.py")
        return

    _, _, bookings = HotelRepository(TEST_PATH).load()
    checker = OverlapChecker()
    print(f"Python {sys.version.split()[0]}, ядер: {os.cpu_count()}, "
          f"GIL: {'увімкнено' if gil_enabled() else 'вимкнено'}, "
          f"free-threading збірка: {bool(sysconfig.get_config_var('Py_GIL_DISABLED'))}")
    print(f"Бронювань: {len(bookings)}, номерів: {len(checker.group_by_room(bookings))}, "
          f"запусків на кожен режим: {RUNS}\n")

    print(f"{'Потоків n':>10} | {'Tn, с':>8} | {'S = T1/Tn':>9} | {'E = S/n':>7}")
    print("-" * 44)
    t1 = None
    for workers in THREAD_COUNTS:
        tn = measure(checker, bookings, workers)
        t1 = t1 or tn
        speedup = t1 / tn
        print(f"{workers:>10} | {tn:>8.4f} | {speedup:>9.2f} | {speedup / workers:>7.2f}")


if __name__ == "__main__":
    main()
