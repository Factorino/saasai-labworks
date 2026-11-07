from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Trapezoid:
    """Трапециевидная функция принадлежности.

    Степень равна 0 вне `[a, d]`, линейно растёт на `[a, b]`, равна 1 на
    `[b, c]` и линейно убывает на `[c, d]`. При `b == c` функция треугольная,
    при `a == b` или `c == d` — «плечо» с вертикальным краем на границе
    универсума.
    """

    a: float
    b: float
    c: float
    d: float

    def __post_init__(self) -> None:
        self._validate()

    def degree(self, x: float) -> float:
        """Степень принадлежности значения `x`, от 0 до 1."""
        if x < self.a or x > self.d:
            return 0.0
        if x < self.b:
            return (x - self.a) / (self.b - self.a)
        if x <= self.c:
            return 1.0
        return (self.d - x) / (self.d - self.c)

    def _validate(self) -> None:
        if not self.a <= self.b <= self.c <= self.d:
            raise ValueError(f"Trapezoid {self} must satisfy a <= b <= c <= d")
        if self.a == self.d:
            raise ValueError(f"Trapezoid {self} must not be a single point")
