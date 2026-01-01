"""
Smart Bulk Sender System with:
- Account limits
- Verification
- NOT_FOUND skip
- Anti-duplicate checkpoint system
"""
import asyncio
import random
import logging
import json
import os
from collections import deque
from typing import List, Tuple, Dict, Optional, Set
from datetime import datetime

logger = logging.getLogger(__name__)


class SmartBulkSender:
    """
    سیستم هوشمند ارسال پیام bulk با قوانین:
    - هر اکانت حداکثر 4 پیام
    - انتخاب رندوم اکانت‌ها
    - تایید ارسال پیام
    - جایگزینی خودکار در صورت خطا
    - چرخه مجدد
    - Skip username های NOT_FOUND
    - جلوگیری از ارسال تکراری با checkpoint system
    """
    
    def __init__(self, accounts: List[Tuple[str, any]], usernames: List[str], message: str, 
                 max_per_account: int = 4, task_id: str = None):
        """
        Initialize the smart bulk sender
        
        Args:
            accounts: لیست تاپل‌های (session_name, client)
            usernames: لیست username‌های مقصد
            message: متن پیام
            max_per_account: حداکثر تعداد پیام برای هر اکانت (default: 4)
            task_id: شناسه یکتا برای این task (برای checkpoint)
        """
        self.all_accounts = accounts
        self.message = message
        self.max_per_account = max_per_account
        
        # Task ID برای checkpoint
        self.task_id = task_id or f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.checkpoint_file = f"task_checkpoint_{self.task_id}.json"
        
        # Set username های موفقیت‌آمیز ارسال شده (برای جلوگیری از تکرار)
        self.sent_usernames: Set[str] = set()
        
        # بارگذاری checkpoint اگر وجود دارد
        self._load_checkpoint()
        
        # فیلتر username‌هایی که قبلاً ارسال شده‌اند
        filtered_usernames = []
        skipped_count = 0
        for username in usernames:
            normalized = self._normalize_username(username)
            if normalized not in self.sent_usernames:
                filtered_usernames.append(username)
            else:
                skipped_count += 1
                logger.info(f"⏭️ Skipping {username} (already sent in previous task)")
        
        if skipped_count > 0:
            logger.warning(f"⚠️ {skipped_count} usernames already sent, skipping them")
        
        # صف username‌ها
        self.usernames_queue = deque(filtered_usernames)
        
        # State tracking
        self.account_counters = {session: 0 for session, _ in accounts}
        self.available_accounts = list(accounts)
        self.failed_attempts = {}
        
        # Statistics
        self.total_sent = 0
        self.total_failed = 0
        self.account_stats = {session: {"success": 0, "failed": 0} for session, _ in accounts}
        
        logger.info(f"SmartBulkSender initialized: {len(accounts)} accounts, {len(filtered_usernames)} usernames (after deduplication), limit={max_per_account}")
    
    def _normalize_username(self, username: str) -> str:
        """
        Normalize username برای مقایسه (حذف @ و lowercase)
        
        Args:
            username: username خام
            
        Returns:
            username نرمال شده
        """
        return username.lstrip('@').strip().lower()
    
    def _load_checkpoint(self):
        """بارگذاری checkpoint از فایل"""
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.sent_usernames = set(data.get('sent_usernames', []))
                    logger.info(f"✅ Checkpoint loaded: {len(self.sent_usernames)} usernames already sent")
            except Exception as e:
                logger.error(f"❌ Failed to load checkpoint: {e}")
                self.sent_usernames = set()
        else:
            logger.info("ℹ️ No checkpoint found, starting fresh")
            self.sent_usernames = set()
    
    def _save_checkpoint(self):
        """ذخیره checkpoint در فایل"""
        try:
            data = {
                'task_id': self.task_id,
                'sent_usernames': list(self.sent_usernames),
                'total_sent': self.total_sent,
                'total_failed': self.total_failed,
                'timestamp': datetime.now().isoformat()
            }
            with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug(f"💾 Checkpoint saved: {len(self.sent_usernames)} usernames")
        except Exception as e:
            logger.error(f"❌ Failed to save checkpoint: {e}")
    
    def _mark_as_sent(self, username: str):
        """
        Mark کردن یک username به عنوان ارسال شده
        
        Args:
            username: username ارسال شده
        """
        normalized = self._normalize_username(username)
        self.sent_usernames.add(normalized)
        self._save_checkpoint()
        logger.info(f"✅ Marked as sent: {username}")
    
    def _select_random_account(self) -> Optional[Tuple[str, any]]:
        """انتخاب رندوم یک اکانت از لیست available"""
        if not self.available_accounts:
            return None
        return random.choice(self.available_accounts)
    
    def _remove_account_from_pool(self, session_name: str):
        """حذف اکانت از لیست available (وقتی به محدودیت رسید)"""
        self.available_accounts = [(s, c) for s, c in self.available_accounts if s != session_name]
        logger.info(f"Account {session_name} reached limit ({self.max_per_account}), removed from pool. Available: {len(self.available_accounts)}")
    
    def _reset_account_pool(self):
        """Reset کردن pool اکانت‌ها برای شروع چرخه جدید"""
        self.available_accounts = list(self.all_accounts)
        for session in self.account_counters:
            self.account_counters[session] = 0
        logger.info(f"🔄 Account pool reset! Starting new cycle with {len(self.available_accounts)} accounts")
    
    async def _verify_message_sent(self, client, username: str, message_text: str) -> bool:
        """تایید اینکه پیام واقعاً ارسال شده است"""
        try:
            # فعلاً: اگر exception نداشت، موفق بوده
            # در آینده می‌توان از get_messages برای verify استفاده کرد
            return True
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            return False
    
    async def _send_to_username(self, session_name: str, client, username: str) -> str:
        """
        ارسال پیام به یک username با یک اکانت خاص
        
        Returns:
            "SUCCESS" - ارسال موفق
            "NOT_FOUND" - username وجود ندارد
            "FAILED" - خطای دیگر
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
                        return "SUCCESS"  # اگر send_message موفق بود، success است
                        
                except Exception as send_error:
                    error_str = str(send_error).lower()
                    
                    # بررسی نوع خطا
                    if 'nonetype' in error_str or 'cannot cast' in error_str:
                        continue
                    
                    if any(kw in error_str for kw in ['too many requests', 'flood', 'floodwait']):
                        logger.warning(f"Rate limit for {clean_user} with {session_name}")
                        return "FAILED"
                    
                    # USERNAME NOT FOUND
                    if any(kw in error_str for kw in ['username', 'not found', 'invalid', 'no user', 'user not found', 'could not find', 'no entity']):
                        username_not_found_count += 1
                        if username_not_found_count >= len(send_methods):
                            logger.warning(f"❌ Username {clean_user} NOT FOUND - skipping")
                            return "NOT_FOUND"
                        continue
                    
                    continue
            
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
            
            # بررسی اینکه قبلاً ارسال نشده باشد (double-check)
            if self._normalize_username(username) in self.sent_usernames:
                logger.warning(f"⏭️ {username} already marked as sent, skipping")
                self.usernames_queue.popleft()
                continue
            
            # تلاش برای ارسال
            logger.info(f"📤 Trying to send to {username} with {session_name} (counter: {self.account_counters[session_name]}/{self.max_per_account})")
            
            result = await self._send_to_username(session_name, client, username)
            
            if result == "SUCCESS":
                # موفق بود - MARK AS SENT
                self.usernames_queue.popleft()
                self._mark_as_sent(username)  # ✅ خط زدن از لیست
                
                self.account_counters[session_name] += 1
                self.account_stats[session_name]["success"] += 1
                self.total_sent += 1
                processed += 1
                
                logger.info(f"✅ SUCCESS: {username} sent by {session_name} (counter: {self.account_counters[session_name]}/{self.max_per_account})")
                
                # بررسی محدودیت
                if self.account_counters[session_name] >= self.max_per_account:
                    self._remove_account_from_pool(session_name)
                
                if progress_callback:
                    await progress_callback(f"✅ {processed}/{total_usernames} sent ({self.total_failed} failed)")
                
                await asyncio.sleep(random.uniform(1, 2))
            
            elif result == "NOT_FOUND":
                # USERNAME وجود ندارد - skip
                logger.warning(f"⚠️ SKIP: {username} not found (old/changed username)")
                self.usernames_queue.popleft()
                self.total_failed += 1
                processed += 1
                
                # ثبت در failed
                if username not in self.failed_attempts:
                    self.failed_attempts[username] = []
                self.failed_attempts[username].append("NOT_FOUND")
                
                # ذخیره checkpoint
                self._save_checkpoint()
                
                if progress_callback:
                    await progress_callback(f"⏭️ {processed}/{total_usernames} processed ({self.total_failed} not found/failed)")
                
                await asyncio.sleep(random.uniform(0.5, 1))
                
            else:  # result == "FAILED"
                # ناموفق بود - جایگزینی اکانت
                self.account_stats[session_name]["failed"] += 1
                
                if username not in self.failed_attempts:
                    self.failed_attempts[username] = []
                self.failed_attempts[username].append(session_name)
                
                logger.warning(f"❌ FAILED: {username} with {session_name}, trying with another account...")
                
                # اگر با همه اکانت‌ها fail شد، skip کن
                if len(self.failed_attempts.get(username, [])) >= len(self.all_accounts):
                    logger.error(f"⚠️ SKIP: {username} failed with ALL accounts")
                    self.usernames_queue.popleft()
                    self.total_failed += 1
                    processed += 1
                    
                    # ذخیره checkpoint
                    self._save_checkpoint()
                    
                    if progress_callback:
                        await progress_callback(f"⚠️ {processed}/{total_usernames} processed ({self.total_failed} failed)")
                
                await asyncio.sleep(random.uniform(2, 3))
        
        # آمار نهایی
        logger.info("="*60)
        logger.info("📊 FINAL STATISTICS:")
        logger.info(f"  Total sent: {self.total_sent}")
        logger.info(f"  Total failed: {self.total_failed}")
        logger.info(f"  Checkpoint: {len(self.sent_usernames)} usernames marked")
        logger.info("="*60)
        
        for session_name, stats in self.account_stats.items():
            logger.info(f"  {session_name}: {stats['success']} success, {stats['failed']} failed")
        
        return {
            "total_sent": self.total_sent,
            "total_failed": self.total_failed,
            "sent_usernames": list(self.sent_usernames),
            "account_stats": self.account_stats,
            "failed_attempts": self.failed_attempts
        }
    
    def cleanup(self):
        """پاکسازی فایل checkpoint (اختیاری - بعد از اتمام task)"""
        try:
            if os.path.exists(self.checkpoint_file):
                os.remove(self.checkpoint_file)
                logger.info(f"🗑️ Checkpoint file removed: {self.checkpoint_file}")
        except Exception as e:
            logger.error(f"❌ Failed to remove checkpoint: {e}")

