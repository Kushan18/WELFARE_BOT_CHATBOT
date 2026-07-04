TELANGANA_SOURCES = [
    "https://www.telangana.gov.in/government-initiatives/",
    "https://en.vikaspedia.in/viewcontent/schemesall/state-specific-schemes/welfare-schemes-of-telangana",
    "https://en.vikaspedia.in/viewcontent/schemesall/state-specific-schemes/welfare-schemes-of-telangana/sc-welfare-schemes-telangana",
    "https://en.vikaspedia.in/viewcontent/schemesall/state-specific-schemes/welfare-schemes-of-telangana/bc-welfare-schemes-telangana",
    "https://en.vikaspedia.in/viewcontent/schemesall/state-specific-schemes/welfare-schemes-of-telangana/women-welfare-schemes-telangana",
]

ANDHRA_SOURCES = [
    "https://en.vikaspedia.in/viewcontent/schemesall/state-specific-schemes/welfare-schemes-of-andhra-pradesh",
    "https://socialwelfare.apcfss.in/schemes.html",
]

CENTRAL_SOURCES = [
    "https://en.vikaspedia.in/viewcontent/schemesall/central-sector-schemes",
    "https://sarkariyojana.com/",
]

STATE_SOURCE_MAP = {
    "telangana": TELANGANA_SOURCES,
    "andhra pradesh": ANDHRA_SOURCES,
    "all india": CENTRAL_SOURCES,
    "central": CENTRAL_SOURCES,
}

ALL_SOURCES = TELANGANA_SOURCES + ANDHRA_SOURCES + CENTRAL_SOURCES
