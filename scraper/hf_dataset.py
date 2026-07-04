import os
import logging
import httpx
import io
import pandas as pd
from scraper.base import make_scheme
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()
logger = logging.getLogger(__name__)

HF_API_URL = "https://huggingface.co/api/datasets/shrijayan/gov_myscheme"

# Fallback URLs for possible parquet files
FALLBACK_PARQUET_URLS = [
    "https://huggingface.co/datasets/shrijayan/gov_myscheme/resolve/main/data/train-00000-of-00001.parquet",
    "https://huggingface.co/datasets/shrijayan/gov_myscheme/resolve/main/train.parquet",
    "https://huggingface.co/datasets/shrijayan/gov_myscheme/resolve/main/gov_myscheme.parquet",
]

def _fetch_parquet_records() -> list:
    """Fetch parquet file from HuggingFace dataset.
    Tries the dataset metadata first; if no parquet is listed, falls back to known URLs.
    Returns a list of records (dicts) or empty list on failure.
    """
    try:
        # First, try the official API metadata
        resp = httpx.get(HF_API_URL, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        data = resp.json()
        logger.info(f"hf_dataset: API response keys {list(data.keys())}")
        # Show full JSON for debugging (truncated to reasonable size)
        logger.debug(f"hf_dataset: full API response: {data}")
        parquet_name = None
        for sibling in data.get("siblings", []):
            name = sibling.get("rfilename", "")
            if name.endswith('.parquet'):
                parquet_name = name
                break
        if parquet_name:
            download_url = f"https://huggingface.co/datasets/shrijayan/gov_myscheme/resolve/main/{parquet_name}"
            logger.info(f"hf_dataset: downloading parquet from metadata {parquet_name}")
            r = httpx.get(download_url, timeout=30, follow_redirects=True)
            r.raise_for_status()
            df = pd.read_parquet(io.BytesIO(r.content), engine="pyarrow")
            logger.info(f"hf_dataset: parquet loaded with {len(df)} rows and columns {list(df.columns)}")
            return df.to_dict(orient="records")
        else:
            logger.warning("hf_dataset: No parquet file listed in metadata, trying fallback URLs")
    except Exception as e:
        logger.error(f"hf_dataset: error fetching metadata or parquet - {e}")

    # Fallback attempts
    for url in FALLBACK_PARQUET_URLS:
        try:
            head = httpx.head(url, timeout=10)
            if head.status_code == 200:
                logger.info(f"hf_dataset: fallback URL found {url}, downloading")
                r = httpx.get(url, timeout=30, follow_redirects=True)
                r.raise_for_status()
                df = pd.read_parquet(io.BytesIO(r.content), engine="pyarrow")
                logger.info(f"hf_dataset: fallback parquet loaded with {len(df)} rows and columns {list(df.columns)}")
                return df.to_dict(orient="records")
            else:
                logger.debug(f"hf_dataset: fallback URL {url} returned status {head.status_code}")
        except Exception as e:
            logger.error(f"hf_dataset: fallback download failed for {url} - {e}")
    logger.error("hf_dataset: all parquet download attempts failed")
    return []

def scrape():
    """Scrape the HuggingFace gov_myscheme dataset.
    Skips if staging already contains 50+ documents.
    Returns list of scheme dicts matching our schema.
    """
    try:
        client = MongoClient(os.getenv("MONGODB_URI"))
        db = client["welfarebot"]
        count = db["staging"].count_documents({})
        client.close()
        if count >= 50:
            logger.info("hf_dataset: staging already has sufficient data, skipping")
            return []
        records = _fetch_parquet_records()
        if not records:
            return []
        schemes = []
        for rec in records:
            state = str(rec.get("state") or "Central")
            priority = "Telangana" in state or "Andhra" in state
            scheme = make_scheme({
                "name": str(rec.get("scheme_name") or rec.get("name") or ""),
                "description": str(rec.get("description") or ""),
                "eligibility": str(rec.get("eligibility") or ""),
                "benefits": str(rec.get("benefits") or ""),
                "apply_link": str(rec.get("apply_link") or rec.get("url") or ""),
                "state": state,
                "source": "huggingface_myscheme",
                "category": str(rec.get("category") or "General"),
            })
            schemes.append((priority, scheme))
        # Prioritize Telangana/Andhra rows first
        schemes.sort(key=lambda x: not x[0])
        ordered = [s for _, s in schemes]
        logger.info(f"hf_dataset: loaded {len(ordered)} schemes")
        return ordered
    except Exception as e:
        logger.error(f"hf_dataset failed: {e}")
        return []