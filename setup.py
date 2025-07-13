"""Legacy *setup.py* retained for tooling that doesn’t yet understand
PEP 517/PEP 621.  It now forwards the metadata required by PyPI so that
`python -m build` and similar commands still produce a fully-compliant
distribution even if they fall back to executing this file.

NB: The canonical project metadata lives in *pyproject.toml* – **do not**
add new fields here unless strictly necessary.  Keep this stub minimal.
"""

from pathlib import Path

from setuptools import find_packages, setup


BASE_DIR = Path(__file__).resolve().parent


setup(
    # --- Mandatory metadata -------------------------------------------------
    name="reghelp-client",
    # Version is generated from Git tags via *setuptools_scm*
    use_scm_version={"fallback_version": "0.0.0"},

    # --- Brief description (the long one comes from README) ----------------
    description="Современная асинхронная Python библиотека для работы с REGHelp API",
    long_description=(BASE_DIR / "README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",

    # --- Packaging options --------------------------------------------------
    packages=find_packages(exclude=("tests*", "examples*", "docs*")),
    include_package_data=True,

    # Keep other metadata (authors, classifiers, deps) in *pyproject.toml*
) 