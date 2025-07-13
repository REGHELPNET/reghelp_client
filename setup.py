"""
Setup script для REGHelp Python Client Library.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Читаем README для long_description
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

# Читаем зависимости из requirements.txt
requirements_path = Path(__file__).parent / "reghelp_client" / "requirements.txt"
requirements = []
if requirements_path.exists():
    requirements = requirements_path.read_text(encoding="utf-8").strip().split("\n")

setup(
    name="reghelp-client",
    version="1.0.0",
    author="REGHelp Team",
    author_email="support@reghelp.net",
    description="Современная асинхронная Python библиотека для работы с REGHelp Key API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/REGHELPNET/reghelp_client",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Communications :: Email",
        "Typing :: Typed",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-httpx>=0.21.0",
            "black>=23.0.0",
            "mypy>=1.0.0",
            "ruff>=0.1.0",
        ],
    },
    keywords=[
        "reghelp",
        "api",
        "client",
        "async",
        "push",
        "email",
        "telegram",
        "integrity",
        "recaptcha",
        "turnstile",
        "voip",
    ],
    project_urls={
        "Bug Reports": "https://github.com/REGHELPNET/reghelp_client/issues",
        "Source": "https://github.com/REGHELPNET/reghelp_client",
        "Documentation": "https://docs.reghelp.net/",
    },
) 