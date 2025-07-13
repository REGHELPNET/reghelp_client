"""Legacy stub for ``pip install .`` when ``pyproject.toml`` is ignored.

Все метаданные и зависимости теперь хранятся только в *pyproject.toml*.
Файл оставлен для совместимости со старыми экосистемами, которые требуют
``setup.py``. Он просто делегирует вызов ``setuptools.setup()`` и позволяет
``setuptools`` самому прочитать конфигурацию из ``pyproject.toml``.
"""

from setuptools import setup


if __name__ == "__main__":
    setup() 