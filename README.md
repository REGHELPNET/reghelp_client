# REGHelp Python Client / REGHelp Python Client (Русская версия ниже)

![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![Version](https://img.shields.io/badge/version-1.3.3-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

---

## 📑 Table of contents / Содержание

1. [Features](#-features)
2. [Installation](#-installation)
3. [Quick start](#-quick-start)
4. [What's new](#-whats-new-in-133)
5. [Environment variables](#-environment-variables)
6. [Testing](#-testing)
7. [Contributing](#-contributing)
8. [FAQ](#-faq)
9. [Changelog](#-changelog)

---

## 🇬🇧 English

Modern asynchronous Python library for interacting with the REGHelp Key API. It supports all services: Push tokens, Email, Integrity, Turnstile, VoIP Push and Recaptcha Mobile.

### 🚀 Features

* **Asynchronous first** – full `async`/`await` support powered by `httpx`.
* **Type-safe** – strict typing with Pydantic data models.
* **Retries with exponential back-off** built-in.
* **Smart rate-limit handling** (provider-configurable).
* **Async context-manager** for automatic resource management.
* **Webhook support** out of the box.
* **Comprehensive error handling** with dedicated exception classes.

### 🆕 What's new in 1.3.3

* `proxy` parameter in `get_recaptcha_mobile_token()` and `RecaptchaMobileRequest` model is now **optional** (`None` by default). Proxy parameters are only included in the request when explicitly provided.
* Added `processing` status to `TaskStatus` enum — Recaptcha Mobile API returns this status while a task is being executed.

### What was new in 1.3.1

* `wait_for_result` now returns task data even when `status="error"`, so your code can decide how to handle failures.
* All `get_*_status` methods return the full API payload instead of raising when `status="error"`.
* `set_push_status` treats HTTP 200 responses with a valid balance as success, even if `status="error"`.
* `get_turnstile_token` accepts new `actor` and `scope` parameters and forwards them to the API.

### What was new in 1.2.4

* Added support for the `submitted` task status in client models.
* Masked `apiKey` in debug logs.
* Preserved `task_id` across 429 retries for better diagnostics.
* Generalized rate-limit messaging (limits are provider-controlled).
* Updated documentation and examples (no longer read tokens from create responses).

### What was new in 1.2.3

* **Improved error handling for `TASK_NOT_FOUND`** – when task ID is known, it returns `TaskNotFoundError` with the specific ID; otherwise it raises a generic `RegHelpError` instead of the confusing "unknown" message.

### What was new in 1.2.2

* **Fixed `TaskNotFoundError`** – now shows the real task ID instead of "unknown" when a task is not found.
* **Improved error handling** – better reporting for status methods with correct task context.

### What was new in 1.2.1

* **Increased proxy configuration limits** – proxy address up to 255 characters, login up to 128, password up to 256.
* **Enhanced `ProxyConfig` validation** – improved support for long domain names and credentials.

### What was new in 1.2.0

* **Standard Integrity tokens** – request them via `get_integrity_token(..., token_type="std")`.
* **`IntegrityTokenType` enum** for type-safe token selection.
* Public exports for `AppDevice`, `IntegrityStatusResponse`, `VoipStatusResponse`, `IntegrityTokenType` from the package root.
* `get_integrity_token()` switched to keyword-only parameters for new options while staying backward compatible.

### 📦 Installation

```bash
pip install reghelp-client
```

For development:

```bash
pip install "reghelp-client[dev]"
```

### 🔧 Quick start

```python
import asyncio
from reghelp_client import RegHelpClient, AppDevice, EmailType

async def main():
    async with RegHelpClient("your_api_key") as client:
        # Check balance
        balance = await client.get_balance()
        print(f"Balance: {balance.balance} {balance.currency}")
        
        # Get Telegram iOS push token
        task = await client.get_push_token(
            app_name="tgiOS",
            app_device=AppDevice.IOS
        )
        print(f"Task created: {task.id}")
        
        # Wait for result
        result = await client.wait_for_result(task.id, "push")
        print(f"Push token: {result.token}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

# RU Русская версия

Современная асинхронная Python библиотека для работы с REGHelp Key API. Поддерживает все сервисы: Push tokens, Email, Integrity, Turnstile, VoIP Push, Recaptcha Mobile.

## 🚀 Возможности

- **Асинхронность**: Полная поддержка async/await
- **Типизация**: Полная типизация с Pydantic моделями
- **Retry логика**: Автоматические повторы с exponential backoff
- **Rate limiting**: Умная обработка rate limits (динамические лимиты провайдера)
- **Context manager**: Поддержка async context manager
- **Webhook support**: Поддержка webhook уведомлений
- **Comprehensive error handling**: Детальная обработка всех ошибок API

### 🆕 Что нового в 1.3.3

* Параметр `proxy` в `get_recaptcha_mobile_token()` и модели `RecaptchaMobileRequest` стал **необязательным** (по умолчанию `None`). Прокси-параметры добавляются в запрос только при явной передаче.
* Добавлен статус `processing` в перечисление `TaskStatus` — API Recaptcha Mobile возвращает этот статус в процессе выполнения задачи.

### Что было нового в 1.3.1

* `wait_for_result` возвращает объект статуса даже при `status="error"`, позволяя клиентскому коду принять решение самостоятельно.
* Методы `get_*_status` больше не выбрасывают исключение при `status="error"`, а отдают полный ответ API.
* `set_push_status` учитывает ответы с корректным балансом при HTTP 200, даже если `status="error"`.
* `get_turnstile_token` поддерживает параметры `actor` и `scope` (прокидываются в API).

### Что было нового в 1.2.4

* Поддержан новый статус задач `submitted` в `TaskStatus`.
* Добавлено маскирование `apiKey` в debug-логах.
* Ретраи при `429` сохраняют `task_id` для диагностики.
* Обновлена документация, примеры и сообщения `RateLimitError`.

### Что было нового в 1.2.3

* Улучшена обработка ошибки `TASK_NOT_FOUND`.

### Что было нового в 1.2.1

* **Увеличенные лимиты для прокси конфигурации** — адрес прокси теперь может содержать до 255 символов, логин до 128 символов, а пароль до 256 символов.
* **Улучшенная валидация ProxyConfig** — расширенная поддержка длинных доменных имен и данных аутентификации.

### Что было нового в 1.2.0

* **Стандартные Integrity-токены** — используйте параметр `token_type="std"` в методе `get_integrity_token()`.
* Новый перечислитель **IntegrityTokenType** для строгой типизации.
* Экспорт `AppDevice`, `IntegrityStatusResponse`, `VoipStatusResponse`, `IntegrityTokenType` из корневого пакета.
* Сигнатура `get_integrity_token()` использует keyword-only параметры для новых опций, сохраняя совместимость с существующим кодом.

## 📦 Установка

```bash
pip install reghelp-client
```

Или для разработки:

```bash
pip install reghelp-client[dev]
```

## 🔧 Быстрый старт

```python
import asyncio
from reghelp_client import RegHelpClient, AppDevice, EmailType

async def main():
    async with RegHelpClient("your_api_key") as client:
        # Проверить баланс
        balance = await client.get_balance()
        print(f"Баланс: {balance.balance} {balance.currency}")
        
        # Получить push токен для Telegram iOS
        task = await client.get_push_token(
            app_name="tgiOS",
            app_device=AppDevice.IOS
        )
        print(f"Задача создана: {task.id}")
        
        # Ждать результат
        result = await client.wait_for_result(task.id, "push")
        print(f"Push токен: {result.token}")

if __name__ == "__main__":
    asyncio.run(main())
```

## 📚 Документация API

### Инициализация клиента

```python
from reghelp_client import RegHelpClient

# Базовое использование
client = RegHelpClient("your_api_key")

# С кастомными настройками
client = RegHelpClient(
    api_key="your_api_key",
    base_url="https://api.reghelp.net",
    timeout=30.0,
    max_retries=3,
    retry_delay=1.0
)

# Использование как context manager (рекомендуется)
async with RegHelpClient("your_api_key") as client:
    # Ваш код здесь
    pass
```

### 📱 Push Tokens

#### Получение push токена

```python
from reghelp_client import AppDevice

# Для Telegram iOS
task = await client.get_push_token(
    app_name="tgiOS",
    app_device=AppDevice.IOS,
    app_version="10.9.2",
    app_build="25345",
    ref="my_ref_tag"
)

# Для Telegram Android
task = await client.get_push_token(
    app_name="tg",
    app_device=AppDevice.ANDROID
)

# Проверить статус
status = await client.get_push_status(task.id)
if status.status == "done":
    print(f"Токен: {status.token}")
```

#### Поддерживаемые приложения

| Platform | app_name | Bundle ID |
|----------|----------|-----------|
| Android | `tg` | `org.telegram.messenger` |
| Android | `tg_beta` | `org.telegram.messenger.beta` |
| Android | `tg_web` | `org.telegram.messenger.web` |
| Android | `tg_x` | `org.thunderdog.challegram` |
| iOS | `tgiOS` | `ph.telegra.Telegraph` |

#### Отметка неуспешного токена

```python
from reghelp_client import PushStatusType

# Если токен оказался неработающим
await client.set_push_status(
    task_id="task_id",
    phone_number="+15551234567",
    status=PushStatusType.NOSMS
)
```

### 📧 Email Service

```python
from reghelp_client import EmailType

# Получить временный email
email_task = await client.get_email(
    app_name="tg",
    app_device=AppDevice.IOS,
    phone="+15551234567",
    email_type=EmailType.ICLOUD
)

print(f"Email: {email_task.email}")

# Ждать код подтверждения
email_status = await client.wait_for_result(email_task.id, "email")
print(f"Код: {email_status.code}")
```

### 🔒 Integrity Service

```python
import base64

# Генерируем nonce
nonce = base64.urlsafe_b64encode(b"your_nonce_data").decode()

# Получить integrity токен
integrity_task = await client.get_integrity_token(
    app_name="tg",
    app_device=AppDevice.ANDROID,
    nonce=nonce
)

# Ждать результат
result = await client.wait_for_result(integrity_task.id, "integrity")
print(f"Integrity токен: {result.token}")
```

### 🤖 Recaptcha Mobile

```python
from reghelp_client import ProxyConfig, ProxyType

# Решить recaptcha без прокси (proxy необязателен)
recaptcha_task = await client.get_recaptcha_mobile_token(
    app_name="org.telegram.messenger",
    app_device=AppDevice.ANDROID,
    app_key="6Lc-recaptcha-site-key",
    app_action="login",
)

# Или с прокси (поддерживает длинные значения)
proxy = ProxyConfig(
    type=ProxyType.HTTP,
    address="very-long-proxy-domain-name.example.com",  # до 255 символов
    port=8080,
    login="very_long_username_up_to_128_chars",  # до 128 символов
    password="very_long_password_up_to_256_characters"  # до 256 символов
)

recaptcha_task = await client.get_recaptcha_mobile_token(
    app_name="org.telegram.messenger",
    app_device=AppDevice.ANDROID,
    app_key="6Lc-recaptcha-site-key",
    app_action="login",
    proxy=proxy,
)

# Ждать результат
result = await client.wait_for_result(recaptcha_task.id, "recaptcha")
print(f"Recaptcha токен: {result.token}")
```

### 🔐 Turnstile

```python
# Решить Cloudflare Turnstile
turnstile_task = await client.get_turnstile_token(
    url="https://example.com/page",
    site_key="0x4AAAA...",
    action="login",  # опционально
    actor="test_bot",  # опционально
    scope="cf-turnstile",  # опционально
    proxy="http://proxy.example.com:8080"  # опционально
)

# Ждать результат
result = await client.wait_for_result(turnstile_task.id, "turnstile")
print(f"Turnstile токен: {result.token}")
```

### 📞 VoIP Push

```python
# Получить VoIP push токен
voip_task = await client.get_voip_token(
    app_name="tgiOS",
    ref="voip_ref"
)

# Ждать результат
result = await client.wait_for_result(voip_task.id, "voip")
print(f"VoIP токен: {result.token}")
```

### 🔄 Автоматическое ожидание результата

```python
# Автоматически ждать выполнения задачи
result = await client.wait_for_result(
    task_id="task_id",
    service="push",  # push, email, integrity, recaptcha, turnstile, voip
    timeout=180.0,   # максимальное время ожидания
    poll_interval=2.0  # интервал между проверками
)
```

### 🪝 Webhook поддержка

```python
# Создать задачу с webhook
task = await client.get_push_token(
    app_name="tgiOS",
    app_device=AppDevice.IOS,
    webhook="https://yourapp.com/webhook"
)

# Когда задача завершится, на указанный URL придет POST запрос
# с JSON данными аналогичными ответу get_status
```

## 🚨 Обработка ошибок

```python
from reghelp_client import (
    RegHelpError,
    RateLimitError,
    UnauthorizedError,
    TaskNotFoundError,
    NetworkError
)

try:
    task = await client.get_push_token("tgiOS", AppDevice.IOS)
except RateLimitError:
    print("Превышен лимит запросов")
except UnauthorizedError:
    print("Неверный API ключ")
except TaskNotFoundError as e:
    print(f"Задача не найдена: {e.task_id}")
except NetworkError as e:
    print(f"Сетевая ошибка: {e}")
except RegHelpError as e:
    print(f"API ошибка: {e}")
```

## ⚙️ Конфигурация

### Логирование

```python
import logging

# Включить debug логи
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("reghelp_client")
```

### Кастомный HTTP клиент

```python
import httpx

# Использовать свой HTTP клиент
custom_client = httpx.AsyncClient(
    timeout=60.0,
    verify=False  # отключить SSL проверку (не рекомендуется)
)

client = RegHelpClient(
    api_key="your_api_key",
    http_client=custom_client
)
```

## 🧪 Примеры для разных случаев

### Массовое получение токенов

```python
import asyncio

async def get_multiple_tokens():
    async with RegHelpClient("your_api_key") as client:
        # Создать несколько задач параллельно
        tasks = await asyncio.gather(*[
            client.get_push_token("tgiOS", AppDevice.IOS)
            for _ in range(5)
        ])
        
        # Ждать все результаты
        results = await asyncio.gather(*[
            client.wait_for_result(task.id, "push")
            for task in tasks
        ])
        
        for i, result in enumerate(results):
            print(f"Токен {i+1}: {result.token}")
```

### Работа с балансом

```python
async def manage_balance():
    async with RegHelpClient("your_api_key") as client:
        balance = await client.get_balance()
        
        if balance.balance < 10:
            print("Низкий баланс! Пополните аккаунт")
            return
            
        print(f"Текущий баланс: {balance.balance} {balance.currency}")
```

### Обработка длительных операций

```python
async def long_running_task():
    async with RegHelpClient("your_api_key") as client:
        task = await client.get_push_token("tgiOS", AppDevice.IOS)
        
        # Проверять статус с кастомным интервалом
        while True:
            status = await client.get_push_status(task.id)
            
            if status.status == "done":
                print(f"Готово! Токен: {status.token}")
                break
            elif status.status == "error":
                print(f"Ошибка: {status.message}")
                break
                
            print(f"Статус: {status.status}")
            await asyncio.sleep(5)  # проверять каждые 5 секунд
```

## 📋 Требования

- Python 3.8+
- httpx >= 0.27.0
- pydantic >= 2.0.0

## 📄 Лицензия

MIT License. См. [LICENSE](LICENSE) для деталей.

## 🤝 Поддержка

- Документация: https://reghelp.net/api-docs
- Поддержка: support@reghelp.net
- Issues: https://github.com/REGHELPNET/reghelp_client/issues

---

## 🌐 Environment variables / Переменные окружения

| Variable | Description | Example |
|----------|-------------|---------|
| `REGHELP_API_KEY` | Your personal API key | `demo_123abc` |
| `REGHELP_BASE_URL` | Override base URL if you host a private mirror | `https://api.reghelp.net` |
| `REGHELP_TIMEOUT` | Default request timeout in seconds | `30` |
| `REGHELP_MAX_RETRIES` | Max automatic retries on network errors | `3` |

> 💡 *Tip:* you can create a `.env` file and load it with [python-dotenv](https://github.com/theskumar/python-dotenv).

---

## 🧪 Testing / Тестирование

```bash
# clone repo and install dev extras
git clone https://github.com/REGHELPNET/reghelp_client.git
cd reghelp_client
pip install -e ".[dev]"

# unit tests + coverage
pytest -v --cov=reghelp_client --cov-report=term-missing
```

Additional commands:

* **Formatting** – `black reghelp_client/ tests/`
* **Linting** – `ruff check reghelp_client/ tests/ examples/`
* **Type checking** – `mypy reghelp_client/`

---

## 🛠️ Contributing / Вклад

1. Fork the repository and create your branch: `git checkout -b feat/my-feature`  
2. Install dev dependencies: `pip install -e ".[dev]"`  
3. Run `pre-commit install` to enable hooks.  
4. Ensure tests & linters pass: `pytest && ruff check . && mypy .`  
5. Submit a pull-request with a clear description of your changes.

We follow **Conventional Commits** for commit messages and the **Black** code style.

---

## ❓ FAQ / Часто задаваемые вопросы

<details>
<summary>How do I increase the request timeout?</summary>

```python
client = RegHelpClient("api_key", timeout=60.0)
```

</details>

<details>
<summary>Does the client support synchronous code?</summary>

No, the library is asynchronous-first. You can run it in synchronous code with `asyncio.run()`.

</details>

<details>
<summary>What is the difference between `Integrity` and `SafetyNet`?</summary>

`Integrity` refers to Google Play Integrity API while SafetyNet is deprecated. REGHelp supports the new Integrity API.

</details>

---

## 🗒️ Changelog

See [CHANGELOG.md](CHANGELOG.md) for a complete release history. 