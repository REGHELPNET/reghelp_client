# Changelog

## [1.1.4] - 2025-01-13

### Fixed
- Исправлена структура пакета для правильной публикации на PyPI
- Исправлен workflow для GitHub Actions
- Убраны предупреждения в pyproject.toml
- Синхронизированы версии между файлами

### Changed
- Переход на использование только pyproject.toml (убран setup.py)
- Улучшена структура проекта
- Обновлен workflow для автоматической публикации

### Technical
- Файлы пакета перемещены в подпапку `reghelp_client/reghelp_client/`
- Исправлены настройки setuptools в pyproject.toml
- Убраны конфликты между setup.py и pyproject.toml
- Исправлены пути в GitHub Actions workflow

## [1.1.5] - 2025-07-14

### Fixed
- Исправлена ошибка сборки: wheel без полей Name/Version (требовалась setuptools>=61)

### Changed
- Обновлена минимальная версия setuptools до 61.0 в pyproject.toml
- Версия пакета увеличена до 1.1.5

## [1.0.0] - 2025-01-12

### Added
- Первый релиз REGHelp Python Client
- Поддержка всех сервисов REGHelp API
- Асинхронная архитектура с httpx
- Полная типизация с Pydantic
- Обработка ошибок и retry логика
- Документация и примеры использования 