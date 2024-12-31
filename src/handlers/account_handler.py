#account_handlers.py
from telethon import TelegramClient, events, Button
from telethon.errors import SessionPasswordNeededError
from telethon.tl.types import Channel, Chat
from datetime import datetime
from asyncio.log import logger
from config import API_ID, API_HASH, CHANNEL_ID
import logging
import os

logger = logging.getLogger(__name__)

class AccountHandler:
    def __init__(self, bot):
        self.bot = bot
        self._conversations = {}

    async def add_account(self, event):
        """Add a new Telegram account"""
        print("add_account in AccountHandler")
        try:
            chat_id = event.chat_id
            # Send initial message
            await self.bot.bot.send_message(chat_id, "Please enter your phone number:")
            self.bot._conversations[chat_id] = 'phone_number_handler'
        except Exception as e:
            logger.error(f"Error in add_account: {e}")
            await self.bot.bot.send_message(chat_id, "Error occurred while adding account. Please try again.")

    async def phone_number_handler(self, event):
        """Handle phone number input"""
        print("phone_number_handler in AccountHandler")
        try:
            phone_number = event.message.text.strip()
            chat_id = event.chat_id

            client = TelegramClient(phone_number, API_ID, API_HASH)
            await client.connect()

            if not await client.is_user_authorized():
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
        print("code_handler in AccountHandler")
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
        print("password_handler in AccountHandler")
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
        print("finalize_client_setup in AccountHandler")
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
        print("cleanup_temp_handlers in AccountHandler")
        if 'temp_client' in self.bot.handlers:
            del self.bot.handlers['temp_client']
        if 'temp_phone' in self.bot.handlers:
            del self.bot.handlers['temp_phone']

    async def process_message(self, event):
        """Process and forward messages"""
        print("process_message in AccountHandler")
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

    async def update_groups(self, event):
        """Update groups for all accounts"""
        print("update_groups in AccountHandler")
        try:
            status_message = await event.respond("🔄 Updating groups...")
            total = len(self.bot.active_clients)
            updated = 0

            for session_name, client in self.bot.active_clients.items():
                try:
                    dialogs = await client.get_dialogs()
                    groups = [
                        dialog.entity.id for dialog in dialogs
                        if isinstance(dialog.entity, (Chat, Channel)) and not dialog.entity.broadcast
                    ]

                    # Update config
                    for client_info in self.bot.config['clients']:
                        if client_info['session'] == session_name:
                            client_info['groups'] = groups
                            break

                    updated += 1
                    progress = (updated / total) * 100
                    await status_message.edit(f"🔄 Updating groups... {progress:.1f}%")

                except Exception as e:
                    logger.error(f"Error updating groups for {session_name}: {e}")

            self.bot.config_manager.save_config()
            await status_message.edit("✅ Groups updated successfully!")

        except Exception as e:
            logger.error(f"Error in update_groups: {e}")
            await event.respond("❌ Error updating groups. Please try again.")

    async def show_accounts(self, event):
        """Show all accounts with their status"""
        print("show_accounts in AccountHandler")
        try:
            if not self.bot.config['clients']:
                await event.respond("No accounts added yet.")
                return

            for client_info in self.bot.config['clients']:
                phone = client_info['phone_number']
                session = client_info['session']
                groups = len(client_info.get('groups', []))
                status = "🟢 Active" if session in self.bot.active_clients else "🔴 Inactive"

                text = (
                    f"📱 Phone: {phone}\n"
                    f"📑 Session: {session}\n"
                    f"👥 Groups: {groups}\n"
                    f"📊 Status: {status}\n"
                )

                buttons = [
                    [
                        Button.inline("❌ Disable" if status == "🟢 Active" else "✅ Enable",
                                    data=f"toggle_{session}"),
                        Button.inline("🗑 Delete", data=f"delete_{session}")
                    ]
                ]

                await event.respond(text, buttons=buttons)

        except Exception as e:
            logger.error(f"Error in show_accounts: {e}")
            await event.respond("Error showing accounts. Please try again.")

    async def toggle_client(self, session: str, event):
        """Toggle client active status"""
        print("toggle_client in AccountHandler")
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
        print("delete_client in AccountHandler")
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
