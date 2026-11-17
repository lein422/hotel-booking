from abc import ABC, abstractmethod

class Billable(ABC):
    """Інтерфейс для об'єктів, які мають вартість."""

    @abstractmethod
    def calculate_total(self) -> float:
        """Розраховує загальну вартість."""