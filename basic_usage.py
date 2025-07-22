#!/usr/bin/env python3
"""
Basic usage example for REGHelp Python Client.

Demonstrates main library features:
- Balance checking
- Getting push tokens
- Working with email service
- Error handling
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


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def check_balance(client: RegHelpClient) -> None:
    """Check current account balance."""
    try:
        balance = await client.get_balance()
        logger.info(f"💰 Current balance: {balance.balance} {balance.currency}")
        
        if balance.balance < 10:
            logger.warning("⚠️ Low balance! Consider topping up your account")
        
    except Exception as e:
        logger.error(f"❌ Error getting balance: {e}")


async def get_telegram_push_token(client: RegHelpClient) -> Optional[str]:
    """Get push token for Telegram iOS."""
    try:
        logger.info("📱 Creating task for Telegram iOS push token...")
        
        # Create task
        task = await client.get_push_token(
            app_name="tgiOS",
            app_device=AppDevice.IOS,
            ref="demo_example"
        )
        
        logger.info(f"✅ Task created: {task.id} (price: {task.price} RUB)")
        
        # Wait for result with automatic polling
        result = await client.wait_for_result(
            task_id=task.id,
            service="push",
            timeout=60.0,  # 1 minute
            poll_interval=3.0  # check every 3 seconds
        )
        
        if result.token:
            logger.info(f"🎉 Push token received: {result.token[:50]}...")
            return result.token
        else:
            logger.error("❌ Token not received")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error getting push token: {e}")
        return None


async def get_temporary_email(client: RegHelpClient) -> Optional[str]:
    """Get temporary email address."""
    try:
        logger.info("📧 Getting temporary email address...")
        
        # Get email
        email_task = await client.get_email(
            app_name="tg",
            app_device=AppDevice.IOS,
            phone="+15551234567",  # Test number
            email_type=EmailType.ICLOUD
        )
        
        logger.info(f"✅ Email received: {email_task.email}")
        
        # Can wait for verification code
        logger.info("⏳ Waiting for verification code (30 sec)...")
        
        try:
            email_result = await client.wait_for_result(
                task_id=email_task.id,
                service="email",
                timeout=30.0
            )
            
            if email_result.code:
                logger.info(f"📬 Verification code: {email_result.code}")
                return email_result.code
                
        except asyncio.TimeoutError:
            logger.info("⏰ Verification code not received within 30 seconds")
        
        return email_task.email
        
    except Exception as e:
        logger.error(f"❌ Error getting email: {e}")
        return None


async def demonstrate_turnstile(client: RegHelpClient) -> Optional[str]:
    """Demonstrate Turnstile challenge solving."""
    try:
        logger.info("🔐 Solving Cloudflare Turnstile...")
        
        task = await client.get_turnstile_token(
            url="https://demo.example.com",
            site_key="0x4AAAA-demo-site-key",
            action="demo",
        )
        
        logger.info(f"✅ Turnstile task created: {task.id}")
        
        # Wait for result
        result = await client.wait_for_result(
            task_id=task.id,
            service="turnstile",
            timeout=120.0
        )
        
        if result.token:
            logger.info(f"🎉 Turnstile token: {result.token[:50]}...")
            return result.token
        
    except Exception as e:
        logger.error(f"❌ Turnstile error: {e}")
        return None


async def demonstrate_error_handling(client: RegHelpClient) -> None:
    """Demonstrate various error handling."""
    logger.info("🚨 Demonstrating error handling...")
    
    try:
        # Try to get status of non-existent task
        await client.get_push_status("invalid_task_id")
        
    except UnauthorizedError:
        logger.error("🔑 Authorization error: invalid API key")
    except RateLimitError:
        logger.error("🚦 Rate limit exceeded (50/sec)")
    except RegHelpError as e:
        logger.error(f"🔴 API error: {e}")
    except Exception as e:
        logger.error(f"💥 Unexpected error: {e}")


async def parallel_tasks_example(client: RegHelpClient) -> None:
    """Example of parallel task execution."""
    logger.info("🔄 Demonstrating parallel execution...")
    
    try:
        # Create multiple tasks in parallel
        tasks = await asyncio.gather(*[
            client.get_push_token("tgiOS", AppDevice.IOS, ref=f"parallel_{i}")
            for i in range(3)
        ], return_exceptions=True)
        
        # Filter successful tasks
        successful_tasks = [task for task in tasks if not isinstance(task, Exception)]
        
        logger.info(f"✅ Created {len(successful_tasks)} tasks in parallel")
        
        # Can wait for results in parallel
        if successful_tasks:
            results = await asyncio.gather(*[
                client.get_push_status(task.id) 
                for task in successful_tasks
                if hasattr(task, 'id')
            ], return_exceptions=True)
            
            logger.info(f"📊 Received {len(results)} statuses")
        
    except Exception as e:
        logger.error(f"❌ Parallel execution error: {e}")


async def main() -> None:
    """Main function demonstrating all capabilities."""
    # Get API key from environment variable
    api_key = os.getenv("REGHELP_API_KEY")
    if not api_key:
        logger.error("❌ API key not found in REGHELP_API_KEY environment variable")
        logger.info("💡 Set the variable: export REGHELP_API_KEY=your_api_key")
        return
    
    logger.info("🚀 Starting REGHelp Python Client demonstration")
    
    # Use context manager for automatic connection cleanup
    async with RegHelpClient(
        api_key=api_key,
        timeout=30.0,
        max_retries=3
    ) as client:
        
        # Check API availability
        if await client.health_check():
            logger.info("✅ API is available")
        else:
            logger.error("❌ API is unavailable")
            return
        
        # Demonstrate various functions
        await check_balance(client)
        
        # Only if balance allows
        balance = await client.get_balance()
        if balance.balance > 1:
            await get_telegram_push_token(client)
            await get_temporary_email(client)
            await demonstrate_turnstile(client)
            await parallel_tasks_example(client)
        else:
            logger.warning("⚠️ Insufficient funds to demonstrate paid functions")
        
        # Demonstrate error handling
        await demonstrate_error_handling(client)
    
    logger.info("🏁 Demonstration completed")


if __name__ == "__main__":
    # Run async function
    asyncio.run(main()) 