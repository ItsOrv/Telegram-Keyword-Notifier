import logging
import random
import asyncio
from telethon import TelegramClient, events, Button
from src.Config import CHANNEL_ID

logger = logging.getLogger(__name__)

class Actions:
    def __init__(self, tbot):
        self.tbot = tbot

    async def prompt_group_action(self, event, action_name):
        """
        Prompt the user to enter the number of accounts to be used for the group action.
        """
        total_accounts = len(self.tbot.active_clients)
        message = f"There are {total_accounts} accounts available. Please choose how many accounts (from 1 to {total_accounts}) will perform the {action_name} action."
        buttons = [Button.inline(str(i), f"{action_name}_{i}") for i in range(1, total_accounts + 1)]
        await event.respond(message, buttons=buttons)

    async def prompt_individual_action(self, event, action_name):
        """
        Show a list of account names as clickable buttons and prompt the user to select which account should perform the action.
        """
        buttons = [Button.inline(session, f"{action_name}_{session}") for session in self.tbot.active_clients.keys()]
        await event.respond("Please select an account to perform the action:", buttons=buttons)

    async def handle_group_action(self, event, action_name, num_accounts):
        """
        Handle the group action by calling the respective function for all selected accounts.
        """
        accounts = list(self.tbot.active_clients.values())[:num_accounts]
        for account in accounts:
            await getattr(self, action_name)(account, event)

    async def handle_individual_action(self, event, action_name, session):
        """
        Handle the individual action by calling the respective function for the selected account.
        """
        account = self.tbot.active_clients.get(session)
        if account:
            await getattr(self, action_name)(account, event)
        else:
            await event.respond(f"Account {session} not found.")

    async def reaction(self, account, event):
        """
        Perform the reaction action.
        """
        # Step 1: Ask for the link to the message
        await event.respond("Please provide the link to the message where the reaction will be applied.")
        self.tbot._conversations[event.chat_id] = 'reaction_link_handler'

    async def reaction_link_handler(self, event):
        """
        Handle the link input for the reaction action.
        """
        link = event.message.text.strip()
        await event.respond("Please select a reaction:", buttons=[
            Button.inline("👍", b'reaction_thumbsup'),
            Button.inline("❤️", b'reaction_heart'),
            Button.inline("😂", b'reaction_laugh'),
            Button.inline("😮", b'reaction_wow'),
            Button.inline("😢", b'reaction_sad'),
            Button.inline("😡", b'reaction_angry')
        ])
        self.tbot._conversations[event.chat_id] = 'reaction_select_handler'
        self.tbot.handlers['reaction_link'] = link

    async def reaction_select_handler(self, event):
        """
        Handle the reaction selection.
        """
        reaction = event.data.decode().split('_')[1]
        total_accounts = len(self.tbot.active_clients)
        await event.respond(f"Please specify the number of reactions (from 1 to {total_accounts}):")
        self.tbot._conversations[event.chat_id] = 'reaction_count_handler'
        self.tbot.handlers['reaction'] = reaction

    async def reaction_count_handler(self, event):
        """
        Handle the number of reactions input.
        """
        try:
            count = int(event.message.text.strip())
            if count < 1 or count > len(self.tbot.active_clients):
                raise ValueError("Invalid number of reactions.")
            link = self.tbot.handlers['reaction_link']
            reaction = self.tbot.handlers['reaction']
            accounts = list(self.tbot.active_clients.values())[:count]
            for account in accounts:
                await self.apply_reaction(account, link, reaction)
                await asyncio.sleep(random.randint(1, 10))
            await event.respond(f"Applied {reaction} reaction using {count} accounts.")
        except ValueError as e:
            await event.respond(f"Error: {e}. Please enter a valid number of reactions.")
            self.tbot._conversations[event.chat_id] = 'reaction_count_handler'

    async def apply_reaction(self, account, link, reaction):
        """
        Apply the selected reaction using the given account.
        """
        try:
            await account.send_message(link, reaction)
            logger.info(f"Applied {reaction} reaction using account {account.session.filename}")
        except Exception as e:
            logger.error(f"Error applying reaction: {e}")

    async def poll(self, account, event):
        """
        Perform the poll action.
        """
        # Implement the poll logic here
        await event.respond(f"Poll action performed by {account.session.filename}")

    async def join(self, account, event):
        """
        Perform the join action.
        """
        # Implement the join logic here
        await event.respond(f"Join action performed by {account.session.filename}")

    async def left(self, account, event):
        """
        Perform the left action.
        """
        # Implement the left logic here
        await event.respond(f"Left action performed by {account.session.filename}")

    async def block(self, account, event):
        """
        Perform the block action.
        """
        # Implement the block logic here
        await event.respond(f"Block action performed by {account.session.filename}")

    async def send_pv(self, account, event):
        """
        Perform the send_pv action.
        """
        # Implement the send_pv logic here
        await event.respond(f"Send PV action performed by {account.session.filename}")

    async def comment(self, account, event):
        """
        Perform the comment action.
        """
        # Implement the comment logic here
        await event.respond(f"Comment action performed by {account.session.filename}")

    async def exit(self, account, event):
        """
        Perform the exit action.
        """
        # Implement the exit logic here
        await event.respond(f"Exit action performed by {account.session.filename}")
