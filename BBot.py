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

import os
import json
from datetime import date as dt
import asyncio
from contextlib import suppress
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD = os.getenv("DISCORD_GUILD")
S_USERS = json.loads(os.environ["AUTHORIZED_USERS"])
S_ROLES = json.loads(os.environ["AUTHORIZED_ROLES"])
BIRTHDAY_FILE = os.getenv("BIRTHDAY_FILE_NAME")
BIRTHDAY_BACKUP_FILE = os.getenv("BIRTHDAY_BACKUP_FILE_NAME")
BIRTHDAY_LOCATION = ""
BIRTHDAY_BACKUP_LOCATION = ""
BIRTHDAY_CHANNEL = int(os.getenv("BIRTHDAY_WISH_CHANNEL"))
BIRTHDAY_ROLE = int(os.getenv("BIRTHDAY_ROLE"))
REST_TIME = int(os.getenv("RESET_TIME"))


client = discord.Client()


class BirthdayBot(commands.Bot):
    def author_in_birthdays(self, author):
        return any(lambda x: x["discordID"] == author.id in self.birthdays)

    def check_admin(self, author):
        role_ids = (str(role.id) for role in author.roles)
        return str(author.id) in S_USERS or any(map(lambda x: x in role_ids, S_ROLES))

    def remove_member(self, discordID):
        temp = self.birthdays
        self.birthdays = [
            birthday for birthday in temp if birthday["discordID"] != discordID
        ]
        if len(temp) > len(self.birthdays):
            return f"```removed {discordID} from birthday file```"
        return f"Can't find user with id: {discordID}"
        # self.birthdays = temp

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

    async def on_ready(self):
        print(f"{self.user.display_name} has connected to Discord!")
        self.birthdays = []
        self.initialize_birthdays()
        self._loop = None
        self.is_started = False
        # self.time = REST_TIME
        self.time = 10
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

        if words[0] == f"<@{self.user.id}>":
            if self.check_admin(author):
                # admin stuff
                # IF A VALID USER TRIES TO SET A BIRTHDAY ALLOW THEM TO
                # ex: @bbot add @izman48 19/06
                if len(words) == 4 and words[1] == "add":
                    user = next(mentions)
                    date = words[3]
                    response = self.add_birthday(user, date)

                if len(words) == 3 and words[1] == "remove":
                    person = str(next(mentions))
                    self.remove_member(person)
                    response = f"```removed {person} from birthday file```"

            if len(words) == 2 and words[1] == "help":
                response = "```Possible commands are add and remove. Ex. @bBot add @izman48 19/06, @bBot remove @izman48```"

            if len(words) == 3 and words[1] == "add":
                if self.author_in_birthdays(author):
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

    async def add_birthday(self, user, date):
        if date == "today":
            date = dt.today().strftime("%d/%m")
        if self.validate(date):
            for member in self.birthdays:
                if member["discordID"] == user:
                    print(member["discordID"])
                    self.remove_member(user)
                    break
            self.birthdays.append({"discordID": user, "date": date})

            response = "```added user```"
        else:
            response = "```invalid date```"
        return response


intents = discord.Intents.default()
intents.members = True
bBot = BirthdayBot(command_prefix="!", intents=intents)
bBot.run(TOKEN)
