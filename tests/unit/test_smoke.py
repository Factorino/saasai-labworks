"""Smoke test: the package is installed and importable.

Deliberately trivial. Its job is to fail loudly when packaging breaks — a bad
wheel, a missing dependency group, or a container image built without the
project installed.
"""

import anamnesis


def test_package_is_importable() -> None:
    assert anamnesis.__name__ == "anamnesis"
