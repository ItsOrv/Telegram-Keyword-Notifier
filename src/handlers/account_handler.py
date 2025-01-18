#account_handlers.py
from telethon import TelegramClient, events, Button
from telethon.errors import SessionPasswordNeededError
from telethon.tl.types import Channel, Chat
from datetime import datetime
from asyncio.log import logger
from config import API_ID, API_HASH, CHANNEL_ID
import logging
import os
from clients.client_manager import ClientManager
import json
from telethon.errors import FloodWaitError

import asyncio

logger = logging.getLogger(__name__)

class AccountHandler:
    def __init__(self, bot):
        self.bot = bot
        self._conversations = {}
        self.ClientManager = bot.client_manager 

    async def add_account(self, event):
        """Add a new Telegram account"""
        logger.info("add_account in AccountHandler")
        try:
            chat_id = event.chat_id
            await self.bot.bot.send_message(chat_id, "Please enter your phone number:")
            self.bot._conversations[chat_id] = 'phone_number_handler'
        except Exception as e:
            logger.error(f"Error in add_account: {e}")
            await self.bot.bot.send_message(chat_id, "Error occurred while adding account. Please try again.")

    async def phone_number_handler(self, event):
        """Handle phone number input"""
        logger.info("phone_number_handler in AccountHandler")
        try:
            phone_number = event.message.text.strip()
            chat_id = event.chat_id

            client = TelegramClient(phone_number, API_ID, API_HASH)
            await client.connect()

            if not await client.is_user_authorized():
                await self.bot.bot.send_message(chat_id, "authorizing...")
                await client.send_code_request(phone_number)
                await self.bot.bot.send_message(chat_id, "Enter the verification code:")
                self.bot._conversations[chat_id] = 'code_handler'
                self.bot.handlers['temp_client'] = client
                self.bot.handlers['temp_phone'] = phone_number
            else:
                await self.finalize_client_setup(client, phone_number, chat_id)

        except Exception as e:
            logger.error(f"Error in phone_number_handler: {e}")
            await self.bot.bot.send_message(chat_id, "Error occurred. Please try again.")
            del self.bot._conversations[chat_id]

    async def code_handler(self, event):
        """Handle verification code input"""
        logger.info("code_handler in AccountHandler")
        try:
            code = event.message.text.strip()
            chat_id = event.chat_id
            client = self.bot.handlers.get('temp_client')
            phone_number = self.bot.handlers.get('temp_phone')

            try:
                await client.sign_in(phone_number, code)
                await self.finalize_client_setup(client, phone_number, chat_id)
            except SessionPasswordNeededError:
                await self.bot.bot.send_message(chat_id, "Enter your 2FA password:")
                self.bot._conversations[chat_id] = 'password_handler'

        except Exception as e:
            logger.error(f"Error in code_handler: {e}")
            await self.bot.bot.send_message(chat_id, "Error occurred. Please try again.")
            self.cleanup_temp_handlers()

    async def password_handler(self, event):
        """Handle 2FA password input"""
        logger.info("password_handler in AccountHandler")
        try:
            password = event.message.text.strip()
            chat_id = event.chat_id
            client = self.bot.handlers.get('temp_client')
            phone_number = self.bot.handlers.get('temp_phone')

            await client.sign_in(password=password)
            await self.finalize_client_setup(client, phone_number, chat_id)

        except Exception as e:
            logger.error(f"Error in password_handler: {e}")
            await self.bot.bot.send_message(chat_id, "Error occurred. Please try again.")
            self.cleanup_temp_handlers()

    async def finalize_client_setup(self, client, phone_number, chat_id):
        """Finalize the client setup process"""
        logger.info("finalize_client_setup in AccountHandler")
        try:
            session_name = f"{phone_number}_session"
            client.session.save()

            # Add to config
            self.bot.config['clients'].append({
                "phone_number": phone_number,
                "session": session_name,
                "groups": [],
                "added_date": datetime.now().isoformat(),
                "disabled": False
            })
            self.bot.config_manager.save_config()

            # Add to active clients
            self.bot.active_clients[session_name] = client
            client.add_event_handler(
                self.process_message,
                events.NewMessage()
            )

            await self.bot.bot.send_message(chat_id, f"Account {phone_number} added successfully!")
            self.cleanup_temp_handlers()

        except Exception as e:
            logger.error(f"Error in finalize_client_setup: {e}")
            await self.bot.bot.send_message(chat_id, "Error occurred while finalizing setup.")
            self.cleanup_temp_handlers()

    def cleanup_temp_handlers(self):
        """Clean up temporary handlers and data"""
        logger.info("cleanup_temp_handlers in AccountHandler")
        if 'temp_client' in self.bot.handlers:
            del self.bot.handlers['temp_client']
        if 'temp_phone' in self.bot.handlers:
            del self.bot.handlers['temp_phone']

    async def update_groups(self, event):
        """Identify groups for each client and save their IDs in JSON without deleting previous data."""
        logger.info("update_groups in AccountHandler")

        groups_per_client = {}
        self.ClientManager.detect_sessions()

        try:
            status_message = await event.respond("🔄 Identifying groups for each client...")

            # بارگذاری اطلاعات قبلی
            json_data = {
                "TARGET_GROUPS": [],
                "KEYWORDS": [],
                "IGNORE_USERS": [],
                "clients": {}
            }
            
            if os.path.exists("clients.json"):
                try:
                    with open("clients.json", "r", encoding='utf-8') as json_file:
                        loaded_data = json.loads(json_file.read())
                        json_data.update(loaded_data)
                        if isinstance(json_data["clients"], list):
                            json_data["clients"] = {session: [] for session in json_data["clients"]}
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error: {e}")

            # به‌روزرسانی گروه‌ها برای هر کلاینت فعال
            for session_name, client in self.bot.active_clients.items():
                try:
                    logger.info(f"Processing client: {session_name}")
                    group_ids = set()

                    try:
                        # دریافت همه دیالوگ‌ها با یک درخواست اولیه
                        dialogs = []
                        async for dialog in client.iter_dialogs(limit=None):
                            try:
                                if isinstance(dialog.entity, (Chat, Channel)) and not (
                                    isinstance(dialog.entity, Channel) and dialog.entity.broadcast
                                ):
                                    group_ids.add(dialog.entity.id)
                                    
                                # هر 50 گروه، یک تاخیر کوتاه
                                if len(group_ids) % 50 == 0:
                                    await asyncio.sleep(2)
                                    
                            except Exception as e:
                                logger.error(f"Error processing dialog: {e}")
                                continue
                                
                            # بروزرسانی پیام وضعیت هر 20 گروه
                            if len(group_ids) % 20 == 0:
                                await status_message.edit(f"📊 Found {len(group_ids)} groups for {session_name}...")

                    except FloodWaitError as e:
                        wait_time = e.seconds
                        logger.info(f"FloodWaitError: Sleeping for {wait_time} seconds")
                        await status_message.edit(f"⏳ Rate limited. Waiting for {wait_time} seconds...")
                        await asyncio.sleep(wait_time)
                        continue
                        
                    except Exception as e:
                        logger.error(f"Error in dialog iteration: {e}")
                        await status_message.edit(f"⚠️ Error processing {session_name}: {str(e)}")
                        continue

                    # ذخیره گروه‌های یافت شده
                    groups_per_client[session_name] = list(group_ids)
                    logger.info(f"Found {len(group_ids)} groups for {session_name}")
                    await status_message.edit(f"✅ Found {len(group_ids)} groups for {session_name}")
                    
                    # تاخیر بین پردازش کلاینت‌های مختلف
                    await asyncio.sleep(3)

                except Exception as e:
                    logger.error(f"Error processing client {session_name}: {e}")
                    continue

            # ادغام اطلاعات جدید
            for session_name, group_ids in groups_per_client.items():
                if session_name in json_data["clients"]:
                    existing_groups = json_data["clients"][session_name]
                    if not isinstance(existing_groups, list):
                        existing_groups = []
                    json_data["clients"][session_name] = list(set(existing_groups + group_ids))
                else:
                    json_data["clients"][session_name] = group_ids

            # ذخیره اطلاعات
            with open("clients.json", "w", encoding='utf-8') as json_file:
                json.dump(json_data, json_file, indent=4, ensure_ascii=False)
                logger.info(f"Saved data for {len(groups_per_client)} clients")

            await status_message.edit(f"✅  {len(group_ids)} Groups identified and saved successfully for all clients!")

        except Exception as e:
            logger.error(f"Error in update_groups: {e}")
            await event.respond(f"❌ Error identifying groups: {str(e)}")

    async def process_messages_for_client(self, client):
        """Process messages for a specific client in a loop."""
        @client.on(events.NewMessage)
        async def process_message(event):
            """Process and forward messages for a single client."""
            try:
                message = event.message.text
                if not message:
                    return

                sender = await event.get_sender()
                if not sender or sender.id in self.bot.config['IGNORE_USERS']:
                    return

                # Check keywords
                if not any(keyword.lower() in message.lower() for keyword in self.bot.config['KEYWORDS']):
                    return

                # Get chat info
                chat = await event.get_chat()
                chat_title = getattr(chat, 'title', 'Unknown Chat')

                # Format message
                text = (
                    f"📝 New Message\n\n"
                    f"👤 From: {getattr(sender, 'first_name', '')} {getattr(sender, 'last_name', '')}\n"
                    f"🆔 User ID: `{sender.id}`\n"
                    f"💭 Chat: {chat_title}\n\n"
                    f"📜 Message:\n{message}\n"
                )

                # Get message link
                if hasattr(chat, 'username') and chat.username:
                    message_link = f"https://t.me/{chat.username}/{event.id}"
                else:
                    chat_id = str(event.chat_id).replace('-100', '', 1)
                    message_link = f"https://t.me/c/{chat_id}/{event.id}"

                buttons = [[Button.url("📎 View Message", url=message_link)]]

                await self.bot.bot.send_message(
                    CHANNEL_ID,
                    text,
                    buttons=buttons,
                    link_preview=False
                )

            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)



    async def show_accounts(self, event):
        """Show all accounts with their status"""
        logger.info("show_accounts in AccountHandler")
        try:
            if not isinstance(self.bot.config['clients'], list) or not self.bot.config['clients']:
                await event.respond("No accounts added yet.")
                return

            for clients in self.bot.config['clients']:
                # بررسی اینکه client_info دیکشنری است
                if isinstance(clients, dict):
                    session = clients.get('session', 'Unknown')
                    # استخراج شماره تلفن از نام فایل سشن
                    phone = session.replace('.session', '') if session != 'Unknown' else 'Unknown'
                    groups = len(clients.get('groups', []))
                    status = "🟢 Active" if session in self.bot.active_clients else "🔴 Inactive"

                    text = (
                        f"📱 Phone: {phone}\n"
                        f"📑 Session: {session}\n"
                        f"👥 Groups: {groups}\n"
                        f"📊 Status: {status}\n"
                    )

                    buttons = [
                        [
                            Button.inline("❌ Disable" if status == "🟢 Active" else "✅ Enable", data=f"toggle_{session}"),
                            Button.inline("🗑 Delete", data=f"delete_{session}")
                        ]
                    ]

                    await event.respond(text, buttons=buttons)
                else:
                    logger.warning(f"Invalid client_info format: {clients}")

        except Exception as e:
            logger.error(f"Error in show_accounts: {e}")
            await event.respond("Error showing accounts. Please try again.")

    async def toggle_client(self, session: str, event):
        """Toggle client active status"""
        logger.info("toggle_client in AccountHandler")
        try:
            for client_info in self.bot.config['clients']:
                if client_info['session'] == session:
                    currently_active = session in self.bot.active_clients

                    if currently_active:
                        # Disable client
                        client = self.bot.active_clients[session]
                        await client.disconnect()
                        del self.bot.active_clients[session]
                        client_info['disabled'] = True
                        await event.respond(f"✅ Account {client_info['phone_number']} disabled")
                    else:
                        # Enable client
                        client = TelegramClient(session, API_ID, API_HASH)
                        await client.start()
                        self.bot.active_clients[session] = client
                        client_info['disabled'] = False
                        await event.respond(f"✅ Account {client_info['phone_number']} enabled")

                    self.bot.config_manager.save_config()
                    break

        except Exception as e:
            logger.error(f"Error toggling client {session}: {e}")
            await event.respond("❌ Error toggling account status")

    async def delete_client(self, session: str, event):
        """Delete a client"""
        logger.info("delete_client in AccountHandler")
        try:
            # Disconnect if active
            if session in self.bot.active_clients:
                client = self.bot.active_clients[session]
                await client.disconnect()
                del self.bot.active_clients[session]

            # Remove from config
            self.bot.config['clients'] = [
                client for client in self.bot.config['clients']
                if client['session'] != session
            ]
            self.bot.config_manager.save_config()

            # Delete session file
            session_file = f"{session}.session"
            if os.path.exists(session_file):
                os.remove(session_file)

            await event.respond(f"✅ Account deleted successfully")

        except Exception as e:
            logger.error(f"Error deleting client {session}: {e}")
            await event.respond("❌ Error deleting account")