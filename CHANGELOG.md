# Changelog

## [1.2.3] - 2025-01-13

### Improved
- Улучшена логика обработки ошибки TASK_NOT_FOUND:
  - Когда task_id известен: возвращается TaskNotFoundError с конкретным ID
  - Когда task_id неизвестен: возвращается общая RegHelpError вместо "unknown"
- Исключена путаница с сообщениями содержащими "unknown"

## [1.2.2] - 2025-01-13

### Fixed
- Исправлена ошибка TaskNotFoundError: теперь показывает реальный ID задачи вместо "unknown"
- Все методы *_status теперь правильно передают task_id для лучшей диагностики ошибок
- Исправлен последний русский комментарий в модели ProxyConfig.to_dict()

### Technical
- Обновлен метод _map_error_code для принятия параметра task_id
- Все методы статуса (get_*_status) теперь передают task_id в _make_request
- Улучшена система обработки ошибок для задач

## [1.2.1] - 2025-01-13

### Enhanced
- Увеличены лимиты для конфигурации прокси:
  - Адрес прокси: до 255 символов (ранее без ограничений, теперь с валидацией)
  - Логин прокси: до 128 символов
  - Пароль прокси: до 256 символов
- Улучшена валидация ProxyConfig для поддержки длинных доменных имен и данных аутентификации

### Technical
- Добавлены min_length и max_length валидаторы в модель ProxyConfig
- Обновлена документация с примерами новых возможностей

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

## [1.2.0] - 2025-07-20

### Added
- Экспорт `AppDevice`, `IntegrityStatusResponse`, `VoipStatusResponse`, `IntegrityTokenType` в корневом пакете для удобного импорта:
  ```python
  from reghelp_client import AppDevice, IntegrityStatusResponse
  ```
- Новый перечислитель `IntegrityTokenType` (`STD = "std"`).
- Поддержка необязательного параметра `type=std` в методе `get_integrity_token()`
  и модели `IntegrityRequest` (поле `token_type`).

### Changed
- Сигнатура `get_integrity_token()` стала keyword-only для новых параметров
  (`token_type`, `ref`, `webhook`) — это сохраняет обратную совместимость
  для существующего позиционного вызова.

### Fixed
- Исправлена проблема импорта `AppDevice` из корневого модуля.

### Migration notes
Если вы ранее вызывали `get_integrity_token()` позиционно:

```python
await client.get_integrity_token(app, device, nonce, ref="my_ref")
```

–– продолжайте использовать тот же вызов – поведение не изменилось. Для
получения стандартного Integrity-токена теперь можно указать:

```python
await client.get_integrity_token(app, device, nonce, token_type="std")
```

## [1.0.0] - 2025-01-12

### Added
- Первый релиз REGHelp Python Client
- Поддержка всех сервисов REGHelp API
- Асинхронная архитектура с httpx
- Полная типизация с Pydantic
- Обработка ошибок и retry логика
- Документация и примеры использования 