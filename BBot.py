# bot.py
# pylint:disable=missing-module-docstring
# pylint:disable=line-too-long
# pylint:disable=missing-class-docstring
# pylint:disable=missing-function-docstring
# pylint:disable=attribute-defined-outside-init
# pylint:disable=too-many-branches
# pylint:disable=redefined-outer-name
# pylint:disable=invalid-name
# pylint:disable=unspecified-encoding
# pylint:disable=assigning-non-slot
# pylint:disable=redefined-builtin

import os
import json
from datetime import date as dt
import asyncio
from contextlib import suppress
from typing import Optional
import discord
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD = os.getenv("DISCORD_GUILD")
S_USERS = json.loads(os.environ["AUTHORIZED_USERS"])
S_ROLES = json.loads(os.environ["AUTHORIZED_ROLES"])
BIRTHDAY_FILE = os.getenv("BIRTHDAY_FILE_NAME")
BIRTHDAY_CHANNEL = int(os.getenv("BIRTHDAY_WISH_CHANNEL"))
BIRTHDAY_ROLE = int(os.getenv("BIRTHDAY_ROLE"))
REST_TIME = int(os.getenv("RESET_TIME"))
MY_GUILD = discord.Object(id=653693334229090304)


class BirthdayBot(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.birthdays = []
        self.initialize_birthdays()
        self._loop = None
        self.is_started = False
        self.time = REST_TIME
        # self.time = 10

    def get_help_message(self):
        return """
        ```Possible slash commands are add and remove. Ex. /add today izman48. Remove is admin only.
        You can also use discord messages. Ex. @bBot add @izman48 19/06, @bBot remove @izman48.
        Other Commands are:
            @bBot list: List all users in list.
            @bBot wish: Manually ask the bot to wish everyone who has birthdays today.
        ```"""

    def birthday_exists_check(self, author_id):
        value = any(x["discordID"] == author_id for x in self.birthdays)
        return value

    def check_admin(self, author):
        role_ids = (str(role.id) for role in author.roles)
        return str(author.id) in S_USERS or any(map(lambda x: x in role_ids, S_ROLES))

    def add_birthday(self, user_id, date):
        if date == "today":
            date = dt.today().strftime("%d/%m")
        if self.validate(date):
            if self.birthday_exists_check(user_id):
                return "```User already in birthday list```"
            self.birthdays.append({"discordID": user_id, "date": date})

            response = f"```added user with id {user_id}```"
        else:
            response = "```invalid date```"
        return response

    def remove_birthday(self, discordID):
        temp = self.birthdays
        if not self.birthday_exists_check(discordID):
            return f"```Can't find user with id: {discordID}```"

        self.birthdays = [
            birthday for birthday in temp if birthday["discordID"] != discordID
        ]
        return f"```removed {discordID} from birthday file```"

    def read_from_file(self, filename):
        with open(filename, "r") as f:
            for line in f.readlines()[1:]:
                if len(line) > 1:
                    data = line.split(",")

                    self.birthdays.append(
                        {"discordID": data[0], "date": data[1].rstrip("\n")}
                    )

    def write_to_file(self, filename):
        with open(filename, "w") as f:
            f.write("discordID,date\n")
            for birthday in self.birthdays:
                f.write(f'\n{birthday["discordID"]},{birthday["date"]}')

    def initialize_birthdays(self):
        self.read_from_file(BIRTHDAY_FILE)
        print(f"{self.user} has read birthdays from {BIRTHDAY_FILE}!")

    def validate(self, date):
        numbers = date.split("/")
        return len(numbers) == 2 and int(numbers[0]) <= 31 or int(numbers[1]) <= 12

    async def setup_hook(self):
        self.tree.copy_global_to(guild=MY_GUILD)
        await self.tree.sync(guild=MY_GUILD)

    async def on_ready(self):
        print(f"{self.user.display_name} has connected to Discord!")
        self.guild = discord.utils.get(self.guilds, name=GUILD)
        self.birthday_role = [
            role for role in self.guild.roles if role.id == BIRTHDAY_ROLE
        ][0]

        print(
            f"{self.user} is connected to the following guild:\n"
            f"{self.guild.name}(id: {self.guild.id})"
        )

        users = "\n - ".join([user for user in S_USERS])
        roles = "\n - ".join([role for role in S_ROLES])
        print(f"Authorised Users:\n - {users}")
        print(f"Authorised Roles\n - {roles}")

        await self.startLoop()

    async def stop(self):
        if self.is_started:
            self.is_started = False
            # Stop task and await it stopped:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task

    async def startLoop(self):
        if not self.is_started:
            self.is_started = True
            self._task = asyncio.ensure_future(self._run())

    async def _run(self):
        while True:
            self.write_to_file(BIRTHDAY_FILE)
            await self.birthday_check()
            await asyncio.sleep(self.time)

    async def birthday_check(self):
        for member in self.guild.members:
            await member.remove_roles(self.birthday_role)

        today = dt.today().strftime("%d/%m")
        channel = self.get_channel(BIRTHDAY_CHANNEL)

        birthday_child = [
            item["discordID"] for item in self.birthdays if item["date"] == today
        ]
        for bChild in birthday_child:
            # print(bChild)
            response = f"@happy <@&{self.birthday_role.id}> <@!{bChild}>"
            await channel.send(response)
            member = self.guild.get_member(int(bChild))
            await member.add_roles(self.birthday_role)

    async def on_message(self, message):
        author = message.author
        if author == self.user:
            return

        mentions = (
            member.id for member in message.mentions if member.id != self.user.id
        )
        response = ""

        words = message.content.split(" ")
        if len(words) == 0:
            return
        try:

            if words[0] == f"<@{self.user.id}>":
                if self.check_admin(author):
                    if len(words) == 4 and words[1] == "add":
                        user = next(mentions)
                        date = words[3]
                        response = self.add_birthday(user, date)

                    if len(words) == 3 and words[1] == "remove":
                        person = str(next(mentions))
                        response = self.remove_birthday(person)

                    if len(words) == 2 and words[1] == "list":
                        birthdays = ",".join(
                            [str(x["discordID"]) for x in self.birthdays]
                        )
                        response = f"```{birthdays}```"

                if len(words) == 2 and words[1] == "help":
                    response = self.get_help_message()

                if len(words) == 3 and words[1] == "add":
                    if self.birthday_exists_check(author.id):
                        response = "```you can no longer edit your birthday, get an admin to do that for you```"
                        await message.channel.send(response)
                        return
                    user = author.id
                    date = words[2]
                    response = self.add_birthday(user, date)

                if len(words) == 2 and words[1] == "remove":
                    response = "```How did you get your birthday wrong? Get an admin to remove for you```"

                if len(words) == 2 and words[1] == "wish":
                    await self.birthday_check()
                    return
                if response:
                    await message.channel.send(response)
        except Exception as exc:
            print(exc)


intents = discord.Intents.default()
intents.members = True
bBot = BirthdayBot(intents=intents)


@bBot.tree.command()
@app_commands.describe(
    user="user who we add the bday to",
    date="The date for you birthday in day/month format, ex: 19/06",
)
async def add(
    interaction: discord.Interaction, date: str, user: Optional[discord.User] = None
):
    """Adds two numbers together."""
    try:
        if user is not None:
            if bBot.check_admin(interaction.user):
                response = bBot.add_birthday(str(user.id), date)
            else:
                response = "Not sufficient perms, speak to an admin"
        else:
            response = bBot.add_birthday(str(interaction.user.id), date)

    except Exception as exc:
        response = "Invalid command"
        print(exc)
    await interaction.response.send_message(f"{response}", ephemeral=True)


@bBot.tree.command()
@app_commands.describe(
    user="Who do you wanna remove from the birthday list",
)
async def remove(interaction: discord.Interaction, user: discord.User):
    """Adds two numbers together."""
    try:
        if bBot.check_admin(interaction.user):
            response = bBot.remove_birthday(str(user.id))
        else:
            response = "Not sufficient perms, speak to an admin"
    except Exception as exc:
        response = "Invalid command"
        print(exc)
    await interaction.response.send_message(f"{response}", ephemeral=True)


@bBot.tree.command(description="Help message (all the available commands)")
async def help(interaction: discord.Interaction):
    help_message = bBot.get_help_message()
    await interaction.response.send_message(
        help_message,
        ephemeral=True,
    )


bBot.run(TOKEN)
