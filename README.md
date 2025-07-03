# REGHelp Python Client / REGHelp Python Client (Русская версия ниже)

![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![Version](https://img.shields.io/badge/version-1.0.0-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## 🇬🇧 English

Modern asynchronous Python library for interacting with the REGHelp Key API. It supports all services: Push tokens, Email, Integrity, Turnstile, VoIP Push and Recaptcha Mobile.

### 🚀 Features

* **Asynchronous first** – full `async`/`await` support powered by `httpx`.
* **Type-safe** – strict typing with Pydantic data models.
* **Retries with exponential back-off** built-in.
* **Smart rate-limit handling** (50 requests per second).
* **Async context-manager** for automatic resource management.
* **Webhook support** out of the box.
* **Comprehensive error handling** with dedicated exception classes.

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
        print(f"Push token: {task.token}")
        
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
- **Rate limiting**: Умная обработка rate limits (50 rps)
- **Context manager**: Поддержка async context manager
- **Webhook support**: Поддержка webhook уведомлений
- **Comprehensive error handling**: Детальная обработка всех ошибок API

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

# Настройка прокси
proxy = ProxyConfig(
    type=ProxyType.HTTP,
    address="proxy.example.com",
    port=8080,
    login="username",  # опционально
    password="password"  # опционально
)

# Решить recaptcha
recaptcha_task = await client.get_recaptcha_mobile_token(
    app_name="org.telegram.messenger",
    app_device=AppDevice.ANDROID,
    app_key="6Lc-recaptcha-site-key",
    app_action="login",
    proxy=proxy
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
    action="login",
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
    print("Превышен лимит запросов (50/сек)")
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