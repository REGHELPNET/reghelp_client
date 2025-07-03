# REGHelp Python Client – Installation & Setup / Установка и настройка

## 🇬🇧 English

### 🚀 Quick installation

#### From PyPI (recommended)

```bash
pip install reghelp-client
```

#### For development

```bash
pip install "reghelp-client[dev]"
```

#### From source

```bash
git clone https://github.com/REGHELPNET/reghelp_client.git
cd reghelp_client
pip install -e .
```

## 📋 Requirements

* **Python**: 3.8+
* **Dependencies**:
  * `httpx >= 0.27.0` – HTTP client
  * `pydantic >= 2.0.0` – data validation & typing
  * `typing-extensions >= 4.5.0` – typing helpers

---

# 🇷🇺 Русская версия

## 🚀 Быстрая установка

### Из PyPI (рекомендуется)

```bash
pip install reghelp-client
```

### Для разработки

```bash
pip install reghelp-client[dev]
```

### Из исходного кода

```bash
git clone https://github.com/REGHELPNET/reghelp_client.git
cd reghelp_client
pip install -e .
```

## 📋 Требования

- **Python**: 3.8+
- **Зависимости**:
  - `httpx >= 0.27.0` - для HTTP запросов
  - `pydantic >= 2.0.0` - для валидации данных
  - `typing-extensions >= 4.5.0` - для типизации

## 🔧 Настройка

### Получение API ключа

1. Зарегистрируйтесь на [reghelp.net](https://reghelp.net)
2. Пополните баланс
3. Получите API ключ в личном кабинете

### Настройка переменных окружения

```bash
export REGHELP_API_KEY="your_api_key_here"
```

Или создайте файл `.env`:

```bash
REGHELP_API_KEY=your_api_key_here
```

## 🧪 Проверка установки

Создайте файл `test_installation.py`:

```python
import asyncio
from reghelp_client import RegHelpClient

async def test():
    async with RegHelpClient("your_api_key") as client:
        # Проверка доступности API
        health = await client.health_check()
        print(f"API доступен: {health}")
        
        # Проверка баланса
        balance = await client.get_balance()
        print(f"Баланс: {balance.balance} {balance.currency}")

if __name__ == "__main__":
    asyncio.run(test())
```

Запустите:

```bash
python test_installation.py
```

## 🛠️ Разработка

### Установка зависимостей для разработки

```bash
pip install -e ".[dev]"
```

### Запуск тестов

```bash
pytest
```

### Запуск тестов с покрытием

```bash
pytest --cov=reghelp_client --cov-report=html
```

### Форматирование кода

```bash
black reghelp_client/ tests/ examples/
```

### Линтинг

```bash
ruff check reghelp_client/ tests/ examples/
```

### Проверка типов

```bash
mypy reghelp_client/
```

## 📁 Структура проекта

```
reghelp_client/
├── reghelp_client/           # Основная библиотека
│   ├── __init__.py          # Экспорты
│   ├── client.py            # Основной клиент
│   ├── models.py            # Модели данных
│   ├── exceptions.py        # Исключения
│   └── requirements.txt     # Зависимости
├── examples/                # Примеры использования
│   └── basic_usage.py       # Базовый пример
├── tests/                   # Тесты
│   └── test_client.py       # Тесты клиента
├── README.md                # Основная документация
├── INSTALL.md              # Инструкции по установке
├── setup.py                # Установка (legacy)
├── pyproject.toml          # Современная конфигурация
└── requirements.txt        # Зависимости разработки
```

## 🔍 Примеры использования

### Базовый пример

```python
import asyncio
from reghelp_client import RegHelpClient, AppDevice

async def main():
    async with RegHelpClient("your_api_key") as client:
        # Получить push токен
        task = await client.get_push_token(
            app_name="tgiOS",
            app_device=AppDevice.IOS
        )
        
        # Ждать результат
        result = await client.wait_for_result(task.id, "push")
        print(f"Токен: {result.token}")

asyncio.run(main())
```

### С обработкой ошибок

```python
import asyncio
from reghelp_client import (
    RegHelpClient, 
    RegHelpError, 
    RateLimitError,
    UnauthorizedError
)

async def safe_example():
    try:
        async with RegHelpClient("your_api_key") as client:
            balance = await client.get_balance()
            print(f"Баланс: {balance.balance}")
            
    except UnauthorizedError:
        print("Неверный API ключ")
    except RateLimitError:
        print("Превышен лимит запросов")
    except RegHelpError as e:
        print(f"Ошибка API: {e}")

asyncio.run(safe_example())
```

## 🌐 Переменные окружения

| Переменная | Описание | Пример |
|------------|----------|---------|
| `REGHELP_API_KEY` | API ключ | `demo_123abc` |
| `REGHELP_BASE_URL` | Базовый URL API | `https://api.reghelp.net` |
| `REGHELP_TIMEOUT` | Таймаут запросов (сек) | `30` |
| `REGHELP_MAX_RETRIES` | Максимум повторов | `3` |

## 🔒 Безопасность

### Хранение API ключей

❌ **НЕ ДЕЛАЙТЕ ТАК:**

```python
# Не храните ключи в коде!
client = RegHelpClient("real_api_key_here")
```

✅ **ПРАВИЛЬНО:**

```python
import os
api_key = os.getenv("REGHELP_API_KEY")
client = RegHelpClient(api_key)
```

### Логирование

Будьте осторожны с логированием - не выводите API ключи:

```python
import logging

# Настройка безопасного логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("reghelp_client")

# Фильтр для скрытия API ключей
class APIKeyFilter(logging.Filter):
    def filter(self, record):
        if hasattr(record, 'msg'):
            record.msg = str(record.msg).replace(api_key, "[HIDDEN]")
        return True

logger.addFilter(APIKeyFilter())
```

## 🐛 Отладка

### Включение debug логов

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Просмотр HTTP запросов

```python
import httpx
import logging

# Логирование httpx
logging.getLogger("httpx").setLevel(logging.DEBUG)
```

### Кастомный HTTP клиент

```python
import httpx
from reghelp_client import RegHelpClient

# Клиент с отладкой
http_client = httpx.AsyncClient(
    timeout=60.0,
    verify=False,  # Только для отладки!
)

client = RegHelpClient(
    api_key="your_key",
    http_client=http_client
)
```

## 📊 Мониторинг производительности

### Измерение времени запросов

```python
import time
import asyncio
from reghelp_client import RegHelpClient

async def benchmark():
    async with RegHelpClient("your_api_key") as client:
        start = time.time()
        
        balance = await client.get_balance()
        
        elapsed = time.time() - start
        print(f"Запрос занял: {elapsed:.2f} сек")

asyncio.run(benchmark())
```

### Параллельные запросы

```python
import asyncio
from reghelp_client import RegHelpClient, AppDevice

async def parallel_requests():
    async with RegHelpClient("your_api_key") as client:
        # Создаем 5 задач параллельно
        tasks = await asyncio.gather(*[
            client.get_push_token("tgiOS", AppDevice.IOS)
            for _ in range(5)
        ])
        
        print(f"Создано {len(tasks)} задач")

asyncio.run(parallel_requests())
```

## 🆘 Устранение неполадок

### Частые проблемы

1. **"Invalid API key"**
   - Проверьте правильность API ключа
   - Убедитесь, что ключ активен

2. **"Rate limit exceeded"**
   - Снизьте частоту запросов
   - Используйте retry с увеличивающейся задержкой

3. **"Connection timeout"**
   - Увеличьте таймаут
   - Проверьте интернет соединение

4. **"Task not found"**
   - Проверьте правильность ID задачи
   - Задача могла устареть (срок жизни ~1 час)

### Получение помощи

- 📧 Email: support@reghelp.net
- 🐛 Issues: https://github.com/REGHELPNET/reghelp_client/issues
- 📖 Документация: https://reghelp.net/api-docs

## 📈 Обновления

### Проверка версии

```python
import reghelp_client
print(reghelp_client.__version__)
```

### Обновление библиотеки

```bash
pip install --upgrade reghelp-client
```

### Миграция с версии 0.x

При обновлении с более старых версий возможны breaking changes. Проверьте CHANGELOG.md для деталей. 