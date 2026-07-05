import os
import re
from urllib.parse import quote_plus, unquote_plus
from pymongo import MongoClient

def get_mongodb_uri(uri: str = None) -> str:
    if uri is None:
        uri = os.getenv("MONGODB_URI")
    if not uri:
        return uri
    
    # Clean up accidental whitespace or quotes from env variables
    uri = uri.strip().strip("'").strip('"')
    
    match = re.match(r"^(mongodb(?:\+srv)?://)(.*)@(.*)$", uri)
    if match:
        prefix, userpass, rest = match.groups()
        if ":" in userpass:
            user, pwd = userpass.split(":", 1)
            user = quote_plus(unquote_plus(user))
            pwd = quote_plus(unquote_plus(pwd))
            return f"{prefix}{user}:{pwd}@{rest}"
        else:
            user = quote_plus(unquote_plus(userpass))
            return f"{prefix}{user}@{rest}"
    return uri

def get_mongo_client(uri: str = None, **kwargs) -> MongoClient:
    if uri is None:
        escaped_uri = get_mongodb_uri()
    else:
        escaped_uri = get_mongodb_uri(uri)
    return MongoClient(escaped_uri, **kwargs)
