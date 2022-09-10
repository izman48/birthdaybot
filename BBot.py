#!bot.py
import os
import json
import discord
from discord.ext import tasks, commands
from dotenv import load_dotenv
from datetime import date as dt
import asyncio
from contextlib import suppress
import csv
from threading import Thread

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

BIRTHDAYS = []

client = discord.Client()


class BirthdayBot(commands.Bot):
    async def on_ready(self):
        print(f"{self.user.display_name} has connected to Discord!")
        self.initialize_birthdays()
        self._loop = None
        self.is_started = False
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
            self.write_to_file()
            await self.birthday_check()
            await asyncio.sleep(self.time)

    async def birthday_check(self):
        for member in self.guild.members:
            await member.remove_roles(self.birthday_role)

        today = dt.today().strftime("%d/%m")
        channel = self.get_channel(BIRTHDAY_CHANNEL)

        birthday_child = [
            item["discordID"] for item in BIRTHDAYS if item["date"] == today
        ]
        # print(*birthday_child, sep='\n')
        for bChild in birthday_child:
            print(bChild)
            response = f"@happy <@&{self.birthday_role.id}> <@!{bChild}>"
            await channel.send(response)
            member = self.guild.get_member(int(bChild))
            await member.add_roles(self.birthday_role)

    async def on_message(self, message):
        author = message.author
        if author == self.user:
            return

        role_ids = (str(role.id) for role in author.roles)

        words = message.content.split(" ")
        if words[0] == f"<@{self.user.id}>":

            response = "you called"

            if words[1] == "help":
                response = f"Possible commands are add and remove. Ex. @bBot add @izman48 19/06, @bBot remove @izman48"

            if words[1] == "add":
                # TOO MANY/NOT ENOUGH ARGUMENTS
                if len(words) > 4 or len(words) < 2:
                    response = "Command not recognized, try again like: Ex. @bBot add @izman48 19/06"
                    await message.channel.send(response)
                    return
                # IF A VALID USER TRIES TO SET A BIRTHDAY ALLOW THEM TO
                if len(words) == 4 and (
                    str(author.id) in S_USERS or bool(set(role_ids) & set(S_ROLES))
                ):
                    mentions = (
                        member.id
                        for member in message.mentions
                        if member.id != self.user.id
                    )
                    user = next(mentions)
                    date = words[3]
                # IF SOMEONE TRIES TO SET THEIR OWN BIRTHDAY (CAN ONLY BE DONE IF ITS NOT BEEN SET YET)
                if len(words) == 3:
                    for member in BIRTHDAYS:
                        if member["discordID"] == author.id:
                            response = "you can no longer edit your birthday, get an admin to do that for you"
                            await message.channel.send(response)
                            return
                    user = author.id
                    date = words[2]
                # IF TODAY IS BIRTHDAY GET TODAYS DATE
                if date == "today":
                    date = dt.today().strftime("%d/%m")
                if self.validate(date):
                    for member in BIRTHDAYS:
                        if member["discordID"] == user:
                            print(member["discordID"])
                            self.remove_member(user)
                            break
                    BIRTHDAYS.append({"discordID": user, "date": date})

                    response = "added user"
                else:
                    response = "invalid date"

            if words[1] == "remove":
                if str(author.id) in S_USERS or bool(set(role_ids) & set(S_ROLES)):
                    mentions = (
                        member.id
                        for member in message.mentions
                        if member.id != self.user.id
                    )
                    person = str(next(mentions))
                    self.remove_member(person)
                    response = "removed them"
                else:
                    response = "you can no longer edit your birthday, get an admin to do that for you"
            if words[1] == "wish":
                await self.birthday_check()
                return

            await message.channel.send(response)

    def remove_member(self, discordID):
        index = -1
        for i in range(len(BIRTHDAYS)):
            member = BIRTHDAYS[i]
            if discordID == member["discordID"]:
                index = i
        if index == -1:
            return
        BIRTHDAYS.pop(index)

        # UPDATE CSV FILE

        # with open(self.BIRTHDAY_LOCATION, "r") as source:
        #     reader = csv.reader(source)
        #     with open(self.BIRTHDAY_BACKUP_LOCATION, "w", newline='') as result:
        #         writer = csv.writer(result)
        #         for row in reader:
        #             if len(row) > 1 and  row[0] != discordID:
        #                 writer.writerow(row)
        # self.switch_files()

    def read_from_file(self, filename):
        print(filename)
        f = open(filename, "r")
        lines = f.readlines()

        lines = lines[1:]

        for line in lines:
            print(len(line))

        for line in lines:

            if len(line) > 1:
                data = line.split(",")

                BIRTHDAYS.append({"discordID": data[0], "date": data[1].rstrip("\n")})
        f.close()

    def write_to_file(self):

        with open(self.BIRTHDAY_LOCATION, "w") as f:
            f.write("discordid,date\n")
            for birthday in BIRTHDAYS:
                f.write(f'\n{birthday["discordID"]},{birthday["date"]}')

    def initialize_birthdays(self):

        self.read_from_file(self.BIRTHDAY_LOCATION)
        print(f"{self.user} has read birthdays from {BIRTHDAY_FILE}!")

    def validate(self, date):
        numbers = date.split("/")

        if len(numbers) != 2 or int(numbers[0]) > 31 or int(numbers[1]) > 12:
            return False

        return True


intents = discord.Intents.default()
intents.members = True
bBot = BirthdayBot(command_prefix="!", intents=intents)
bBot.run(TOKEN)
