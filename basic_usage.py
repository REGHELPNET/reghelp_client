#!/usr/bin/env python3
"""
Пример базового использования REGHelp Python Client.

Демонстрирует основные возможности библиотеки:
- Проверка баланса
- Получение push токенов
- Работа с email сервисом
- Обработка ошибок
"""

import asyncio
import logging
import os
from typing import Optional

from reghelp_client import (
    RegHelpClient,
    AppDevice,
    EmailType,
    ProxyConfig,
    ProxyType,
    RegHelpError,
    RateLimitError,
    UnauthorizedError,
)


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def check_balance(client: RegHelpClient) -> None:
    """Проверить текущий баланс аккаунта."""
    try:
        balance = await client.get_balance()
        logger.info(f"💰 Текущий баланс: {balance.balance} {balance.currency}")
        
        if balance.balance < 10:
            logger.warning("⚠️ Низкий баланс! Рекомендуется пополнить аккаунт")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при получении баланса: {e}")


async def get_telegram_push_token(client: RegHelpClient) -> Optional[str]:
    """Получить push токен для Telegram iOS."""
    try:
        logger.info("📱 Создание задачи для push токена Telegram iOS...")
        
        # Создать задачу
        task = await client.get_push_token(
            app_name="tgiOS",
            app_device=AppDevice.IOS,
            ref="demo_example"
        )
        
        logger.info(f"✅ Задача создана: {task.id} (цена: {task.price} руб.)")
        
        # Ждать результат с автоматическим polling
        result = await client.wait_for_result(
            task_id=task.id,
            service="push",
            timeout=60.0,  # 1 минута
            poll_interval=3.0  # проверять каждые 3 секунды
        )
        
        if result.token:
            logger.info(f"🎉 Push токен получен: {result.token[:50]}...")
            return result.token
        else:
            logger.error("❌ Токен не получен")
            return None
            
    except Exception as e:
        logger.error(f"❌ Ошибка при получении push токена: {e}")
        return None


async def get_temporary_email(client: RegHelpClient) -> Optional[str]:
    """Получить временный email адрес."""
    try:
        logger.info("📧 Получение временного email адреса...")
        
        # Получить email
        email_task = await client.get_email(
            app_name="tg",
            app_device=AppDevice.IOS,
            phone="+15551234567",  # Тестовый номер
            email_type=EmailType.ICLOUD
        )
        
        logger.info(f"✅ Email получен: {email_task.email}")
        
        # Можно ждать код подтверждения
        logger.info("⏳ Ожидание кода подтверждения (30 сек)...")
        
        try:
            email_result = await client.wait_for_result(
                task_id=email_task.id,
                service="email",
                timeout=30.0
            )
            
            if email_result.code:
                logger.info(f"📬 Код подтверждения: {email_result.code}")
                return email_result.code
                
        except asyncio.TimeoutError:
            logger.info("⏰ Код подтверждения не получен за 30 секунд")
        
        return email_task.email
        
    except Exception as e:
        logger.error(f"❌ Ошибка при получении email: {e}")
        return None


async def demonstrate_turnstile(client: RegHelpClient) -> Optional[str]:
    """Демонстрация решения Turnstile задачи."""
    try:
        logger.info("🔐 Решение Cloudflare Turnstile...")
        
        task = await client.get_turnstile_token(
            url="https://demo.example.com",
            site_key="0x4AAAA-demo-site-key",
            action="demo",
        )
        
        logger.info(f"✅ Задача Turnstile создана: {task.id}")
        
        # Ждать результат
        result = await client.wait_for_result(
            task_id=task.id,
            service="turnstile",
            timeout=120.0
        )
        
        if result.token:
            logger.info(f"🎉 Turnstile токен: {result.token[:50]}...")
            return result.token
        
    except Exception as e:
        logger.error(f"❌ Ошибка Turnstile: {e}")
        return None


async def demonstrate_error_handling(client: RegHelpClient) -> None:
    """Демонстрация обработки различных ошибок."""
    logger.info("🚨 Демонстрация обработки ошибок...")
    
    try:
        # Попытка получить статус несуществующей задачи
        await client.get_push_status("invalid_task_id")
        
    except UnauthorizedError:
        logger.error("🔑 Ошибка авторизации: неверный API ключ")
    except RateLimitError:
        logger.error("🚦 Превышен лимит запросов (50/сек)")
    except RegHelpError as e:
        logger.error(f"🔴 API ошибка: {e}")
    except Exception as e:
        logger.error(f"💥 Неожиданная ошибка: {e}")


async def parallel_tasks_example(client: RegHelpClient) -> None:
    """Пример параллельного выполнения задач."""
    logger.info("🔄 Демонстрация параллельного выполнения...")
    
    try:
        # Создать несколько задач параллельно
        tasks = await asyncio.gather(*[
            client.get_push_token("tgiOS", AppDevice.IOS, ref=f"parallel_{i}")
            for i in range(3)
        ], return_exceptions=True)
        
        # Фильтровать успешные задачи
        successful_tasks = [task for task in tasks if not isinstance(task, Exception)]
        
        logger.info(f"✅ Создано {len(successful_tasks)} задач параллельно")
        
        # Можно ждать результаты параллельно
        if successful_tasks:
            results = await asyncio.gather(*[
                client.get_push_status(task.id) 
                for task in successful_tasks
                if hasattr(task, 'id')
            ], return_exceptions=True)
            
            logger.info(f"📊 Получено {len(results)} статусов")
        
    except Exception as e:
        logger.error(f"❌ Ошибка параллельного выполнения: {e}")


async def main() -> None:
    """Главная функция с демонстрацией всех возможностей."""
    # Получить API ключ из переменной окружения
    api_key = os.getenv("REGHELP_API_KEY")
    if not api_key:
        logger.error("❌ Не найден API ключ в переменной REGHELP_API_KEY")
        logger.info("💡 Установите переменную: export REGHELP_API_KEY=your_api_key")
        return
    
    logger.info("🚀 Запуск демонстрации REGHelp Python Client")
    
    # Использование context manager для автоматического закрытия соединений
    async with RegHelpClient(
        api_key=api_key,
        timeout=30.0,
        max_retries=3
    ) as client:
        
        # Проверить доступность API
        if await client.health_check():
            logger.info("✅ API доступен")
        else:
            logger.error("❌ API недоступен")
            return
        
        # Демонстрация различных функций
        await check_balance(client)
        
        # Только если баланс позволяет
        balance = await client.get_balance()
        if balance.balance > 1:
            await get_telegram_push_token(client)
            await get_temporary_email(client)
            await demonstrate_turnstile(client)
            await parallel_tasks_example(client)
        else:
            logger.warning("⚠️ Недостаточно средств для демонстрации платных функций")
        
        # Демонстрация обработки ошибок
        await demonstrate_error_handling(client)
    
    logger.info("🏁 Демонстрация завершена")


if __name__ == "__main__":
    # Запуск асинхронной функции
    asyncio.run(main()) 