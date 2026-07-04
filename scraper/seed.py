import logging
import os
import argparse
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()
logging.basicConfig(level=logging.INFO)

try:
    from scraper.manager import run_scraper
except ImportError:
    from .manager import run_scraper

def main():
    parser = argparse.ArgumentParser(description="WelfareBot scraper seeding script")
    parser.add_argument("--force", action="store_true", help="Clear the staging collection before seeding")
    args = parser.parse_args()

    if args.force:
        logging.info("Force flag detected: clearing staging collection before seeding")
        client = MongoClient(os.getenv("MONGODB_URI"))
        db = client["welfarebot"]
        db["staging"].delete_many({})
        client.close()
        logging.info("Staging collection cleared.")

    logging.info("Starting WelfareBot scraper seed...")
    run_scraper()

    client = MongoClient(os.getenv("MONGODB_URI"))
    db = client["welfarebot"]
    count = db["staging"].count_documents({})
    logging.info(f"Total schemes in staging: {count}")
    cursor = db["staging"].find({}, {"_id": 0, "name": 1, "state": 1, "source": 1}).limit(3)
    preview = list(cursor)
    print("Preview of first 3 schemes:")
    for s in preview:
        print(" -", s)
    client.close()

if __name__ == "__main__":
    main()
