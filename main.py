from sanic.response import json
from sanic_limiter import Limiter, get_remote_address
import asyncio
import uuid as UUID
import copy
import time
import json as JSON
import random
import logging
from sanic import Sanic
from database import auth as authDB
from database import glicko as glickoDB
from database import name as nameDB
from database import displayNames as displayDB
from database import dates as datesDB
from auth import hash_password, verify_password
from rating import determineNewRating, getRating, changeRating
import os

app = Sanic('HexicastServer')
limiter = Limiter(app, key_func=get_remote_address)
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

db = {}


def add_db_category(db, name, backup, errorValue, clean):
    if clean:
        db[name] = copy.deepcopy(errorValue)

    else:
        try:
            db[name] = backup[name]

        except KeyError:
            db[name] = copy.deepcopy(errorValue)


def set_up_db(clean):
    backup = {}
    for key, item in db.items():
        backup[key] = copy.deepcopy(item)

    for key in db.keys():
        del db[key]

    add_db_category(db, "uuidName", backup, {}, clean)
    add_db_category(db, "pending", backup, {}, clean)
    add_db_category(db, "myGame", backup, {}, clean)
    add_db_category(db, "games", backup, {}, clean)
    add_db_category(db, "gameLoad", backup, [], clean)
    add_db_category(db, "codeToId", backup, {}, clean)
    add_db_category(db, "ratingBrackets", backup, {}, clean)
    add_db_category(db, "accountToGameUuid", backup, {}, clean)
    add_db_category(db, "gameToAccountUuid", backup, {}, clean)


@app.route('/')
async def hello_world(request):
    return json('Hello, World!')


@app.route("/maps", methods=["GET"])
@limiter.limit("1/minute")
async def getMaps(request):
    ret = []
    for mapName in os.listdir("maps/"):
        with open(f"maps/{mapName}") as f:
            string = f.read()

        map = [[[int(x) for x in c.split("/")] for c in x.strip().split()]
               for x in string.split("\n")]
        spawn = (map[-1][0][0], map[-1][1][0])
        map.pop(len(map) - 1)
        ret.append((mapName.split(".")[0], map))

    return json(ret)


@app.route("/queue", methods=["POST"])
@limiter.limit("1/minute")
async def queue(request):
    accountUuid = request.json["accountUuid"]
    uuid = request.json["uuid"]
    rating = glickoDB.find_data(uuid=accountUuid)["rating"]
    ratingBracket = round(rating // 50 * 50)
    if ratingBracket in db["ratingBrackets"].keys():
        for key in db["ratingBrackets"][ratingBracket].keys():
            if db["ratingBrackets"][ratingBracket][key] == "":
                db["ratingBrackets"][ratingBracket][
                    key] = await createGameFunc(
                    "ladderGame", key, {
                        "maxPlayers": 2,
                        "rated": True,
                        "show": False,
                        "type": "ladder"
                    })
                return db["ratingBrackets"][ratingBracket][key]

        db["ratingBrackets"][ratingBracket][uuid] = ""
        while True:
            if db["ratingBrackets"][ratingBracket][uuid] != "":
                return db["ratingBrackets"][ratingBracket][uuid]

            await asyncio.sleep(0.1)

    else:
        db["ratingBrackets"][ratingBracket] = {}
        db["ratingBrackets"][ratingBracket][uuid] = ""
        while True:
            if db["ratingBrackets"][ratingBracket][uuid] != "":
                return db["ratingBrackets"][ratingBracket][uuid]
            await asyncio.sleep(0.1)


@app.route("/signup", methods=["POST"])
@limiter.limit("1/minute")
async def signup(request):
    name = request.json["name"]
    disp = request.json["display"]
    pw = request.json["pw"]
    uuid = str(UUID.uuid4())
    if nameDB.data_exists(name=name):
        return json("TAKEN")

    authDB.add_data({"uuid": uuid, "hash": hash_password(pw)[0]})
    glickoDB.add_data({"uuid": uuid, "rating": 900, "rd": 350, "vol": 0.2})
    nameDB.add_data({"uuid": uuid, "name": name})
    displayDB.add_data({"uuid": uuid, "name": disp})
    datesDB.add_data({
        "uuid": uuid,
        "joined": time.time(),
        "lastOnline": time.time()
    })
    return json("GOOD")



@app.route("/login", methods=["POST"])
async def login(request):
    name = request.json["name"]
    pw = request.json["pw"]
    if not nameDB.data_exists(name=name):
        return json("NOACCEX")

    uuid = nameDB.find_data(name=name)["uuid"]
    hash = authDB.find_data(uuid=uuid)["hash"]
    if verify_password(pw, hash):
        return json(f'SUCCESS {uuid} {displayDB.find_data(uuid=uuid)["name"]}')

    else:
        return json("INCUSERPW")


@app.route("/getInfo", methods=["GET"])
@limiter.limit("30/minute")
def getUserInfo(request):
    username = request.args["username"]
    if nameDB.data_exists(name=username):
        uuid = nameDB.find_data(name=username)["uuid"]
        dateData = datesDB.find_data(uuid=uuid)
        data = {
            "rating": glickoDB.find_data(uuid=uuid)["rating"],
            "displayName": displayDB.find_data(uuid=uuid)["name"],
            "username": username,
            "lastOnline": dateData["lastOnline"],
            "joined": dateData["joined"]
        }
        return json(data)

    else:
        return json("DNE")


@app.route("/getInfoByUuid", methods=["GET"])
@limiter.limit("30/minute")
def getUserInfoByUuid(request):
    uuid = request.args["uuid"][0]
    if nameDB.data_exists(uuid=uuid):
        username = nameDB.find_data(uuid=uuid)["name"]
        dateData = datesDB.find_data(uuid=uuid)
        data = {
            "rating": glickoDB.find_data(uuid=uuid)["rating"],
            "displayName": displayDB.find_data(uuid=uuid)["name"],
            "username": username,
            "lastOnline": dateData["lastOnline"],
            "joined": dateData["joined"]
        }
        return json(data)

    else:
        return json("DNE")


@app.route("/join", methods=["POST"])
async def join(request):
    name = request.json["name"]
    accountUuid = request.json["accountUuid"]
    if accountUuid in db["accountToGameUuid"].keys():
        uuid = db["accountToGameUuid"][accountUuid]

    else:
        uuid = str(UUID.uuid4())
        db["uuidName"][uuid] = name
        if accountUuid != "":
            db["accountToGameUuid"][accountUuid] = uuid
            db["gameToAccountUuid"][uuid] = accountUuid

    return json(uuid)


@app.route("/createGame", methods=["POST"])
async def createGame(request):
    # map, players
    name = request.json["name"]
    settings = request.json["settings"]
    player_id = request.json["uuid"]
    return await createGameFunc(name, player_id, settings)


async def createGameFunc(name, player_id, settings):
    uuid = str(UUID.uuid4())
    db["pending"][uuid] = {
        "name": name,
        "host": player_id,
        "settings": settings,
        "players": []
    }
    return json(uuid)


@app.route("/createPrivateGame", methods=["POST"])
async def createPrivateGame(request):
    # map, players
    name = request.json["name"]
    if name in db["codeToId"].keys():
        return json("No")
    settings = request.json["settings"]
    player_id = request.json["uuid"]
    uuid = str(UUID.uuid4())
    db["pending"][uuid] = {
        "name": name,
        "host": player_id,
        "settings": settings,
        "players": []
    }
    db["codeToId"][name] = uuid
    return json(uuid)


@app.route("/joinPrivateGame", methods=["POST"])
@limiter.limit("15/minute")
async def joinPrivateGame(request):
    uuid = request.json["uuid"]
    try:
        game_id = db["codeToId"][request.json["game_id"]]

    except KeyError:
        return json("Game does not exist")

    if len(db["pending"][game_id]
           ["players"]) == db["pending"][game_id]["settings"]["maxPlayers"]:
        return json("Full game")

    await joinGameF(uuid, game_id)

    return json(game_id)


@app.route("/getGames", methods=["GET"])
async def getGames(request):
    ret = {}
    for key, item in db["pending"].items():
        if item["settings"]["show"]:
            ret[key] = item

    return json(ret)


@app.route("/getName", methods=["GET"])
@limiter.limit("60/minute")
async def getName(request):
    return json(db["uuidName"][request.args["uuid"][0]])


@app.route("/joinGame", methods=["POST"])
@limiter.limit("15/minute")
async def joinGame(request):
    uuid = request.json["uuid"]
    game_id = request.json["game_id"]
    if len(db["pending"][game_id]
           ["players"]) == db["pending"][game_id]["settings"]["maxPlayers"]:
        return json("No")

    await joinGameF(uuid, game_id)

    return json("")


async def joinGameF(uuid, game_id):
    db["pending"][game_id]["players"].append(uuid)

    if len(db["pending"][game_id]
           ["players"]) == db["pending"][game_id]["settings"]["maxPlayers"]:
        db["gameLoad"].append(game_id)
        for player in db["pending"][game_id]["players"]:
            db["myGame"][player] = game_id

        newGameData = db["pending"][game_id]
        newGameData["gameData"] = {}
        if "map" in db["pending"][game_id]["settings"].keys():
            with open(f"maps/{db['pending'][game_id]['settings']['map']}.txt"
                      ) as f:
                string = f.read()

        else:
            maps = os.listdir("maps/")
            with open(f"maps/{random.choice(maps)}") as f:
                string = f.read()

        map = [[[int(x) for x in c.split("/")] for c in x.strip().split()]
               for x in string.split("\n")]
        spawn = (map[-1][0][0], map[-1][1][0])
        map.pop(len(map) - 1)

        newGameData["gameData"]["map"] = map
        newGameData["gameData"]["playerPos"] = {}
        newGameData["gameData"]["spells"] = {}
        newGameData["gameData"]["period"] = 0
        newGameData["gameData"]["timeStart"] = time.time()
        newGameData["gameData"]["playerHealth"] = {}
        newGameData["gameData"]["alive"] = {}

        for player in db["pending"][game_id]["players"]:
            newGameData["gameData"]["playerHealth"][player] = 100
            newGameData["gameData"]["playerPos"][player] = [
                spawn[0], spawn[1],
                len(map[spawn[1]][spawn[0]]), "n"
            ]
            newGameData["gameData"]["alive"][player] = True

        newGameData["result"] = {}

        db["games"][game_id] = newGameData
        db["gameLoad"].remove(game_id)
        del db["pending"][game_id]


@app.route("/gameState", methods=["POST"])
async def gameState(request):
    uuid = request.json["uuid"]
    if uuid in db["gameLoad"]:
        return json("Loading")

    elif uuid in db["pending"].keys():
        return json("Pending")

    elif uuid in db["games"].keys():
        return json("Loaded")

    return json("DNE")


@app.websocket('/game')
async def handle_game(_, ws):
    while True:
        data = JSON.loads(await ws.recv())
        uuid = data["uuid"]
        request = data["request"]
        answer = {}
        if request == "ping":
            answer = {"recv": True}

        else:
            if uuid in db["myGame"].keys():
                game_id = db["myGame"][uuid]
                if game_id in db["games"].keys():
                    timeElapsed = time.time(
                    ) - db["games"][game_id]["gameData"]["timeStart"]
                    if timeElapsed < 30:
                        db["games"][game_id]["gameData"]["period"] = 0

                    elif 30 <= timeElapsed < 300:
                        db["games"][game_id]["gameData"]["period"] = 1

                    else:
                        db["games"][game_id]["gameData"]["period"] = 2

                    if request == "update":
                        db["games"][game_id]["gameData"]["playerPos"][
                            uuid] = data["pos"]

                        for key, value in data["newSpells"].items():
                            db["games"][game_id]["gameData"]["spells"][
                                key] = value

                        for key, value in data["deletedSpells"].items():
                            del db["games"][game_id]["gameData"]["spells"][key]

                        for player, change in data["healthChanges"].items():
                            db["games"][game_id]["gameData"]["playerHealth"][
                                player] += change
                            if db["games"][game_id]["gameData"][
                                "playerHealth"][player] > 100:
                                db["games"][game_id]["gameData"][
                                    "playerHealth"][player] = 100

                            if db["games"][game_id]["gameData"][
                                "playerHealth"][player] < 0:
                                db["games"][game_id]["gameData"][
                                    "playerHealth"][player] = 0
                                db["games"][game_id]["gameData"]["alive"][
                                    player] = False

                                if player not in db["games"][game_id][
                                    "result"].keys():
                                    db["games"][game_id]["result"][
                                        player] = time.time()
                        if len(db["games"][game_id]["result"].keys()
                               ) + 1 >= len(db["games"][game_id]["players"]):
                            if db["games"][game_id]["settings"]["rated"]:
                                allPlayers = set(
                                    db["games"][game_id]["players"])
                                res = []
                                for key, item in db["games"][game_id][
                                    "result"].items():
                                    res.append((key, item))
                                    allPlayers.remove(key)

                                res.sort(key=lambda x: x[1], reverse=True)
                                res.insert(
                                    0, (next(iter(allPlayers)), res[0][1] + 2))

                                ratingsL = []
                                rdsL = []
                                for person, _ in res:
                                    rating, rd, _ = getRating(
                                        db["gameToAccountUuid"][person])
                                    ratingsL.append(rating)
                                    rdsL.append(rd)

                                for index, item in enumerate(res):
                                    accountUuid = db["gameToAccountUuid"][
                                        item[0]]
                                    changeRating(
                                        accountUuid,
                                        *determineNewRating(
                                            *getRating(accountUuid),
                                            [False] * index + [True] *
                                            (len(res) - 1 - index),
                                            ratingsL[:index] +
                                            ratingsL[index + 1:],
                                            rdsL[:index] + rdsL[index + 1:],
                                            multiplier=1
                                            if db["games"][game_id]["settings"]
                                               ["type"] == "ladder" else 0.5))

                    answer = db["games"][game_id]

        await ws.send(JSON.dumps(answer))


async def run():
    app.run(host='0.0.0.0', port=8080, debug=False, access_log=False)


set_up_db(True)
if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(run())
