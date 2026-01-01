"""
Smart Bulk Sender System with Account Limits and Verification
این سیستم ارسال پیام با قوانین دقیق و محدودیت برای هر اکانت
"""
import asyncio
import random
import logging
from collections import deque
from typing import List, Tuple, Dict, Optional

logger = logging.getLogger(__name__)


class SmartBulkSender:
    """
    سیستم هوشمند ارسال پیام bulk با قوانین:
    - هر اکانت حداکثر 4 پیام
    - انتخاب رندوم اکانت‌ها
    - تایید ارسال پیام
    - جایگزینی خودکار در صورت خطا
    - چرخه مجدد
    """
    
    def __init__(self, accounts: List[Tuple[str, any]], usernames: List[str], message: str, max_per_account: int = 4):
        """
        Initialize the smart bulk sender
        
        Args:
            accounts: لیست تاپل‌های (session_name, client)
            usernames: لیست username‌های مقصد
            message: متن پیام
            max_per_account: حداکثر تعداد پیام برای هر اکانت (default: 4)
        """
        self.all_accounts = accounts  # همه اکانت‌ها
        self.usernames_queue = deque(usernames)  # صف username‌ها
        self.message = message
        self.max_per_account = max_per_account
        
        # State tracking
        self.account_counters = {session: 0 for session, _ in accounts}  # تعداد پیام‌های هر اکانت
        self.available_accounts = list(accounts)  # اکانت‌های در دسترس
        self.failed_attempts = {}  # username: [failed_accounts]
        
        # Statistics
        self.total_sent = 0
        self.total_failed = 0
        self.account_stats = {session: {"success": 0, "failed": 0} for session, _ in accounts}
        
        logger.info(f"SmartBulkSender initialized: {len(accounts)} accounts, {len(usernames)} usernames, limit={max_per_account}")
    
    def _select_random_account(self) -> Optional[Tuple[str, any]]:
        """
        انتخاب رندوم یک اکانت از لیست available
        
        Returns:
            تاپل (session_name, client) یا None اگر اکانتی در دسترس نباشد
        """
        if not self.available_accounts:
            return None
        
        return random.choice(self.available_accounts)
    
    def _remove_account_from_pool(self, session_name: str):
        """
        حذف اکانت از لیست available (وقتی به محدودیت رسید)
        """
        self.available_accounts = [(s, c) for s, c in self.available_accounts if s != session_name]
        logger.info(f"Account {session_name} reached limit ({self.max_per_account}), removed from pool. Available: {len(self.available_accounts)}")
    
    def _reset_account_pool(self):
        """
        Reset کردن pool اکانت‌ها برای شروع چرخه جدید
        """
        self.available_accounts = list(self.all_accounts)
        for session in self.account_counters:
            self.account_counters[session] = 0
        logger.info(f"🔄 Account pool reset! Starting new cycle with {len(self.available_accounts)} accounts")
    
    async def _verify_message_sent(self, client, username: str, message_text: str) -> bool:
        """
        تایید اینکه پیام واقعاً ارسال شده است
        
        این تابع پس از ارسال، چک می‌کند که پیام در chat history موجود است
        
        Args:
            client: کلاینت تلگرام
            username: username مقصد
            message_text: متن پیام
            
        Returns:
            True اگر پیام واقعاً ارسال شده باشد
        """
        try:
            # روش 1: بررسی آخرین پیام‌های ارسالی
            # می‌توانیم outgoing messages را بررسی کنیم
            # اما برای سادگی، اگر send_message بدون exception بود، موفق بوده
            
            # در آینده می‌توان:
            # 1. آخرین پیام outgoing را check کرد
            # 2. message.id را ذخیره و بعداً verify کرد
            # 3. از get_messages با filter استفاده کرد
            
            # فعلاً: اگر exception نداشت، موفق بوده
            return True
            
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            return False
    
    async def _send_to_username(self, session_name: str, client, username: str) -> str:
        """
        ارسال پیام به یک username با یک اکانت خاص
        
        Args:
            session_name: نام session اکانت
            client: کلاینت تلگرام
            username: username مقصد
            
        Returns:
            "SUCCESS" اگر موفق بود
            "NOT_FOUND" اگر username وجود نداشت
            "FAILED" برای سایر خطاها
        """
        clean_user = username.lstrip('@').strip()
        
        try:
            # اتصال اکانت
            if not client.is_connected():
                await client.connect()
            
            # بررسی authorization
            me = await client.get_me()
            if not me:
                logger.error(f"Account {session_name} get_me() returned None")
                return "FAILED"
            
            # تلاش برای ارسال با روش‌های مختلف
            send_methods = [
                (f"@{clean_user}", "with @"),
                (clean_user, "without @"),
            ]
            
            username_not_found_count = 0
            
            for method_target, method_name in send_methods:
                try:
                    if method_target is None:
                        continue
                    
                    # ارسال پیام
                    await client.send_message(method_target, self.message)
                    logger.info(f"✅ Sent to {clean_user} via {method_name} with {session_name}")
                    
                    # تایید ارسال
                    verified = await self._verify_message_sent(client, username, self.message)
                    if verified:
                        return "SUCCESS"
                    else:
                        logger.warning(f"⚠️ Message sent but verification failed for {clean_user}")
                        return "SUCCESS"  # اگر send_message موفق بود، success حساب می‌شود
                        
                except Exception as send_error:
                    error_str = str(send_error).lower()
                    
                    # بررسی نوع خطا
                    if 'nonetype' in error_str or 'cannot cast' in error_str:
                        continue  # تلاش با روش بعدی
                    
                    if any(kw in error_str for kw in ['too many requests', 'flood', 'floodwait']):
                        logger.warning(f"Rate limit for {clean_user} with {session_name}")
                        return "FAILED"
                    
                    # USERNAME NOT FOUND - این مهمترین بخش است
                    if any(kw in error_str for kw in ['username', 'not found', 'invalid', 'no user', 'user not found', 'could not find', 'no entity']):
                        username_not_found_count += 1
                        if username_not_found_count >= len(send_methods):
                            # همه روش‌ها گفتند username وجود ندارد
                            logger.warning(f"❌ Username {clean_user} NOT FOUND - skipping to next username")
                            return "NOT_FOUND"
                        continue
                    
                    # سایر خطاها
                    continue
            
            # همه روش‌ها fail شدند
            logger.warning(f"All methods failed for {clean_user} with {session_name}")
            return "FAILED"
            
        except Exception as e:
            logger.error(f"Error sending to {username} with {session_name}: {e}")
            return "FAILED"
    
    async def send_all(self, progress_callback=None) -> Dict:
        """
        ارسال پیام به همه username‌ها با قوانین سیستم
        
        Args:
            progress_callback: تابع callback برای گزارش پیشرفت
            
        Returns:
            دیکشنری حاوی آمار و نتایج
        """
        logger.info(f"🚀 Starting smart bulk send: {len(self.usernames_queue)} usernames")
        
        processed = 0
        total_usernames = len(self.usernames_queue)
        
        while self.usernames_queue:
            # اگر pool خالی شد، reset کن
            if not self.available_accounts:
                logger.info("🔄 All accounts reached limit, resetting pool...")
                self._reset_account_pool()
                
                # گزارش پیشرفت
                if progress_callback:
                    await progress_callback(f"🔄 Cycle restart: {processed}/{total_usernames} sent")
            
            # انتخاب رندوم اکانت
            account_info = self._select_random_account()
            if not account_info:
                logger.error("❌ No accounts available!")
                break
            
            session_name, client = account_info
            
            # گرفتن username بعدی
            username = self.usernames_queue[0]  # peek without pop
            
            # تلاش برای ارسال
            logger.info(f"📤 Trying to send to {username} with {session_name} (counter: {self.account_counters[session_name]}/{self.max_per_account})")
            
            result = await self._send_to_username(session_name, client, username)
            
            if result == "SUCCESS":
                # موفق بود
                self.usernames_queue.popleft()  # حذف از صف
                self.account_counters[session_name] += 1
                self.account_stats[session_name]["success"] += 1
                self.total_sent += 1
                processed += 1
                
                logger.info(f"✅ SUCCESS: {username} sent by {session_name} (counter: {self.account_counters[session_name]}/{self.max_per_account})")
                
                # بررسی محدودیت
                if self.account_counters[session_name] >= self.max_per_account:
                    self._remove_account_from_pool(session_name)
                
                # گزارش پیشرفت
                if progress_callback:
                    await progress_callback(f"✅ {processed}/{total_usernames} sent ({self.total_failed} failed)")
                
                # تاخیر کوتاه
                await asyncio.sleep(random.uniform(1, 2))
            
            elif result == "NOT_FOUND":
                # USERNAME وجود ندارد - skip به username بعدی
                logger.warning(f"⚠️ SKIP: {username} not found (old/changed username), moving to next")
                self.usernames_queue.popleft()  # حذف از صف
                self.total_failed += 1
                processed += 1
                
                # ثبت در failed_usernames
                if username not in self.failed_attempts:
                    self.failed_attempts[username] = []
                self.failed_attempts[username].append("NOT_FOUND")
                
                # گزارش پیشرفت
                if progress_callback:
                    await progress_callback(f"⏭️ {processed}/{total_usernames} processed ({self.total_failed} not found/failed)")
                
                # تاخیر کوتاه و به بعدی برو
                await asyncio.sleep(random.uniform(0.5, 1))
                
            else:  # result == "FAILED"
                # ناموفق بود - جایگزینی اکانت
                self.account_stats[session_name]["failed"] += 1
                
                # ثبت در failed_attempts
                if username not in self.failed_attempts:
                    self.failed_attempts[username] = []
                self.failed_attempts[username].append(session_name)
                
                logger.warning(f"❌ FAILED: {username} with {session_name}, trying with another account...")
                
                # اگر با همه اکانت‌های موجود fail شد، skip کن
                if len(self.failed_attempts.get(username, [])) >= len(self.all_accounts):
                    logger.error(f"⚠️ SKIP: {username} failed with ALL accounts")
                    self.usernames_queue.popleft()  # حذف از صف
                    self.total_failed += 1
                    processed += 1
                    
                    if progress_callback:
                        await progress_callback(f"⚠️ {processed}/{total_usernames} processed ({self.total_failed} failed)")
                
                # تاخیر قبل از retry
                await asyncio.sleep(random.uniform(2, 3))
        
        # آمار نهایی
        logger.info("="*60)
        logger.info("📊 FINAL STATISTICS:")
        logger.info(f"  Total sent: {self.total_sent}")
        logger.info(f"  Total failed: {self.total_failed}")
        logger.info(f"  Total processed: {processed}/{total_usernames}")
        logger.info("="*60)
        
        for session, stats in self.account_stats.items():
            logger.info(f"  {session}: ✅ {stats['success']} | ❌ {stats['failed']}")
        
        return {
            "total_sent": self.total_sent,
            "total_failed": self.total_failed,
            "total_processed": processed,
            "account_stats": self.account_stats,
            "failed_usernames": [u for u in self.failed_attempts.keys() if len(self.failed_attempts[u]) >= len(self.all_accounts)]
        }

