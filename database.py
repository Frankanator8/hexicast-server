import certifi
import uuid
import pymongo as pymongo
from pymongo.server_api import ServerApi
import os
import time

# import urllib.request

# external_ip = urllib.request.urlopen('https://ident.me').read().decode('utf8')

# print(external_ip)

ca = certifi.where()

client = pymongo.MongoClient(
    f"mongodb+srv://frankanator8:{os.getenv('db_pass')}@games.2wtmq.mongodb.net/?retryWrites=true&w=majority",
    tlsCAFile=ca)

client.admin.command('ping')
print("Connected to database")


class Database:

    def __init__(self, database, collection):
        self.db = client[database][collection]

    def add_data(self, data):
        self.db.insert_one(data)

    def data_exists(self, **search):
        return self.db.count_documents(search) != 0

    def find_data(self, **search):
        return self.db.find_one(search)

    def find(self, **search):
        return self.db.find(search)

    def fill_data(self, otherDb, func):
        for document in otherDb.find():
            self.add_data(func(document["uuid"]))

    def update(self, key, value, **search):
        self.db.update_one(search, {"$set":{key: value}})

    def updateInc(self, key, value, **search):
        self.db.update_one(search, {"$inc":{key: value}})


auth = Database("hexicast", "game-auth")
glicko = Database("hexicast", "glicko")
name = Database("hexicast", "name")
displayNames = Database("hexicast", "display-names")
dates = Database("hexicast", "dates")
