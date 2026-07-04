import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()
client = MongoClient(os.getenv('MONGODB_URI'))
db = client['welfarebot']
query = {"$or": [{"verified": False}, {"verified": {"$exists": False}}]}
print("unverified_query:", db.schemes.count_documents(query))
print("verified != True:", db.schemes.count_documents({"verified": {"$ne": True}}))
print("raw unverified_query:", db.raw_schemes.count_documents(query))
print("new unverified_query:", db.new_schemes.count_documents(query))
