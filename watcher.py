import requests
import discord
import threading
import time
import hashlib
import json
import queue
import os



admin_file = "/etc/configs/admins"
open(admin_file, "a").close()
hashes_file = "/etc/configs/hashes"
open(hashes_file, "a").close()

q = queue.Queue()
admins = []
chanlist = []
watching = {}
_commands = {}
wiki = "http://wiki.databutt.com/index.php"

user = os.environ.get("DISCORD_USER", None)
password = os.environ.get("DISCORD_PASSWORD", None)

if not user or not password:
    raise Exception("Your Discord login details are missing inside the enviornment. " +
                    "Please set DISCORD_USER and DISCORD_PASSWORD before running this bot.")

while True:
    try:
        client = discord.Client()
        client.login(user, password)
    except Exception as e:
        print(e)
        time.sleep(50)
    else:
        break


class CommandError(Exception):
    pass


def cmd(name, admin=False, help=""):
    def _(fn):
        _commands[name] = {
            "f": fn,
            "admin": admin,
            "help": help
        }
    return _


def get_user(server, username):
    users = []
    username = username.strip()

    if not username or username == "":
        raise CommandError("Username field is missing.")

    for member in server.members:
        if member.name == username or member.id == username:
            users.append(member)

    if len(users) == 0:
        raise CommandError("User '{user}' not found.".format(user=username))

    if len(users) > 1:
        extra = ""

        for user in users:
            extra += "'{username}' #{id} with roles {roles}\n".format(
                username=user.name,
                id=user.id,
                roles=" ".join([role.name for role in user.roles])
            )

        raise CommandError("Multiple users with the username {username} found.\n{extra}".format(
            username=username,
            extra=extra
        ))

    return users[0]


def send_messages(chanlist, msg):
    for chan in chanlist:
        try:
            client.send_message(chan, msg)
        except discord.errors.HTTPException as e:
            print(e)


def watcher(client, q):
    while True:
        print("Checking websites")
        for k, v in list(watching.items()):
            try:
                r = requests.get(k)
            except:
                pass
            else:
                hash = hashlib.sha224(r.text.encode("utf-8")).hexdigest()
                if hash != v:
                    s = ""
                    if k == "http://104.131.44.161/":
                        s += "```\n"
                        s += r.text
                        s += "\n```"
                    watching[k] = hash
                    try:
                        i = q.get_nowait()
                        if i:
                            watching[i[0]] = i[1]
                    except:
                        pass
                    send_messages(chanlist, "Webpage has updates! " + k + "\n" + s)
                    print("ITS CHANGED: " + k)
                    watching[k] = hash
                    print(hash)
        try:
            i = q.get_nowait()
            if i:
                watching[i[0]] = i[1]
        except:
            pass

        # Save
        with open(admin_file, "w+") as f:
            json.dump(admins, f)

        with open(hashes_file, "w+") as f:
            json.dump(watching, f)
        time.sleep(10)


# Discord events
@client.event
def on_message(message):
    msg = message.content.split(" ")

    for argument, command in _commands.items():
        if message.author.id not in admins and command["admin"] is True:
            continue

        if msg[0] == argument:
            try:
                command["f"](message)
            except CommandError as e:
                return client.send_message(message.channel, str(e))


@client.event
def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    chanlist.append(client.servers[0].get_default_channel())
    for i in list(client.get_all_channels()):
        if i.name == "bots":
            chanlist.append(i)
    t = threading.Thread(target=watcher, args=(client, q))
    t.daemon = True
    t.start()
    print('-----k-')


# Commands
@cmd("!mods", help="Hilights mods")
def command_mods(message):
    client.send_message(message.channel, "@MrDetonia @nickforall @kolpet @nepeat")


@cmd("!bots", help="Get info from all bots")
def command_bots(message):
    client.send_message(message.channel, "Bot written in Python by Foxboron source: https://github.com/Foxboron/WatcherBot")

@cmd("!wiki", help="Get a wiki page")
def wiki_cmd(message):
    msg = message.content.split(" ")
    if len(msg) >= 2:
        client.send_message(message.channel, wiki+"?title="+"+".join(msg[1:]))
    else:
        client.send_message(message.channel, wiki+"?title=Main_Page")

@cmd(".watch")
def watching(message):
    client.send_message(message.channel, str(list(watching.keys())))

@cmd(".help", help="Get this help")
def command_help(message):
    s="```\n"
    for k,v in _commands.items():
        s+="{cmd}: {help}\n".format(cmd=k, help=v["help"])
    s+="```"
    client.send_message(message.channel, s)


@cmd(".source", help="Get source")
def command_source(message):
    s = "O'mighty source: https://github.com/Foxboron/WatcherBot"
    client.send_message(message.channel, s)


@cmd(".amiadmin", help="Are you a bot herder?")
def command_amiadmin(message):
    if message.author.id in admins:
        client.send_message(message.channel, "Yes.")
    else:
        client.send_message(message.channel, "No.")


@cmd(".admin", help="Add new admin. Admins only", admin=True)
def command_admin(message):
    msg = message.content.split(" ")
    user = get_user(message.server, msg[1])

    if user.id not in admins:
        client.send_message(message.channel, "Added admin " + msg[1])
        admins.append(user.id)
    else:
        client.send_message(message.channel, "User {user} is already an admin!".format(user=msg[1]))


@cmd(".add", help="Add new webpage too watch. Admins only", admin=True)
def command_add(message):
    msg = message.content.split(" ")

    client.send_message(message.channel, "Added webpage for watching: " + msg[1])
    r = requests.get(msg[1])
    hash = hashlib.sha224(r.text.encode("utf-8")).hexdigest()
    q.put_nowait((msg[1], hash))

# Startup
try:
    admins = json.load(open(admin_file, "r+"))
except:
    admins = [
        "107244504934830080",  # @nepeat
        "66153853824802816",   # @Foxboron
        "132638759215824897",  # nickforall
        "134066166095151105"   # Retsam19
    ]

try:
    watching = json.load(open(hashes_file, "r+"))
except:
    # url => hash
    watching = {"http://104.131.44.161/": "4fa759b49bad7a52c46f573df80ec2cb9ef11e9c1b39b072f0fdfd43"}

client.run()
