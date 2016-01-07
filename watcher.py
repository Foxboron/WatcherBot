import requests
import discord
import threading
import time
import hashlib
import json
import sys
import queue


admin_file = ".admins"
open(admin_file, "a").close()
hashes_file = ".hashes"
open(hashes_file, "a").close()


admins = []
chanlist = []
watching = {}

user, password = sys.argv[1:]

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
                    send_messages(chanlist, "Webpage has updates! "+k+"\n"+s)
                    print("ITS CHANGED: "+k)
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


@client.event
def on_message(message):
    msg = message.content.split(" ")

    if msg[0] == "!mods":
        client.send_message(message.channel, "@MrDetonia @nickforall @kolpet @nepeat")

    if msg[0] == "!bots":
        client.send_message(message.channel, "Bot written in Python by Foxboron source: https://github.com/Foxboron/WatcherBot")

    if msg[0] == ".help":
        s = "I'm a watcherbot! Tell an admin too add the webpage with .add.  Curret admins: " + " ".join(admins)
        client.send_message(message.channel, s)

    if msg[0] == ".source":
        s = "O'mighty source: https://github.com/Foxboron/WatcherBot"
        client.send_message(message.channel, s)

    if message.author.id not in admins:
        return

    if msg[0] == ".admin":
        try:
            user = get_user(message.server, msg[1])
        except CommandError as e:
            return client.send_message(message.channel, str(e))

        if user.id not in admins:
            client.send_message(message.channel, "Added admin " + msg[1])
            admins.append(user.id)
        else:
            client.send_message(message.channel, "User {user} is already an admin!".format(user=msg[1]))

    if msg[0] == ".add":
        client.send_message(message.channel, "Added webpage for watching: "+msg[1])
        r = requests.get(msg[1])
        hash = hashlib.sha224(r.text.encode("utf-8")).hexdigest()
        q.put_nowait((msg[1], hash))


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


q = queue.Queue()

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
    watching = {"http://104.131.44.161/": "d9efb9409d1c182e3f879740a08e93a9563c49ac5571b5a8818e8133"}

client.run()

