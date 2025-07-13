import importlib


def test_basic_import():
    """Проверка, что пакет импортируется и содержит __version__."""
    pkg = importlib.import_module("reghelp_client")
    assert hasattr(pkg, "__version__") 