"""Proposed Entity Catalogue roster: slug, Entity Type and the Listings it is keyed on.

Refs: ("OFAC", "<UID>") on the OFAC SDN List, ("UK", "<Unique ID>") on the UK Sanctions List.
"""

ROSTER = [
    # ---- Banks (20)
    ("sberbank", "bank", [("OFAC", "17018"), ("UK", "RUS0256")]),
    ("vtb-bank", "bank", [("OFAC", "17013"), ("UK", "RUS0250")]),
    ("gazprombank", "bank", [("OFAC", "17016"), ("UK", "RUS1072")]),
    ("alfa-bank", "bank", [("OFAC", "34682"), ("UK", "RUS1074")]),
    ("bank-rossiya", "bank", [("OFAC", "16681"), ("UK", "RUS0232")]),
    ("promsvyazbank", "bank", [("OFAC", "34656"), ("UK", "RUS0237")]),
    ("veb-rf", "bank", [("OFAC", "17015"), ("UK", "RUS0253")]),
    ("russian-agricultural-bank", "bank", [("UK", "RUS1073")]),
    ("t-bank", "bank", [("OFAC", "44259")]),
    ("sberbank-europe", "bank", [("OFAC", "18716")]),
    ("evrofinance-mosnarbank", "bank", [("OFAC", "26503"), ("UK", "RUS3620")]),
    ("bank-dabrabyt", "bank", [("OFAC", "34749"), ("UK", "BEL0120")]),
    ("belinvestbank", "bank", [("OFAC", "34752")]),
    ("alfa-bank-belarus", "bank", [("UK", "BEL0166")]),
    ("bank-melli-iran", "bank", [("OFAC", "25578"), ("UK", "INU0300")]),
    ("bank-mellat", "bank", [("OFAC", "25019"), ("UK", "INU0299")]),
    ("bank-sepah", "bank", [("OFAC", "25580"), ("UK", "INU0361")]),
    ("foreign-trade-bank-dprk", "bank", [("OFAC", "15603"), ("UK", "DPR0134")]),
    ("daedong-credit-bank", "bank", [("OFAC", "16085"), ("UK", "DPR0131")]),
    ("bandes", "bank", [("OFAC", "26587")]),
    # ---- Corporates (16)
    ("evraz-plc", "corporate", [("UK", "RUS1027")]),
    ("evraz-ntmk", "corporate", [("OFAC", "50054")]),
    ("rosneft", "corporate", [("OFAC", "17022"), ("UK", "RUS3064")]),
    ("rostec", "corporate", [("OFAC", "17260"), ("UK", "RUS0238")]),
    ("gazprom-neft", "corporate", [("OFAC", "17143"), ("UK", "RUS2383")]),
    ("sovcomflot", "corporate", [("OFAC", "34741"), ("UK", "RUS1097")]),
    ("alrosa", "corporate", [("OFAC", "34644"), ("UK", "RUS1075")]),
    ("belaruskali", "corporate", [("UK", "BEL0111")]),
    ("national-iranian-oil-company", "corporate", [("OFAC", "11317"), ("UK", "INU0318")]),
    ("irisl", "corporate", [("OFAC", "25396"), ("UK", "IRN0241")]),
    ("mahan-air", "corporate", [("OFAC", "12927")]),
    ("komid", "corporate", [("OFAC", "9345"), ("UK", "DPR0157")]),
    ("dandong-hongxiang", "corporate", [("OFAC", "20564")]),
    ("pdvsa", "corporate", [("OFAC", "26367")]),
    ("cham-holding", "corporate", [("OFAC", "12744"), ("UK", "SYR0287")]),
    ("syriatel", "corporate", [("UK", "SYR0336")]),
    # ---- Individuals (14)
    ("roman-abramovich", "individual", [("UK", "RUS0270")]),
    ("alexander-abramov", "individual", [("UK", "RUS1656")]),
    ("andrey-kostin", "individual", [("OFAC", "24063"), ("UK", "RUS0267")]),
    ("herman-gref", "individual", [("OFAC", "34796"), ("UK", "RUS1057")]),
    ("andrey-akimov", "individual", [("OFAC", "24316"), ("UK", "RUS1122")]),
    ("mikhail-fridman", "individual", [("OFAC", "44291"), ("UK", "RUS0664")]),
    ("yuri-kovalchuk", "individual", [("OFAC", "16680"), ("UK", "RUS0007")]),
    ("igor-sechin", "individual", [("OFAC", "16692"), ("UK", "RUS0273")]),
    ("sergey-chemezov", "individual", [("OFAC", "16685"), ("UK", "RUS0088")]),
    ("rami-makhlouf", "individual", [("OFAC", "10725"), ("UK", "SYR0204")]),
    ("fares-chehabi", "individual", [("UK", "SYR0041")]),
    ("ahmad-derakhshandeh", "individual", [("UK", "INU0275")]),
    ("simon-zerpa", "individual", [("OFAC", "22746")]),
    ("kim-chol-sam", "individual", [("OFAC", "16084"), ("UK", "DPR0226")]),
]

# LEIs found by GLEIF full-text search (api.gleif.org filter[fulltext]) and checked by hand
# against the Listing's name, country and registration number.
MANUAL_LEIS = {
    "russian-agricultural-bank": [("253400J0PTWKFG782T93", "GLEIF filter[fulltext]=Россельхозбанк; registeredAs 1027700342890")],
    "sberbank-europe": [("529900IZ8TASAYR3A694", "GLEIF filter[fulltext]=Sberbank Europe (matched a former name); registeredAs 161285i = OFAC Registration Number FN 161285 i")],
    "alfa-bank-belarus": [("253400CHFC0XZ6QMP406", "GLEIF filter[fulltext]=Альфа-Банк; legal address BY")],
    "bank-melli-iran": [("549300DK3GGPVDIPPV39", "GLEIF filter[fulltext]=Bank Melli; legal address IR")],
    "bank-sepah": [
        ("5493008Z30ZS378SB107", "GLEIF filter[fulltext]=Bank Sepah; legal address IR"),
        ("549300FFC0ZUJKJ8GZ78", "GLEIF filter[fulltext]=Bank Sepah; legal address IR (second record, 'BANK SEPAH HEAD OFFICE')"),
    ],
    "pdvsa": [("549300YWR8TN1OFD4P06", "GLEIF filter[fulltext]=Petroleos de Venezuela; legal address VE")],
}
