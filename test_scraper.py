import os
import sys

# Ensure module path works
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scraper.manager import run_scraper

if __name__ == "__main__":
    print("Running scraper manually...")
    run_scraper()
    print("Scraper run completed.")
