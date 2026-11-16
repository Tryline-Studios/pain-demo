# Entity Catalogue candidate roster

Research for issue #16. It proposes 50 real Entities for the v1 Entity Catalogue (20 Banks, 16 Corporates, 14 Individuals) against the criteria and schema in the #6 resolution. Every fact below comes from the current OFAC SDN List and UK Sanctions List files, or from GLEIF. Nothing is taken from memory. **This roster is a proposal and needs the user's approval.**

**Snapshot.** All files were downloaded on 2026-09-16:

| Source | File | Publish date in file |
|---|---|---|
| OFAC SDN List | `SDN_ADVANCED.XML` (parsed) and `SDN.XML` (spot checks) from `https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/<FILE>` | `DateOfIssue` 2026-09-14; `Publish_Date` 09/14/2026; 19,388 records |
| UK Sanctions List | `https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.xml` | `DateGenerated` 11/09/2026; 6,340 designations |
| GLEIF BIC-to-LEI mapping | `https://mapping.gleif.org/api/v2/bic-lei/latest/download` → `lei-bic-20260828T000000.csv` | 2026-08-28; 39,347 rows |
| GLEIF LEI records | `https://api.gleif.org/api/v1/lei-records` | golden copy 2026-09-16 |

## TL;DR

- **All three must-includes are listed.**
  - **Roman Abramovich is UK-only.** He has one Listing of his own: UK `RUS0270` under the Russia regime, designated 2022-03-10. `SDN.XML` and `SDN_ADVANCED.XML` contain no "Abramovich" at all. No substitution is needed, because the UK Listing satisfies "every Entity has at least one Listing of its own".
  - Sberbank is on both lists (OFAC `17018`, UK `RUS0256`). Evraz PLC is UK-only (`RUS1027`), as #3 found.
- **Mix.**
  - List coverage: 32 Entities are on both lists, 9 are OFAC-only and 9 are UK-only.
  - Programmes: Russia 27, Iran 7, DPRK 5, Belarus 4, Syria 4, Venezuela 4. Evrofinance Mosnarbank counts under both Russia and Venezuela.
  - 31 of the 50 have at least one non-Latin name. The target was 17.
- **Every Bank has a BIC.**
  - 17 Banks have a BIC from OFAC's structured `SWIFT/BIC` feature.
  - The other 3 have a BIC from GLEIF only. Russian Agricultural Bank and Alfa Bank Belarus are UK-only.
  - Bank Melli Iran has no BIC on OFAC. GLEIF maps its lapsed LEI to `MELIIRT1` and five BICs in other countries.
- **Control Relationships.** 12 of the 14 Individuals have a Control Relationship that fits the schema. Each is quoted from a UK position, UK statement of reasons or OFAC title. Two need a decision:
  - `simon-zerpa`: OFAC gives the title "President of … BANDES" with no date, so current/former can't be sourced.
  - `kim-chol-sam`: he is "Treasurer" (OFAC) or "Representative" (UK) of Daedong Credit Bank. That role is not ultimate beneficial owner, controlling shareholder, director or parent company.
  - Two Legal-Entity parent links also qualify: Sberbank → Sberbank Europe AG (OFAC relationship) and Evraz PLC → Evraz NTMK (UK statement of reasons).
- **Gaps and surprises.**
  - **No Syrian Bank is listed on either list today**, so Syria is represented only by Corporates and Individuals.
  - **The UK Venezuela regime lists Individuals only**, so every Venezuelan Legal Entity is OFAC-only.
  - Several GLEIF records have moved on from the listed names. Sberbank Europe AG is now "MeSoFa Vermögensverwaltungs AG in Abwicklung". Evraz NTMK's registration number now belongs to "ПАО ЕВРАЗ".
  - More detail is in [Gaps, substitutions and surprises](#gaps-substitutions-and-surprises).

## Criteria checklist

| Criterion (#6 resolution) | Target | Proposed | Met |
|---|---|---|---|
| Total Entities | about 50 | 50 | yes |
| Banks | about 20 | 20 | yes |
| Corporates | about 16 | 16 | yes |
| Individuals | about 14 | 14 | yes |
| Must include Sberbank | yes | `sberbank` (OFAC 17018, UK RUS0256) | yes |
| Must include Evraz PLC | yes | `evraz-plc` (UK RUS1027) | yes |
| Must include Roman Abramovich | yes | `roman-abramovich` (UK RUS0270; not on OFAC SDN) | yes, UK-only |
| Programmes mostly Russia | majority | Russia 27 of 50 (Banks 11, Corporates 7, Individuals 9) | yes |
| Plus Iran | some | 7 (Banks 3, Corporates 3, Individuals 1) | yes |
| Plus DPRK | some | 5 (Banks 2, Corporates 2, Individuals 1) | yes |
| Plus Belarus | some | 4 (Banks 3, Corporates 1, Individuals 0) | yes, but no Belarus Individual |
| Plus Syria | some | 4 (Banks 0, Corporates 2, Individuals 2) | yes, but no Syrian Bank exists on either list |
| Plus Venezuela | some | 4 (Banks 2 incl. Evrofinance Mosnarbank, Corporates 1, Individuals 1) | yes |
| Both-list Entities | a mix | 32 (Banks 14, Corporates 9, Individuals 9) | yes |
| OFAC-only Entities | a mix | 9 (Banks 4, Corporates 4, Individuals 1) | yes |
| UK-only Entities | a mix | 9 (Banks 2, Corporates 3, Individuals 4) | yes |
| At least a third with a non-Latin name | ≥ 17 | 31 (Banks 12, Corporates 8, Individuals 11) | yes |
| Every Entity has a Listing of its own | all | 50 of 50 | yes |
| Individuals have a documented Control Relationship to a catalogue Legal Entity | where one exists | 12 fit the schema; 2 flagged (`simon-zerpa` status, `kim-chol-sam` role) | partly |
| Banks have a BIC (OFAC or GLEIF) | preferred | 20 of 20 (17 from an OFAC Listing, 3 from GLEIF only: `russian-agricultural-bank`, `alfa-bank-belarus`, `bank-melli-iran`) | yes |

Programme is counted per Entity, so Evrofinance Mosnarbank counts once for Russia and once for Venezuela. That is why the programme counts add up to 51. VTB Bank also carries OFAC `IRAN-EO13902`, but it is counted as Russia only.

## Summary table

"BIC" shows BIC8s. "(GLEIF)" marks a BIC found only in the GLEIF BIC-to-LEI mapping, not on a Listing. "Control Relationship" summarises the next section.

| # | id | Type | Programme | Lists | Listing IDs | Non-Latin | BIC | LEI | Control Relationship |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `sberbank` | bank | Russia | both | OFAC 17018, UK RUS0256 | yes | SABRINDD (GLEIF), SABRRUMM | `549300WE6TAF5EEWQS81` | parent of `sberbank-europe` |
| 2 | `vtb-bank` | bank | Russia | both | OFAC 17013, UK RUS0250 | yes | VTBRRUMM | `253400V1H6ART1UQ0N98` | — |
| 3 | `gazprombank` | bank | Russia | both | OFAC 17016, UK RUS1072 | yes | GAZPRUMM | `253400WSS48YWMBUA688` | — |
| 4 | `alfa-bank` | bank | Russia | both | OFAC 34682, UK RUS1074 | yes | ALFARUMM | `253400QWEQNERA6RJS29` | — |
| 5 | `bank-rossiya` | bank | Russia | both | OFAC 16681, UK RUS0232 | yes | ROSYRU2P | `2534006WDUE2J9S01D70` | — |
| 6 | `promsvyazbank` | bank | Russia | both | OFAC 34656, UK RUS0237 | yes | PRMSRUMM | `VX43JDHPWL0M8GQ0QU45` | — |
| 7 | `veb-rf` | bank | Russia | both | OFAC 17015, UK RUS0253 | yes | BFEARUMM | `25340076UP17XECUF417` | — |
| 8 | `russian-agricultural-bank` | bank | Russia | UK-only | UK RUS1073 | yes | RUAGRUMM (GLEIF) | `253400J0PTWKFG782T93` | — |
| 9 | `t-bank` | bank | Russia | OFAC-only | OFAC 44259 | no | TICSRUMM | `2534000KL0PLD6KG7T76` | — |
| 10 | `sberbank-europe` | bank | Russia | OFAC-only | OFAC 18716 | no | SABRATWW, VOINATW1 (GLEIF) | `529900IZ8TASAYR3A694` | subsidiary of `sberbank` |
| 11 | `evrofinance-mosnarbank` | bank | Russia, Venezuela | both | OFAC 26503, UK RUS3620 | yes | EVRFRUMM | `253400R9321UP8XXUB33` | — |
| 12 | `bank-dabrabyt` | bank | Belarus | both | OFAC 34749, UK BEL0120 | yes | MMBNBY22 | `253400W29T5225G8X631` | — |
| 13 | `belinvestbank` | bank | Belarus | OFAC-only | OFAC 34752 | no | BLBBBY2X | `253400XG24WV7PY3HY18` | — |
| 14 | `alfa-bank-belarus` | bank | Belarus | UK-only | UK BEL0166 | yes | ALFABY2X (GLEIF) | `253400CHFC0XZ6QMP406` | — |
| 15 | `bank-melli-iran` | bank | Iran | both | OFAC 25578, UK INU0300 | yes | MELIAEA1 (GLEIF), MELIAZ21 (GLEIF), MELIFRP1 (GLEIF), MELIIQB1 (GLEIF), MELIIRT1 (GLEIF), MELIOMR1 (GLEIF) | `549300DK3GGPVDIPPV39` | — |
| 16 | `bank-mellat` | bank | Iran | both | OFAC 25019, UK INU0299 | no | BKMTIRTH | — | — |
| 17 | `bank-sepah` | bank | Iran | both | OFAC 25580, UK INU0361 | no | SEPBDE21 (GLEIF), SEPBFRP1 (GLEIF), SEPBIRT1 (GLEIF), SEPBIRTH, SEPBITR1 (GLEIF) | `5493008Z30ZS378SB107`, `549300FFC0ZUJKJ8GZ78` | — |
| 18 | `foreign-trade-bank-dprk` | bank | DPRK | both | OFAC 15603, UK DPR0134 | no | FTBDKPPY | — | — |
| 19 | `daedong-credit-bank` | bank | DPRK | both | OFAC 16085, UK DPR0131 | no | DCBKKPPY | — | — |
| 20 | `bandes` | bank | Venezuela | OFAC-only | OFAC 26587 | no | FIVVVECA | `52990049IEUGB01L0409` | — |
| 21 | `evraz-plc` | corporate | Russia | UK-only | UK RUS1027 | yes | n/a | `5493005B7DAN39RXLK23` | parent of `evraz-ntmk` |
| 22 | `evraz-ntmk` | corporate | Russia | OFAC-only | OFAC 50054 | no | n/a | `25340007CAJLLJ6YBV26` | subsidiary of `evraz-plc` |
| 23 | `rosneft` | corporate | Russia | both | OFAC 17022, UK RUS3064 | yes | n/a | `253400JT3MQWNDKMJE44` | — |
| 24 | `rostec` | corporate | Russia | both | OFAC 17260, UK RUS0238 | yes | n/a | — | — |
| 25 | `gazprom-neft` | corporate | Russia | both | OFAC 17143, UK RUS2383 | yes | n/a | `253400KXA9P2AN72P004` | — |
| 26 | `sovcomflot` | corporate | Russia | both | OFAC 34741, UK RUS1097 | yes | n/a | `253400DYLWR5A6YAWJ69` | — |
| 27 | `alrosa` | corporate | Russia | both | OFAC 34644, UK RUS1075 | yes | n/a | `894500DKUWVBYZLLE651` | — |
| 28 | `belaruskali` | corporate | Belarus | UK-only | UK BEL0111 | yes | n/a | — | — |
| 29 | `national-iranian-oil-company` | corporate | Iran | both | OFAC 11317, UK INU0318 | yes | n/a | — | — |
| 30 | `irisl` | corporate | Iran | both | OFAC 25396, UK IRN0241 | no | n/a | — | — |
| 31 | `mahan-air` | corporate | Iran | OFAC-only | OFAC 12927 | no | n/a | — | — |
| 32 | `komid` | corporate | DPRK | both | OFAC 9345, UK DPR0157 | no | n/a | — | — |
| 33 | `dandong-hongxiang` | corporate | DPRK | OFAC-only | OFAC 20564 | no | n/a | — | — |
| 34 | `pdvsa` | corporate | Venezuela | OFAC-only | OFAC 26367 | no | n/a | `549300YWR8TN1OFD4P06` | — |
| 35 | `cham-holding` | corporate | Syria | both | OFAC 12744, UK SYR0287 | no | n/a | — | — |
| 36 | `syriatel` | corporate | Syria | UK-only | UK SYR0336 | no | n/a | — | — |
| 37 | `roman-abramovich` | individual | Russia | UK-only | UK RUS0270 | yes | n/a | n/a | UBO of `evraz-plc` (current) |
| 38 | `alexander-abramov` | individual | Russia | UK-only | UK RUS1656 | yes | n/a | n/a | director of `evraz-plc` (former); UBO of `evraz-plc` (current) |
| 39 | `andrey-kostin` | individual | Russia | both | OFAC 24063, UK RUS0267 | yes | n/a | n/a | director of `vtb-bank` (current) |
| 40 | `herman-gref` | individual | Russia | both | OFAC 34796, UK RUS1057 | yes | n/a | n/a | director of `sberbank` (current) |
| 41 | `andrey-akimov` | individual | Russia | both | OFAC 24316, UK RUS1122 | yes | n/a | n/a | director of `gazprombank` (current) |
| 42 | `mikhail-fridman` | individual | Russia | both | OFAC 44291, UK RUS0664 | yes | n/a | n/a | director of `alfa-bank` (former) |
| 43 | `yuri-kovalchuk` | individual | Russia | both | OFAC 16680, UK RUS0007 | yes | n/a | n/a | controlling shareholder + director of `bank-rossiya` (current) |
| 44 | `igor-sechin` | individual | Russia | both | OFAC 16692, UK RUS0273 | yes | n/a | n/a | director of `rosneft` (current) |
| 45 | `sergey-chemezov` | individual | Russia | both | OFAC 16685, UK RUS0088 | no | n/a | n/a | director of `rostec` (current) |
| 46 | `rami-makhlouf` | individual | Syria | both | OFAC 10725, UK SYR0204 | yes | n/a | n/a | UBO of `syriatel` (current) |
| 47 | `fares-chehabi` | individual | Syria | UK-only | UK SYR0041 | yes | n/a | n/a | director of `cham-holding` (current) |
| 48 | `ahmad-derakhshandeh` | individual | Iran | UK-only | UK INU0275 | no | n/a | n/a | director of `bank-sepah` (former) |
| 49 | `simon-zerpa` | individual | Venezuela | OFAC-only | OFAC 22746 | no | n/a | n/a | director of `bandes` (status not stated) ⚠ |
| 50 | `kim-chol-sam` | individual | DPRK | both | OFAC 16084, UK DPR0226 | yes | n/a | n/a | treasurer/representative of `daedong-credit-bank` (role not in schema) ⚠ |

## Control Relationships

Each row is a proposed entry for `catalogue/control_relationships.toml`. The quote is taken verbatim from the source Listing.
- **As of** is that UK entry's `LastUpdated` date, or the OFAC file date (2026-09-14) for OFAC sources.
- **Status** follows the source wording. "Former" appears only where the source says "former".
- UK statements of reasons state "reasonable grounds to suspect" and are not findings of fact. They are still the list's own text.

| # | Controller | Role | Controlled Legal Entity | Status | As of | Source and quote |
|---|---|---|---|---|---|---|
| 1 | `roman-abramovich` | ultimate beneficial owner | `evraz-plc` | current | 2025-04-09 | UK `RUS0270` statement of reasons: "ABRAMOVICH is involved in obtaining a benefit from or supporting the Government of Russia by owning or controlling directly or indirectly: (i) Evraz plc". Position: "Stakeholder in Evraz PLC and Norilsk Nickel". |
| 2 | `alexander-abramov` | director | `evraz-plc` | former | 2025-04-09 | UK `RUS1656` position: "Former Non-Executive Chairman and Director, Evraz Plc". Statement of reasons: "ABRAMOV is a former non-executive director of Evraz plc". |
| 3 | `alexander-abramov` | ultimate beneficial owner | `evraz-plc` | current | 2025-04-09 | UK `RUS1656` statement of reasons: "ABRAMOV is involved in obtaining a benefit from or supporting the Government of Russia by owning or controlling directly or indirectly (within the meaning of reg. 7 (2)) Evraz plc". |
| 4 | `andrey-kostin` | director | `vtb-bank` | current | 2025-04-09 | UK `RUS0267` positions: "President of VTB Bank (PJSC)", "Chairman of VTB Bank (PJSC) Management Board", "Member of the Supervisory Council of VTB Bank (PJSC)". |
| 5 | `herman-gref` | director | `sberbank` | current | 2025-04-09 | UK `RUS1057` position: "Chief Executive Officer and Chairman of the Board of PJSC SberBank". Statement of reasons: "He has served in this role since 2007". |
| 6 | `andrey-akimov` | director | `gazprombank` | current | 2025-04-09 | UK `RUS1122` statement of reasons: "AKIMOV is Chairman of the Management Board and Deputy Chairman of the Board of Directors at Gazprombank". OFAC `24316` title: "Chairman of the Management Board of Gazprombank". |
| 7 | `mikhail-fridman` | director | `alfa-bank` | former | 2026-06-24 | UK `RUS0664` position: "Former Member of the Board of Directors of Alfa-Bank Russia". |
| 8 | `yuri-kovalchuk` | controlling shareholder | `bank-rossiya` | current | 2025-04-09 | UK `RUS0007` statement of reasons: "As the chairman and largest shareholder of Bank Rossiya". Position: "Major shareholder of Bank Rossiya". The source says "largest", not "controlling". |
| 9 | `yuri-kovalchuk` | director | `bank-rossiya` | current | 2025-04-09 | Same UK `RUS0007` statement of reasons: "the chairman … of Bank Rossiya". |
| 10 | `igor-sechin` | director | `rosneft` | current | 2025-04-09 | UK `RUS0273` statement of reasons: "SECHIN is Chief Executive Officer, Chairman of the Management Board and Deputy Chairman of the Board of Directors at Rosneft". |
| 11 | `sergey-chemezov` | director | `rostec` | current | 2025-04-09 | UK `RUS0088` position: "Chair of the Rostec conglomerate". Statement of reasons: "including as CEO of the state technology holding company 'Rostec'. He chairs the Rostec conglomerate". |
| 12 | `rami-makhlouf` | ultimate beneficial owner | `syriatel` | current | 2025-05-01 | UK `SYR0336` (Syriatel's own Listing), other information: "Telecommunications sector. Controlled by Rami Makhlouf." |
| 13 | `fares-chehabi` | director | `cham-holding` | current | 2025-05-01 | UK `SYR0041` position: "Vice-chairman of Cham Holding". |
| 14 | `ahmad-derakhshandeh` | director | `bank-sepah` | former | 2025-10-01 | UK `INU0275` position: "Former Chairman and Managing Director of Bank Sepah". |
| 15 | `simon-zerpa` | director ⚠ | `bandes` | **not stated** | 2026-09-14 | OFAC `22746` title: "Vice President of Finance for Petroleos de Venezuela, S.A. (PDVSA) ; President of Venezuela's Economic and Social Development Bank (BANDES); President of Venezuela's National Development Fund (FONDEN)". The title is undated and the SDN listing date is 2017-07-26. |
| 16 | `kim-chol-sam` | **none of the four roles** ⚠ | `daedong-credit-bank` | current per UK wording | 2022-08-01 | OFAC `16084` title: "Treasurer, Daedong Credit Bank". UK `DPR0226` other information: "Kim Chol Sam is a representative for Daedong Credit Bank (DCB) who has been involved in managing transactions on behalf of DCB Finance Limited." |
| 17 | `sberbank` | parent company | `sberbank-europe` | current | 2026-09-14 | OFAC `SDN_ADVANCED.XML` `ProfileRelationship`: 18716 SBERBANK EUROPE AG "Owned or Controlled By" 17018, `Former="false"`. |
| 18 | `evraz-plc` | parent company | `evraz-ntmk` | current | 2025-04-09 | UK `RUS1027` statement of reasons: "Evraz plc is the UK-incorporated holding company … (2) owning or controlling directly or indirectly the following subsidiaries - JSC Evraz NTMK; …". OFAC lists the same plant as UID 50054 "Joint Stock Company Evraz Nizhny Tagil Metallurgical Plant". Matching NTMK to UID 50054 is by name. |

Relationships found and **not** proposed as Control Relationships:
- Rami Makhlouf and Cham Holding: UK `SYR0204` says only "Business interests: Interests in Syriatel, Cham Holding, …". "Interests" is not control.
- Eugene Shvidler and Evraz PLC: UK `RUS1100` says "Former Non-Executive Director, Evraz PLC". This is a documented former director relationship, but Shvidler was left out to keep the Individual mix beyond Evraz (see below).
- Evrofinance Mosnarbank and PDVSA: the OFAC relationship is "Providing support to", which is not control.
- Daedong Credit Bank and KOMID: UK `DPR0131` says DCB "has provided financial services to" KOMID. That is not control.

## Gaps, substitutions and surprises

**Must-includes**
- **Roman Abramovich has no OFAC SDN Listing.** He is designated only by the UK (`RUS0270`). He stays in the roster because the UK Listing is his own, so no substitute is needed. Any Sample File that needs an OFAC-matchable Evraz or Abramovich link must use `evraz-ntmk` (OFAC 50054).

**Programme gaps**
- **Syria has no listed Banks.**
  - Neither the OFAC `PAARSSR-EO13894` Entities nor the UK Syria regime Entities include a bank.
  - "Central Bank of Syria" appears only inside Individuals' positions and other information, such as "Governor of the Central Bank of Syria".
  - Syria is covered by `cham-holding`, `syriatel`, `rami-makhlouf` and `fares-chehabi`.
- **Venezuela is OFAC-only for Legal Entities.** The UK Venezuela regime lists 51 Individuals and no Entities. `bandes`, `pdvsa` and `simon-zerpa` are OFAC-only. `evrofinance-mosnarbank` is on the UK list only under the Russia regime (`RUS3620`, designated 2026-06-16).
- **Belarus has no Individual.** No UK Belarus Individual has a position that names Belaruskali, Bank Dabrabyt, Belinvestbank or Alfa Bank Belarus, and no OFAC Belarus Individual has a matching title.
- **Belaruskali is UK-only.** Neither OFAC file contains "Belaruskal".
- **Iran's UK Listings are recent re-designations.** Bank Melli, Bank Mellat and NIOC are dated 29/09/2025, and Bank Sepah 28/09/2025, under the Iran (Sanctions) (Nuclear) regime. Bank Melli keeps its old OFSI Group ID 10651. IRISL is under the Iran (Sanctions) Regulations 2023 (`IRN0241`).

**Banks and BICs**
- Every Bank has at least one BIC, so none is limited to placement by name.
  - **Russian Agricultural Bank** (UK-only) has no BIC or registration number on its Listing. GLEIF full-text search found LEI `253400J0PTWKFG782T93`, registered as 1027700342890, and both the record and the mapping give `RUAGRUMMXXX`.
  - **Alfa Bank Belarus** (UK-only) has LEI `253400CHFC0XZ6QMP406` and BIC `ALFABY2XXXX` from GLEIF.
  - **Bank Melli Iran** has no `SWIFT/BIC` on OFAC. GLEIF has a lapsed LEI `549300DK3GGPVDIPPV39` for "BANK MELLI IRAN" in IR. It maps to `MELIIRT1XXX` plus BICs with the country codes AE, AZ, FR, IQ and OM. The IR BIC8 in GLEIF is `MELIIRT1`, while OFAC gives Mellat and Sepah `…IRTH`.
  - **Bank Sepah**: OFAC gives `SEPBIRTH`. GLEIF has two lapsed IR LEIs, "BANK SEPAH" (`5493008Z30ZS378SB107`, mapped to `SEPBIRT1XXX` and others) and "BANK SEPAH HEAD OFFICE" (`549300FFC0ZUJKJ8GZ78`, no BIC). Which LEI belongs to the Entity is ambiguous.
- **Evrofinance Mosnarbank's UK entry lists "BIC 044525204"** under business registration numbers. That is the Russian domestic BIK, not a SWIFT BIC, so the loader must not treat it as one.
- **Sberbank Europe AG has been renamed and is in liquidation.** GLEIF LEI `529900IZ8TASAYR3A694` has registeredAs `161285i`, which matches OFAC's "FN 161285 i". Its legal name is now "MeSoFa Vermögensverwaltungs AG in Abwicklung" and its only mapped BIC is `VOINATW1XXX`, not the listed `SABRATWW`.
- **No GLEIF LEI was found** for Bank Mellat, the Foreign Trade Bank of the DPRK or Daedong Credit Bank.

**Corporates**
- **Evraz NTMK's registration number (1026601367539) belongs in GLEIF to "Публичное акционерное общество "ЕВРАЗ"."** That LEI is `25340007CAJLLJ6YBV26`, and it is lapsed. The name no longer matches the OFAC name, so treat the LEI as "same registration number, renamed" and confirm before storing it.
- No GLEIF LEI was found for Rostec, Belaruskali, NIOC, IRISL, Mahan Air, KOMID, Dandong Hongxiang, Cham Holding or Syriatel.
- **Two UK addresses have no country.** Syriatel (`SYR0336`: "Thawra Street, Ste Building 6th Floor, BP 2900") and Cham Holding (`SYR0287`) lack `AddressCountry`, so an ISO code cannot be sourced from the UK Listing. The OFAC address for Cham Holding does say Syria (`SY`).

**Names**
- The UK list often leaves out script and language for non-Latin names. Where it does, the detail below says "(inferred)", based on the Unicode block.
  - `kim-chol-sam`'s UK non-Latin name "(金铁三)" is in Han characters, but the source gives the language as "Korean".
  - `alfa-bank-belarus`'s "ЗАО Альфа-Банк" is labelled Belarusian by the source.
- `bank-melli-iran`'s UK non-Latin name carries a trailing comma in the source ("بانک ملی ایران,").
- `sergey-chemezov` has no non-Latin name on either list. Neither do 13 of the 18 Legal Entities that are outside the Russia programme.

**Individuals**
- **Neither list has a country-of-residence field.** The detail below gives the country of the Individual's listed address, country only, labelled as that. Addresses themselves are left out as the schema requires. Most Individuals have no listed address, so residence is "not listed".
- The chosen Individuals were preferred for having a Control Relationship to a catalogue Legal Entity. Alternatives with documented relationships that were left out:
  - Eugene Shvidler (UK-only), former director of Evraz PLC.
  - Petr Aven (both lists), former Chairman of the Board of Alfa-Bank Russia.
- No DPRK Individual with a schema-fitting role was found. A search of UK positions and OFAC titles that mention FTB, KKBC, DCB or KOMID turned up only "representative", "official" and "treasurer" roles.

## Method and data notes

- The parsing scripts are in `docs/research/scripts/entity-catalogue-roster/`:
  - `parse_lists.py` turns `SDN_ADVANCED.XML` and `UK-Sanctions-List.xml` into JSON.
  - `roster.py` holds the slugs and Listing IDs.
  - `build.py` collects the facts and runs the GLEIF lookups.
  - `render.py` writes the summary table and the per-Entity detail.
  - Run them with `uv run --python 3.13` against a scratch directory outside the repo.
- **OFAC Listing** is the `SanctionsEntry` on `ListID` 1550 ("SDN List"). Entries on the Sectoral Sanctions Identifications List and the Consolidated List are ignored.
  - **Programmes** are the `SanctionsMeasure` comments.
  - **SDN listing date** is that entry's `EntryEvent` date. For older Iranian Entities this is the SDN re-listing (for example 2018-11-05), not the first designation.
- **UK Listing** is the `Designation`, with `DateDesignated` and `LastUpdated` converted from dd/mm/yyyy.
- **Names**:
  - OFAC aliases with `LowQuality="true"` are excluded. UK names with `AliasStrength` "Low quality a.k.a" are excluded, though none in this roster have one.
  - OFAC name types come from `AliasTypeID` (Name = primary, A.K.A., F.K.A., N.K.A.). UK name types come from `NameType` (Primary Name, Primary Name Variation, Alias), with casing normalised.
  - OFAC non-Latin names carry their `ScriptID`. OFAC gives no language.
- **Addresses** keep the source lines. OFAC ISO codes come from the file's own `AreaCode` values, and UK English country names are mapped by hand.
- **Identifiers** are OFAC `IDRegDocument` entries of type Registration Number/ID, Tax ID No., Legal Entity Number and Government Gazette Number, plus UK `BusinessRegistrationNumber`. Individuals' ID documents are never collected.
- **GLEIF lookups** run in this order:
  1. OFAC "Legal Entity Number".
  2. The BIC-to-LEI mapping, matched on BIC8.
  3. `lei-records?filter[entity.registeredAs]=<registration number>`.
  4. For the rest, a hand-checked `filter[fulltext]` search. This covered Russian Agricultural Bank, Sberbank Europe, Alfa Bank Belarus, Bank Melli Iran, Bank Sepah and PDVSA.

  Each LEI's "found via" says which route found it.
- **Licensing** follows #3.
  - UK entries are OGL v3.0, so the catalogue's `NOTICE` must carry the attribution line.
  - OGL does not cover personal data. This document holds Individuals' names, dates and places of birth and nationalities, which the #6 schema already accepts.


## Per-Entity detail

Each entry is generated from the list files and GLEIF by `render.py`. Aliases leave out OFAC `LowQuality` and UK "Low quality a.k.a" names. The excluded weak aliases are listed for traceability only and do not go in the catalogue.

### Banks

#### `sberbank` (Bank)

- **Listings**
  - OFAC SDN UID `17018`: programmes `UKRAINE-EO13662`, `RUSSIA-EO14024`; SDN listing date 2022-04-06
  - UK Sanctions List `RUS0256`: The Russia (Sanctions) (EU Exit) Regulations 2019; designated 2022-03-01; last updated 2025-04-09; source UK; OFSI Group ID 15076
- **Primary name**: PUBLIC JOINT STOCK COMPANY SBERBANK OF RUSSIA (OFAC 17018); PJSC Sberbank (Public Joint-Stock Company Sberbank) (UK RUS0256)
- **Aliases** (weak and low-quality excluded): Sberbank Rossii *(a.k.a., OFAC 17018)*; Sberbank Rossii OAO *(f.k.a., OFAC 17018)*; Otkrytoe Aktsionernoe Obshchestvo Sberbank Rossii *(f.k.a., OFAC 17018)*; Sberbank of Russia *(a.k.a., OFAC 17018)*; PJSC Sberbank *(a.k.a., OFAC 17018)*; Open Joint Stock Company Sberbank of Russia *(f.k.a., OFAC 17018)*; OJSC Sberbank of Russia *(f.k.a., OFAC 17018)*; Joint Stock Commercial Savings Bank of the Russian Federation *(f.k.a., OFAC 17018)*; Joint Stock Commercial Savings Bank of the Russian Soviet Federative Socialist Republic *(f.k.a., OFAC 17018)*; Sberbank of RSFSR *(f.k.a., OFAC 17018)*; PJSC Sberbank of Russia *(primary variation, UK RUS0256)*; Sberbank *(primary variation, UK RUS0256)*; Sberbank of Russia *(primary variation, UK RUS0256)*
- **Non-Latin names**: ПУБЛИЧНОЕ АКЦИОНЕРНОЕ ОБЩЕСТВО СБЕРБАНК РОССИИ *(primary; script Cyrillic; language not stated; OFAC 17018)*; ПАО Сбербанк *(a.k.a.; script Cyrillic; language not stated; OFAC 17018)*; ПАО Сбербанк *(UK non-Latin name; script Cyrillic (inferred); language not stated; UK RUS0256)*
- **Excluded weak aliases**: Sberbank India; Sberbank Mumbai
- **Addresses**
  - 19 ul. Vavilova, Moscow, 117312; country Russia → `RU` (OFAC 17018)
  - C305/306A Lufthansa Centre 50 Liangmaqiao Rd., Chaoyang District, Beijing, 100027; country China → `CN` (OFAC 17018)
  - upper ground floor and fourth floor, Birla Tower, 25-Barakhamba Road, New Delhi, 110001; country India → `IN` (OFAC 17018)
  - 81-B, 8th Floor, 5th North Avenue, Maker Maxity, Bandra Kurla Complex, Bandra East, Mumbai, Maharashtra, 400051; country India → `IN` (OFAC 17018)
  - 19 Vavilova St., Moscow, 117997; country Russia → `RU` (UK RUS0256)
- **Registration numbers and LEIs on the Listings**: Registration Number `1027700132195` (Russia) (OFAC 17018); Tax ID No. `7707083893` (Russia) (OFAC 17018); Business registration number `1027700132195` (UK RUS0256)
- **UK type of entity**: Bank, Financial Services Company
- **BICs**: `SABRRUMM` (OFAC 17018); `SABRINDDXXX` (GLEIF BIC-to-LEI mapping → 549300WE6TAF5EEWQS81)
- **GLEIF LEI records**
  - `549300WE6TAF5EEWQS81`: Публичное акционерное общество "Сбербанк России"; RU; registeredAs 1027700132195; entity ACTIVE, registration ISSUED (last update 2026-06-11); found via GLEIF BIC-to-LEI mapping (lei-bic-20260828T000000.csv) for SABRRUMM; GLEIF lei-records filter[entity.registeredAs]=1027700132195

#### `vtb-bank` (Bank)

- **Listings**
  - OFAC SDN UID `17013`: programmes `UKRAINE-EO13662`, `RUSSIA-EO14024`, `IRAN-EO13902`; SDN listing date 2022-02-24
  - UK Sanctions List `RUS0250`: The Russia (Sanctions) (EU Exit) Regulations 2019; designated 2022-02-24; last updated 2025-04-09; source UK; OFSI Group ID 14195
- **Primary name**: VTB BANK PUBLIC JOINT STOCK COMPANY (OFAC 17013); VTB Bank (Public Joint-Stock Company) (UK RUS0250)
- **Aliases** (weak and low-quality excluded): JSC VTB BANK *(a.k.a., OFAC 17013)*; BANK VTB OPEN JOINT STOCK COMPANY *(a.k.a., OFAC 17013)*; BANK VNESHNEY TORGOVLI OPEN JOINT STOCK COMPANY *(a.k.a., OFAC 17013)*; BANK VNESHNEY TORGOVLI JOINT STOCK COMPANY *(a.k.a., OFAC 17013)*; BANK VNESHNEI TORGOVLI RSFSR *(a.k.a., OFAC 17013)*; BANK VNESHNEY TORGOVLI ROSSIYSKOY FEDERATSII CLOSED JOINT STOCK COMPANY *(a.k.a., OFAC 17013)*; VNESHTORGBANK ROSSII CLOSED JOINT STOCK COMPANY *(a.k.a., OFAC 17013)*; BANK VTB OAO *(a.k.a., OFAC 17013)*; VTB Bank PAO *(a.k.a., OFAC 17013)*; VTB BANK OAO *(a.k.a., OFAC 17013)*; VTB Bank PJSC *(a.k.a., OFAC 17013)*; Bank VTB Publichnoe Aktsionernoe Obshchestvo *(a.k.a., OFAC 17013)*; VTB Bank *(a.k.a., OFAC 17013)*; OAO Bank VTB *(a.k.a., OFAC 17013)*; VTB Bank open joint stock company *(a.k.a., OFAC 17013)*; Bank Vneshei Torgovli OAO *(a.k.a., OFAC 17013)*; Bank Vneshnei Torgovli Rossiskoi Federatsii as a Private Joint Stock Company *(a.k.a., OFAC 17013)*; OAO Vneshtorgbank *(a.k.a., OFAC 17013)*; Bank of Foreign Trade of the Russian Federation *(a.k.a., OFAC 17013)*; Bank for Foreign Trade of RSFSR *(a.k.a., OFAC 17013)*; Vneshtorgbank of RSFSR *(a.k.a., OFAC 17013)*; CJSC Bank for Foreign Trade of the Russian Federation *(a.k.a., OFAC 17013)*; Russian Vneshtorgbank *(a.k.a., OFAC 17013)*; Vneshtorgbank *(a.k.a., OFAC 17013)*; OJSC CJSC Bank for Foreign Trade *(a.k.a., OFAC 17013)*; Bank VTB PAO *(a.k.a., OFAC 17013)*; VTB Bank PJSC Shanghai Branch *(a.k.a., OFAC 17013)*; VTB *(primary variation, UK RUS0250)*; VTB Bank (PJSC) *(primary variation, UK RUS0250)*
- **Non-Latin names**: Банк ВТБ публичное акционерное общество *(primary; script Cyrillic; language not stated; OFAC 17013)*; Банк ВТБ ПАО *(a.k.a.; script Cyrillic; language not stated; OFAC 17013)*; Банк ВТБ (публичное акционерное общество) *(UK non-Latin name; script Cyrillic (inferred); language not stated; UK RUS0250)*
- **Excluded weak aliases**: JSC VTB Bank New Delhi Branch
- **Addresses**
  - 29, Bolshaya Morskaya str., St. Petersburg, 190000; country Russia → `RU` (OFAC 17013)
  - 37 Plyushchikha ul., Moscow, 119121; country Russia → `RU` (OFAC 17013)
  - 43, Vorontsovskaya str., Moscow, 109044; country Russia → `RU` (OFAC 17013)
  - 11 litera, per. Degtyarny, St. Petersburg, 191144; country Russia → `RU` (OFAC 17013)
  - 11, lit A, Degtyarnyy pereulok, St. Petersburg, 191144; country Russia → `RU` (OFAC 17013)
  - 43, bld.1, Vorontsovskaya str., Moscow, 109147; country Russia → `RU` (OFAC 17013)
  - Bashnya Zapad, Kompleks Federatsiya, 12, nab. Presnenskaya, Moscow, 123317; country Russia → `RU` (OFAC 17013)
  - str. 1, 43, ul. Vorontsovskaya, Moscow, 109147; country Russia → `RU` (OFAC 17013)
  - Vorontsovskaya Str 43, Moscow, 109147; country Russia → `RU` (OFAC 17013)
  - The Taj Mahal Hotel, Lobby Mezzanine Floor 1, Mansingh Road, New Delhi, 110001; country India → `IN` (OFAC 17013)
  - 1266 Nanjing Xilu Street, Jingan District, Shanghai, 200040; country China → `CN` (OFAC 17013)
  - 18 BC, CITIC Building, 19 Jianguomenwai Dajie, Beijing, 100004; country China → `CN` (OFAC 17013)
  - Tehran; country Iran → `IR` (OFAC 17013)
  - 11, lit A, Degtyarnyy pereulok, St. Petersburg, 191144; country Russia → `RU` (UK RUS0250)
- **Registration numbers and LEIs on the Listings**: Registration ID `1027739609391` (Russia) (OFAC 17013); Government Gazette Number `00032520` (Russia) (OFAC 17013); Tax ID No. `7702070139` (Russia) (OFAC 17013); Legal Entity Number `253400V1H6ART1UQ0N98` (OFAC 17013)
- **UK type of entity**: Public Joint-Stock Company
- **BICs**: `VTBRRUMM` (OFAC 17013)
- **GLEIF LEI records**
  - `253400V1H6ART1UQ0N98`: Банк ВТБ (публичное акционерное общество); RU; registeredAs 1027739609391; entity ACTIVE, registration ISSUED (last update 2026-05-26); found via OFAC 17013 Legal Entity Number; GLEIF BIC-to-LEI mapping (lei-bic-20260828T000000.csv) for VTBRRUMM; GLEIF lei-records filter[entity.registeredAs]=1027739609391

#### `gazprombank` (Bank)

- **Listings**
  - OFAC SDN UID `17016`: programmes `UKRAINE-EO13662`, `RUSSIA-EO14024`; SDN listing date 2024-11-21
  - UK Sanctions List `RUS1072`: The Russia (Sanctions) (EU Exit) Regulations 2019; designated 2022-03-24; last updated 2025-04-09; source UK; OFSI Group ID 15015
- **Primary name**: Gazprombank Joint Stock Company (OFAC 17016); Gazprombank (UK RUS1072)
- **Aliases** (weak and low-quality excluded): Gazprombank Open Joint Stock Company *(f.k.a., OFAC 17016)*; Bank GPB JSC *(a.k.a., OFAC 17016)*; Joint Stock Bank of the Gas Industry Gazprombank *(f.k.a., OFAC 17016)*
- **Non-Latin names**: Газпромбанк Акционерное общество *(primary; script Cyrillic; language not stated; OFAC 17016)*; Газпромбанк (АО) *(UK non-Latin name; script Cyrillic; language Russian; UK RUS1072)*
- **Addresses**
  - 16 Nametkina Street, Bldg. 1, Moscow, 117420; country Russia → `RU` (OFAC 17016)
  - 6 Enh-Taivan St., Ulaanbaatar, 14250; country Mongolia → `MN` (OFAC 17016)
  - 6 Floor, Business Center Q, Block A, Building 15A, Kabanbay Batyra Avenue, Astana, 010000; country Kazakhstan → `KZ` (OFAC 17016)
  - 10/48 Malcha Marg, Diplomatic Enclave, Chanakyapuri, Delhi, 110021; country India → `IN` (OFAC 17016)
  - Central International Trade Center, Suite No. 1205, Tower C, No. 6A Jianguomenwai Avenue, Chaoyang, Liaoning, 100022; country China → `CN` (OFAC 17016)
  - 16 Nametkina Street, Bldg. 1, Moscow, 117420; country Russia → `RU` (UK RUS1072)
- **Registration numbers and LEIs on the Listings**: Registration Number `1027700167110` (Russia) (OFAC 17016); Tax ID No. `7744001497` (Russia) (OFAC 17016); Legal Entity Number `253400WSS48YWMBUA688` (OFAC 17016)
- **BICs**: `GAZPRUMM` (OFAC 17016)
- **GLEIF LEI records**
  - `253400WSS48YWMBUA688`: "Газпромбанк" (Акционерное общество); RU; registeredAs 1027700167110; entity ACTIVE, registration ISSUED (last update 2026-02-11); found via OFAC 17016 Legal Entity Number; GLEIF BIC-to-LEI mapping (lei-bic-20260828T000000.csv) for GAZPRUMM; GLEIF lei-records filter[entity.registeredAs]=1027700167110

#### `alfa-bank` (Bank)

- **Listings**
  - OFAC SDN UID `34682`: programmes `RUSSIA-EO14024`, `UKRAINE-EO13662`; SDN listing date 2022-04-06
  - UK Sanctions List `RUS1074`: The Russia (Sanctions) (EU Exit) Regulations 2019; designated 2022-03-24; last updated 2025-04-09; source UK; OFSI Group ID 15017
- **Primary name**: JOINT STOCK COMPANY ALFA-BANK (OFAC 34682); Alfa-Bank JSC (UK RUS1074)
- **Aliases** (weak and low-quality excluded): ALFA-BANK *(a.k.a., OFAC 34682)*; JSC ALFA-BANK *(a.k.a., OFAC 34682)*; AO ALFA-BANK *(a.k.a., OFAC 34682)*; OPEN JOINT STOCK COMPANY ALFA-BANK *(f.k.a., OFAC 34682)*; Alfa-Bank Russia *(primary variation, UK RUS1074)*
- **Non-Latin names**: АКЦИОНЕРНОЕ ОБЩЕСТВО АЛЬФА-БАНК *(primary; script Cyrillic; language not stated; OFAC 34682)*; АО АЛЬФА-БАНК *(a.k.a.; script Cyrillic; language not stated; OFAC 34682)*; Альфа-Банка *(UK non-Latin name; script Cyrillic; language Russian; UK RUS1074)*
- **Addresses**
  - Kalanchevskaya Street 27, Moscow, 107078; country Russia → `RU` (OFAC 34682)
  - 27, Kalanchyovskaya Ul., Moscow, 107078; country Russia → `RU` (OFAC 34682)
  - 27 Kalanchevskaya str., Moscow, 107078; country Russia → `RU` (UK RUS1074)
- **Registration numbers and LEIs on the Listings**: Registration Number `1027700067328` (Russia) (OFAC 34682); Tax ID No. `7728168971` (Russia) (OFAC 34682)
- **UK type of entity**: Bank, Financial Services Company, JSC
- **BICs**: `ALFARUMM` (OFAC 34682)
- **GLEIF LEI records**
  - `253400QWEQNERA6RJS29`: АКЦИОНЕРНОЕ ОБЩЕСТВО "АЛЬФА-БАНК"; RU; registeredAs 1027700067328; entity ACTIVE, registration ISSUED (last update 2026-09-09); found via GLEIF BIC-to-LEI mapping (lei-bic-20260828T000000.csv) for ALFARUMM; GLEIF lei-records filter[entity.registeredAs]=1027700067328

#### `bank-rossiya` (Bank)

- **Listings**
  - OFAC SDN UID `16681`: programmes `UKRAINE-EO13661`; SDN listing date 2014-03-20
  - UK Sanctions List `RUS0232`: The Russia (Sanctions) (EU Exit) Regulations 2019; designated 2022-02-22; last updated 2025-04-09; source UK; OFSI Group ID 14177
- **Primary name**: BANK ROSSIYA (OFAC 16681); Bank Rossiya (UK RUS0232)
- **Aliases** (weak and low-quality excluded): AKTSIONERNY BANK RUSSIAN FEDERATION *(f.k.a., OFAC 16681)*; AB ROSSIYA, OAO *(a.k.a., OFAC 16681)*; OTKRYTOE AKTSIONERNOE OBSHCHESTVO AKTSIONERNY BANK ROSSIYA *(a.k.a., OFAC 16681)*; Bank of Russia *(primary variation, UK RUS0232)*; Russia Bank *(primary variation, UK RUS0232)*
- **Non-Latin names**: Акционерное общество "Акционерный Банк "РОССИЯ"' *(UK non-Latin name; script Cyrillic (inferred); language not stated; UK RUS0232)*
- **Addresses**
  - 2 Liter A Pl. Rastrelli, Saint Petersburg, 191124; country Russia → `RU` (OFAC 16681)
  - Rastrelli Square, 2A, Saint-Petersburg, 191124; country Russia → `RU` (UK RUS0232)
- **Registration numbers and LEIs on the Listings**: Government Gazette Number `09804148` (Russia) (OFAC 16681); Tax ID No. `7831000122` (Russia) (OFAC 16681); Registration ID `1027800000084` (Russia) (OFAC 16681); Business registration number `License number: 328` (UK RUS0232); Business registration number `INN: 7831000122` (UK RUS0232); Business registration number `OGRN: 1027800000084` (UK RUS0232)
- **UK type of entity**: Public Joint Stock Company (PJSC)
- **BICs**: `ROSYRU2P` (OFAC 16681)
- **GLEIF LEI records**
  - `2534006WDUE2J9S01D70`: Акционерное общество "Акционерный Банк "РОССИЯ"; RU; registeredAs 1027800000084; entity ACTIVE, registration LAPSED (last update 2024-10-28); found via GLEIF BIC-to-LEI mapping (lei-bic-20260828T000000.csv) for ROSYRU2P; GLEIF lei-records filter[entity.registeredAs]=1027800000084

#### `promsvyazbank` (Bank)

- **Listings**
  - OFAC SDN UID `34656`: programmes `RUSSIA-EO14024`, `UKRAINE-EO13662`; SDN listing date 2022-02-22
  - UK Sanctions List `RUS0237`: The Russia (Sanctions) (EU Exit) Regulations 2019; designated 2022-02-22; last updated 2025-04-09; source UK; OFSI Group ID 14184
- **Primary name**: PROMSVYAZBANK PUBLIC JOINT STOCK COMPANY (OFAC 34656); Public Joint Stock Company Promsvyazbank (UK RUS0237)
- **Aliases** (weak and low-quality excluded): PROMSVYAZBANK PJSC *(a.k.a., OFAC 34656)*; OJSC Promsvyazbank *(f.k.a., OFAC 34656)*; PROMSVYAZBANK PAO *(a.k.a., OFAC 34656)*; Publichnoe Aktsionernoe Obshchestvo Promsvyazbank *(a.k.a., OFAC 34656)*; PJSC Promsvyazbank *(primary variation, UK RUS0237)*; Promsvyazbank PJSC *(primary variation, UK RUS0237)*
- **Non-Latin names**: Публичное Акционерное Общество Промсвязьбанк *(primary; script Cyrillic; language not stated; OFAC 34656)*; ПАО Промсвязьбанк *(a.k.a.; script Cyrillic; language not stated; OFAC 34656)*; ПAO "Промсвязьбанк" *(UK non-Latin name; script Cyrillic (inferred); language not stated; UK RUS0237)*
- **Addresses**
  - Smirnovskaya Street 10/22, Moscow, 109052; country Russia → `RU` (OFAC 34656)
  - Room 1308, SCITECH Tower22, Jianguomenwai Dajie, Beijing, 100004; country China → `CN` (OFAC 34656)
  - 7, MunirkaMarg, Vasant Vhiar, New Delhi, 110057; country India → `IN` (OFAC 34656)
  - Building 22, Smirnovskaya Street, 10, Moscow, 109052; country Russia → `RU` (UK RUS0237)
- **Registration numbers and LEIs on the Listings**: Tax ID No. `7744000912` (Russia) (OFAC 34656); Registration Number `1027739019142` (Russia) (OFAC 34656); Government Gazette Number `40148343` (Russia) (OFAC 34656)
- **UK type of entity**: Public Joint Stock Company (PJSC)
- **BICs**: `PRMSRUMM` (OFAC 34656)
- **GLEIF LEI records**
  - `VX43JDHPWL0M8GQ0QU45`: Публичное акционерное общество "Банк ПСБ"; RU; registeredAs 1027739019142; entity ACTIVE, registration ISSUED (last update 2025-12-10); found via GLEIF BIC-to-LEI mapping (lei-bic-20260828T000000.csv) for PRMSRUMM; GLEIF lei-records filter[entity.registeredAs]=1027739019142

#### `veb-rf` (Bank)

- **Listings**
  - OFAC SDN UID `17015`: programmes `RUSSIA-EO14024`, `UKRAINE-EO13662`; SDN listing date 2018-08-15
  - UK Sanctions List `RUS0253`: The Russia (Sanctions) (EU Exit) Regulations 2019; designated 2022-02-28; last updated 2025-04-09; source UK; OFSI Group ID 14198
- **Primary name**: STATE CORPORATION BANK FOR DEVELOPMENT AND FOREIGN ECONOMIC AFFAIRS VNESHECONOMBANK (OFAC 17015); VEB.RF (UK RUS0253)
- **Aliases** (weak and low-quality excluded): GOSUDARSTVENNAYA KORPORATSIYA RAZVITIYA VEB.RF *(a.k.a., OFAC 17015)*; State Development Corporation VEB.RF *(a.k.a., OFAC 17015)*; GK VEB.RF *(a.k.a., OFAC 17015)*; VEB.RF *(a.k.a., OFAC 17015)*; Vnesheconombank *(f.k.a., OFAC 17015)*; Vneshekonombank SSSR *(f.k.a., OFAC 17015)*; Vneshekonombank GK *(f.k.a., OFAC 17015)*; Bank for Foreign Trade of the U.S.S.R. *(f.k.a., OFAC 17015)*; Vneshekonombank *(primary variation, UK RUS0253)*
- **Non-Latin names**: ГОСУДАРСТВЕННАЯ КОРПОРАЦИЯ РАЗВИТИЯ ВЭБ.РФ *(a.k.a.; script Cyrillic; language not stated; OFAC 17015)*; ВЭБ.РФ *(a.k.a.; script Cyrillic; language not stated; OFAC 17015)*; ВЭБ.РФ *(UK non-Latin name; script Cyrillic (inferred); language not stated; UK RUS0253)*
- **Excluded weak aliases**: VEB; Bank for Development
- **Addresses**
  - Akademik Sakharov Ave 9, Moscow, 107996; country Russia → `RU` (OFAC 17015)
  - Pr-kt, Akademika Sakharova, D. 9, Moscow, 107078; country Russia → `RU` (OFAC 17015)
  - 20A, CITIC Building, 19, Joanguomenwai Dajie, Beijing, 100004; country China → `CN` (OFAC 17015)
  - Shop No. 11, Arcade Ground Floor, World Trade Centre, Cuffe Prade, Colaba, Mumbai, 400005; country India → `IN` (OFAC 17015)
  - Akademia Sakharova Prospekt, Moscow, 107996; country Russia → `RU` (UK RUS0253)
- **Registration numbers and LEIs on the Listings**: Government Gazette Number `00005061` (Russia) (OFAC 17015); Registration Number `1077711000102` (Russia) (OFAC 17015); Tax ID No. `7750004150` (Russia) (OFAC 17015)
- **UK type of entity**: State Development Corporation, State Development Bank
- **BICs**: `BFEARUMM` (OFAC 17015)
- **GLEIF LEI records**
  - `25340076UP17XECUF417`: государственная корпорация развития "ВЭБ.РФ"; RU; registeredAs 1077711000102; entity ACTIVE, registration ISSUED (last update 2026-06-15); found via GLEIF BIC-to-LEI mapping (lei-bic-20260828T000000.csv) for BFEARUMM; GLEIF lei-records filter[entity.registeredAs]=1077711000102

#### `russian-agricultural-bank` (Bank)

- **Listings**
  - UK Sanctions List `RUS1073`: The Russia (Sanctions) (EU Exit) Regulations 2019; designated 2022-03-24; last updated 2025-04-09; source UK; OFSI Group ID 15016
- **Primary name**: Russian Agricultural Bank (UK RUS1073)
- **Aliases** (weak and low-quality excluded): JSC Rosselkhozbank *(primary variation, UK RUS1073)*; RusAg *(primary variation, UK RUS1073)*
- **Non-Latin names**: Россельхозбанк *(UK non-Latin name; script Cyrillic; language Russian; UK RUS1073)*
- **Addresses**
  - 0 Bld. 2 Presnenskaya Emb. (Moscow City, IQ-quarter Complex), Moscow, 123112; country Russia → `RU` (UK RUS1073)
  - 3, Gagarinsky Pereulok, Moscow, 119034; country Russia → `RU` (UK RUS1073)
- **BICs**: `RUAGRUMMXXX` (GLEIF BIC-to-LEI mapping → 253400J0PTWKFG782T93)
- **GLEIF LEI records**
  - `253400J0PTWKFG782T93`: Акционерное общество "Российский Сельскохозяйственный банк"; RU; registeredAs 1027700342890; entity ACTIVE, registration ISSUED (last update 2026-04-20); found via GLEIF filter[fulltext]=Россельхозбанк; registeredAs 1027700342890

#### `t-bank` (Bank)

- **Listings**
  - OFAC SDN UID `44259`: programmes `RUSSIA-EO14024`, `UKRAINE-EO13662`; SDN listing date 2023-07-20
- **Primary name**: T-BANK (OFAC 44259)
- **Aliases** (weak and low-quality excluded): Tinkoff Credit Systems Bank Closed Joint Stock Company *(a.k.a., OFAC 44259)*; Khimmashbank *(a.k.a., OFAC 44259)*; JSC Tinkoff Bank *(a.k.a., OFAC 44259)*
- **Non-Latin names**: none on either list
- **Addresses**
  - Ul. 2nd Khutorskaya, 38A, building 26, Moscow, 127287; country Russia → `RU` (OFAC 44259)
- **Registration numbers and LEIs on the Listings**: Legal Entity Number `2534000KL0PLD6KG7T76` (OFAC 44259); Registration Number `1027739642281` (Russia) (OFAC 44259); Tax ID No. `7710140679` (Russia) (OFAC 44259)
- **BICs**: `TICSRUMM` (OFAC 44259)
- **GLEIF LEI records**
  - `2534000KL0PLD6KG7T76`: Акционерное общество "ТБанк"; RU; registeredAs 1027739642281; entity ACTIVE, registration ISSUED (last update 2026-09-08); found via OFAC 44259 Legal Entity Number; GLEIF BIC-to-LEI mapping (lei-bic-20260828T000000.csv) for TICSRUMM; GLEIF lei-records filter[entity.registeredAs]=1027739642281

#### `sberbank-europe` (Bank)

- **Listings**
  - OFAC SDN UID `18716`: programmes `UKRAINE-EO13662`, `RUSSIA-EO14024`; SDN listing date 2022-04-06
- **Primary name**: SBERBANK EUROPE AG (OFAC 18716)
- **Aliases**: none
- **Non-Latin names**: none on either list
- **Addresses**
  - Schwarzenbergplatz 3, Vienna, 1010; country Austria → `AT` (OFAC 18716)
- **Registration numbers and LEIs on the Listings**: Registration Number `FN 161285 i` (Austria) (OFAC 18716); Tax ID No. `ATU55795009` (Austria) (OFAC 18716)
- **BICs**: `SABRATWW` (OFAC 18716); `VOINATW1XXX` (GLEIF BIC-to-LEI mapping → 529900IZ8TASAYR3A694)
- **GLEIF LEI records**
  - `529900IZ8TASAYR3A694`: MeSoFa Vermögensverwaltungs AG in Abwicklung; AT; registeredAs 161285i; entity ACTIVE, registration LAPSED (last update 2026-05-05); found via GLEIF filter[fulltext]=Sberbank Europe (matched a former name); registeredAs 161285i = OFAC Registration Number FN 161285 i

#### `evrofinance-mosnarbank` (Bank)

- **Listings**
  - OFAC SDN UID `26503`: programmes `VENEZUELA-EO13850`, `RUSSIA-EO14024`; SDN listing date 2019-03-11
  - UK Sanctions List `RUS3620`: The Russia (Sanctions) (EU Exit) Regulations 2019; designated 2026-06-16; last updated 2026-06-16; source UK; no OFSI Group ID
- **Primary name**: Evrofinance Mosnarbank (OFAC 26503); JOINT-STOCK COMMERCIAL BANK "EVROFINANCE MOSNARBANK" (JOINT-STOCK COMPANY) (UK RUS3620)
- **Aliases** (weak and low-quality excluded): Bank Evrofinance *(a.k.a., OFAC 26503)*; EVROFINANCE MOSNARBANK *(primary variation, UK RUS3620)*; JOINT-STOCK COMMERCIAL BANK "EVROFINANCE MOSNARBANK" *(primary variation, UK RUS3620)*; JSC JSCB "EVROFINANCE MOSNARBANK" *(primary variation, UK RUS3620)*
- **Non-Latin names**: АКЦИОНЕРНЫЙ КОММЕРЧЕСКИЙ БАНК "ЕВРОФИНАНС МОСНАРБАНК" (акционерное общество) *(UK non-Latin name; script Cyrillic; language Russian; UK RUS3620)*; АО АКБ «ЕВРОФИНАНС МОСНАРБАНК» *(UK non-Latin name; script Cyrillic; language Russian; UK RUS3620)*
- **Addresses**
  - 29, ul. Novy Arbat, Moscow, 121099; country Russia → `RU` (OFAC 26503)
  - Novy Arbat Street, 29, Moscow, 121099; country Russia → `RU` (UK RUS3620)
- **Registration numbers and LEIs on the Listings**: Registration ID `1027700565970` (Russia) (OFAC 26503); Tax ID No. `7703115760` (Russia) (OFAC 26503); Legal Entity Number `253400R9321UP8XXUB33` (OFAC 26503); Business registration number `OGRN 1027700565970` (UK RUS3620); Business registration number `Correspondent account: 30101810900000000204 in OCC No 1 of the Main Directorate of the Bank of Russia for the Central Federal District,` (UK RUS3620); Business registration number `BIC 044525204` (UK RUS3620); Business registration number `TIN 7703115760` (UK RUS3620); Business registration number `KPP 997950001 / 770401001` (UK RUS3620)
- **UK type of entity**: Bank
- **BICs**: `EVRFRUMM` (OFAC 26503)
- **GLEIF LEI records**
  - `253400R9321UP8XXUB33`: АКЦИОНЕРНЫЙ КОММЕРЧЕСКИЙ БАНК "ЕВРОФИНАНС МОСНАРБАНК" (акционерное общество); RU; registeredAs 1027700565970; entity ACTIVE, registration ISSUED (last update 2026-07-22); found via OFAC 26503 Legal Entity Number; GLEIF BIC-to-LEI mapping (lei-bic-20260828T000000.csv) for EVRFRUMM; GLEIF lei-records filter[entity.registeredAs]=1027700565970

#### `bank-dabrabyt` (Bank)

- **Listings**
  - OFAC SDN UID `34749`: programmes `BELARUS-EO14038`; SDN listing date 2022-02-24
  - UK Sanctions List `BEL0120`: The Republic of Belarus (Sanctions) (EU Exit) Regulations 2019; designated 2022-03-24; last updated 2025-04-09; source UK; OFSI Group ID 14979
- **Primary name**: Bank Dabrabyt Joint Stock Company (OFAC 34749); BANK DABRABYT JOINT STOCK COMPANY (UK BEL0120)
- **Aliases** (weak and low-quality excluded): OJSC Bank Dabrabyt *(a.k.a., OFAC 34749)*; Bank Dabrabyt JSC *(a.k.a., OFAC 34749)*; Bank Moscow-Minsk Joint stock Company *(f.k.a., OFAC 34749)*; Foreign Bank Moskva-Minsk *(f.k.a., OFAC 34749)*; Moscow-Minsk Foreign Bank *(f.k.a., OFAC 34749)*
- **Non-Latin names**: ОАО Банк Дабрабыт *(a.k.a.; script Cyrillic; language not stated; OFAC 34749)*; Банк Дабрабыт *(UK non-Latin name; script Cyrillic; language Russian; UK BEL0120)*
- **Addresses**
  - Kommunisticheskaya Str. 49, premises 1, Minsk, 220002; country Belarus → `BY` (OFAC 34749)
  - premises 1, Kommunisticheskaya Str. 49, Minsk; country Belarus → `BY` (UK BEL0120)
- **Registration numbers and LEIs on the Listings**: Registration Number `807000002` (Belarus) (OFAC 34749)
- **BICs**: `MMBNBY22` (OFAC 34749)
- **GLEIF LEI records**
  - `253400W29T5225G8X631`: Адкрытае акцыянернае таварыства "Банк Дабрабыт"; BY; registeredAs 807000002; entity ACTIVE, registration ISSUED (last update 2025-12-22); found via GLEIF BIC-to-LEI mapping (lei-bic-20260828T000000.csv) for MMBNBY22; GLEIF lei-records filter[entity.registeredAs]=807000002

#### `belinvestbank` (Bank)

- **Listings**
  - OFAC SDN UID `34752`: programmes `BELARUS-EO14038`; SDN listing date 2022-02-24
- **Primary name**: Belarussian Bank of Development and Reconstruction Belinvestbank Joint Stock Company (OFAC 34752)
- **Aliases** (weak and low-quality excluded): Belinvestbank *(a.k.a., OFAC 34752)*; Belinvestbank JSC *(a.k.a., OFAC 34752)*; Belarussian Bank of Development and Reconstruction Joint Stock Company *(a.k.a., OFAC 34752)*
- **Non-Latin names**: none on either list
- **Addresses**
  - 29 Masherova Av., Minsk, 220002; country Belarus → `BY` (OFAC 34752)
- **Registration numbers and LEIs on the Listings**: Registration Number `807000028` (Belarus) (OFAC 34752)
- **BICs**: `BLBBBY2X` (OFAC 34752)
- **GLEIF LEI records**
  - `253400XG24WV7PY3HY18`: Адкрытае акцыянернае таварыства "Беларускi банк развiцця i рэканструкцыi "Белiнвестбанк"; BY; registeredAs 807000028; entity ACTIVE, registration LAPSED (last update 2024-01-18); found via GLEIF BIC-to-LEI mapping (lei-bic-20260828T000000.csv) for BLBBBY2X; GLEIF lei-records filter[entity.registeredAs]=807000028

#### `alfa-bank-belarus` (Bank)

- **Listings**
  - UK Sanctions List `BEL0166`: The Republic of Belarus (Sanctions) (EU Exit) Regulations 2019; designated 2024-10-03; last updated 2025-04-09; source UK; OFSI Group ID 16597
- **Primary name**: CJSC Alfa Bank Belarus (UK BEL0166)
- **Aliases** (weak and low-quality excluded): Alfa Bank Belarus *(primary variation, UK BEL0166)*; Closed Joint Stock Company Alfa Bank *(primary variation, UK BEL0166)*
- **Non-Latin names**: ЗАО Альфа-Банк *(UK non-Latin name; script Cyrillic; language Belarusian; UK BEL0166)*
- **Addresses**
  - 43-47 Surganova Street, Minsk, 220013; country Belarus → `BY` (UK BEL0166)
- **UK type of entity**: Closed Joint Stock Company
- **BICs**: `ALFABY2XXXX` (GLEIF BIC-to-LEI mapping → 253400CHFC0XZ6QMP406)
- **GLEIF LEI records**
  - `253400CHFC0XZ6QMP406`: Закрытае акцыянернае таварыства «Альфа-Банк»; BY; registeredAs 101541947; entity ACTIVE, registration ISSUED (last update 2025-10-31); found via GLEIF filter[fulltext]=Альфа-Банк; legal address BY

#### `bank-melli-iran` (Bank)

- **Listings**
  - OFAC SDN UID `25578`: programmes `IFSR`, `IRAN`, `SDGT`; SDN listing date 2018-11-05
  - UK Sanctions List `INU0300`: The Iran (Sanctions) (Nuclear) (EU Exit) Regulations 2019; designated 2025-09-29; last updated 2025-09-29; source UK; OFSI Group ID 10651
- **Primary name**: Bank Melli Iran (OFAC 25578); Bank Melli (UK INU0300)
- **Aliases** (weak and low-quality excluded): Bank Melli *(a.k.a., OFAC 25578)*; Melli Bank *(a.k.a., OFAC 25578)*; National Bank of Iran *(a.k.a., OFAC 25578)*; Bank Melli Iran *(primary variation, UK INU0300)*; Melli Bank *(primary variation, UK INU0300)*; National Bank of Iran *(primary variation, UK INU0300)*
- **Non-Latin names**: بانک ملی ایران, *(UK non-Latin name; script Arabic (inferred); language Persian; UK INU0300)*
- **Excluded weak aliases**: BMI
- **Addresses**
  - Ferdowsi Avenue - PO Box 11365-171, Tehran; country Iran → `IR` (OFAC 25578)
  - 43 Avenue Montaigne, Paris, 75008; country France → `FR` (OFAC 25578)
  - Room 704-6, Wheelock Hse, 20 Pedder St; country Hong Kong → `HK` (OFAC 25578)
  - Bank Melli Iran Bldg, 111 St 24, 929 Arasat, Baghdad; country Iraq → `IQ` (OFAC 25578)
  - PO Box 2643, Ruwi, 112, Muscat; country Oman → `OM` (OFAC 25578)
  - PO Box 2656, Liva Street, Abu Dhabi; country United Arab Emirates → `AE` (OFAC 25578)
  - PO Box 248, Hamad Bin Abdulla St, Fujairah; country United Arab Emirates → `AE` (OFAC 25578)
  - PO Box 1888, Clock Tower, Industrial Rd, Al Ain Club Bldg, Al Ain, Abu Dhabi; country United Arab Emirates → `AE` (OFAC 25578)
  - PO Box 1894, Baniyas St, Deira, Dubai; country United Arab Emirates → `AE` (OFAC 25578)
  - PO Box 5270, Oman Street Al Nakheel, Ras Al-Khaimah; country United Arab Emirates → `AE` (OFAC 25578)
  - PO Box 459, Al Borj St, Sharjah; country United Arab Emirates → `AE` (OFAC 25578)
  - PO Box 3093, Ahmed Seddiqui Bldg, Khalid Bin El-Walid St, Bur-Dubai, Dubai; country United Arab Emirates → `AE` (OFAC 25578)
  - PO Box 1894, Al Wasl Rd, Jumeirah, Dubai; country United Arab Emirates → `AE` (OFAC 25578)
  - Postfach 112 129, Holzbruecke 2, 20421, Hamburg; country Germany → `DE` (OFAC 25578)
  - 23 Nobel Avenue, Baku; country Azerbaijan → `AZ` (OFAC 25578)
  - Bank Melli Iran Building, Ferdowsi Avenue, Tehran, 11365-144; country Iran → `IR` (OFAC 25578)
  - No. 136 Mirdamad Boulevard, Opposite Al-ghadir Mosque, Tehran; country Iran → `IR` (OFAC 25578)
  - Al Ashar Estiqlal Street - Hal Al Zohor, Basra; country Iraq → `IQ` (OFAC 25578)
  - 98a Kensington High Street, London, W8 4SG; country United Kingdom → `GB` (OFAC 25578)
  - 767 5th Ave, 44th Fl, New York, NY, 10153; country United States → `US` (OFAC 25578)
  - PO Box 1420, New York, NY, 10153; country United States → `US` (OFAC 25578)
  - Ferdowsi Avenue, Tehran, P.O Box 11365-171; country Iran → `IR` (UK INU0300)
- **Registration numbers and LEIs on the Listings**: Business registration number `60 · FC005874` (UK INU0300)
- **BICs**: `MELIAEA1XXX` (GLEIF BIC-to-LEI mapping → 549300DK3GGPVDIPPV39); `MELIAZ21XXX` (GLEIF BIC-to-LEI mapping → 549300DK3GGPVDIPPV39); `MELIFRP1XXX` (GLEIF BIC-to-LEI mapping → 549300DK3GGPVDIPPV39); `MELIIQB1XXX` (GLEIF BIC-to-LEI mapping → 549300DK3GGPVDIPPV39); `MELIIRT1XXX` (GLEIF BIC-to-LEI mapping → 549300DK3GGPVDIPPV39); `MELIOMR1XXX` (GLEIF BIC-to-LEI mapping → 549300DK3GGPVDIPPV39)
- **GLEIF LEI records**
  - `549300DK3GGPVDIPPV39`: BANK MELLI IRAN; IR; registeredAs 60; entity ACTIVE, registration LAPSED (last update 2024-10-25); found via GLEIF filter[fulltext]=Bank Melli; legal address IR

#### `bank-mellat` (Bank)

- **Listings**
  - OFAC SDN UID `25019`: programmes `IFSR`, `SDGT`, `IRAN`; SDN listing date 2018-10-16
  - UK Sanctions List `INU0299`: The Iran (Sanctions) (Nuclear) (EU Exit) Regulations 2019; designated 2025-09-29; last updated 2025-09-29; source UK; OFSI Group ID 11166
- **Primary name**: Bank Mellat (OFAC 25019); Bank Mellat (UK INU0299)
- **Aliases** (weak and low-quality excluded): Mellat International Bank *(primary variation, UK INU0299)*; Nation's Bank *(primary variation, UK INU0299)*
- **Non-Latin names**: none on either list
- **Addresses**
  - Head Office Bldg, 276 Taleghani Ave, Tehran; country Iran → `IR` (OFAC 25019)
  - Head Office Building, 327 Takeghani (Taleghani) Avenue, Tehran, 15817; country Iran → `IR` (UK INU0299)
- **BICs**: `BKMTIRTH` (OFAC 25019)
- **GLEIF LEI**: none found

#### `bank-sepah` (Bank)

- **Listings**
  - OFAC SDN UID `25580`: programmes `IFSR`, `IRAN`, `NPWMD`; SDN listing date 2018-11-05
  - UK Sanctions List `INU0361`: The Iran (Sanctions) (Nuclear) (EU Exit) Regulations 2019; designated 2025-09-28; last updated 2026-02-13; source UN; OFSI Group ID 17103; UN ref IRe.007
- **Primary name**: Bank Sepah (OFAC 25580); Bank Sepah (UK INU0361)
- **Aliases** (weak and low-quality excluded): Bank Sepah International *(primary variation, UK INU0361)*
- **Non-Latin names**: none on either list
- **Addresses**
  - Negin Sepah Building, Head Office of Bank Sepah, Nowrouz Street, Africa Hwy, Argentina Square, Tehran; country Iran → `IR` (OFAC 25580)
  - 6th Floor, Negin Sepah Building, Nowrouz St., Africa Hwy., Argentina Sq., Tehran, 1519662840; country Iran → `IR` (OFAC 25580)
  - Imam Khomeini Square - PO Box 11364, Tehran; country Iran → `IR` (OFAC 25580)
  - Hafenstrasse 54, D-60327, Frankfurt am Main; country Germany → `DE` (OFAC 25580)
  - PO Box 110261, Franfurt am Main, Hessen, 60037; country Germany → `DE` (OFAC 25580)
  - 20 Rue Auguste Vacquerie, Paris, 75016; country France → `FR` (OFAC 25580)
  - Via Barberini 50, Rome, 00187; country Italy → `IT` (OFAC 25580)
- **Registration numbers and LEIs on the Listings**: Registration Number `4293` (OFAC 25580)
- **BICs**: `SEPBIRTH` (OFAC 25580); `SEPBDE21XXX` (GLEIF BIC-to-LEI mapping → 5493008Z30ZS378SB107); `SEPBFRP1XXX` (GLEIF BIC-to-LEI mapping → 5493008Z30ZS378SB107); `SEPBIRT1XXX` (GLEIF BIC-to-LEI mapping → 5493008Z30ZS378SB107); `SEPBITR1XXX` (GLEIF BIC-to-LEI mapping → 5493008Z30ZS378SB107)
- **GLEIF LEI records**
  - `5493008Z30ZS378SB107`: BANK SEPAH; IR; registeredAs —; entity ACTIVE, registration LAPSED (last update 2024-05-23); found via GLEIF filter[fulltext]=Bank Sepah; legal address IR
  - `549300FFC0ZUJKJ8GZ78`: BANK SEPAH HEAD OFFICE; IR; registeredAs —; entity ACTIVE, registration LAPSED (last update 2026-03-19); found via GLEIF filter[fulltext]=Bank Sepah; legal address IR (second record, 'BANK SEPAH HEAD OFFICE')

#### `foreign-trade-bank-dprk` (Bank)

- **Listings**
  - OFAC SDN UID `15603`: programmes `DPRK3`, `NPWMD`; SDN listing date 2013-03-11
  - UK Sanctions List `DPR0134`: The Democratic People's Republic of Korea (Sanctions) (EU Exit) Regulations 2019; designated 2017-08-05; last updated 2022-08-01; source UN; OFSI Group ID 13536; UN ref KPe.047
- **Primary name**: FOREIGN TRADE BANK OF THE DEMOCRATIC PEOPLE'S REPUBLIC OF KOREA (OFAC 15603); FOREIGN TRADE BANK (FTB) (UK DPR0134)
- **Aliases** (weak and low-quality excluded): NORTH KOREA'S FOREIGN TRADE BANK *(a.k.a., OFAC 15603)*; Mooyokbank *(a.k.a., OFAC 15603)*; Korea Trade Bank *(a.k.a., OFAC 15603)*; Korea Trading Bank *(a.k.a., UK DPR0134)*; Mooyokbank *(a.k.a., UK DPR0134)*
- **Non-Latin names**: none on either list
- **Addresses**
  - FTB Building, Jungsong-dong, Central District, Pyongyang; country Korea, North → `KP` (OFAC 15603)
  - FTB Building, Jungsong-dong, Central District, Pyongyang; country North Korea → `KP` (UK DPR0134)
- **BICs**: `FTBDKPPY` (OFAC 15603)
- **GLEIF LEI**: none found

#### `daedong-credit-bank` (Bank)

- **Listings**
  - OFAC SDN UID `16085`: programmes `NPWMD`; SDN listing date 2013-06-27
  - UK Sanctions List `DPR0131`: The Democratic People's Republic of Korea (Sanctions) (EU Exit) Regulations 2019; designated 2016-03-02; last updated 2022-08-01; source UN; OFSI Group ID 13341; UN ref KPe.023
- **Primary name**: DAEDONG CREDIT BANK (OFAC 16085); DAEDONG CREDIT BANK (DCB) (UK DPR0131)
- **Aliases** (weak and low-quality excluded): DAE-DONG CREDIT BANK *(a.k.a., OFAC 16085)*; TAEDONG CREDIT BANK *(a.k.a., OFAC 16085)*; Dae-Dong Credit Bank *(a.k.a., UK DPR0131)*; DCB *(a.k.a., UK DPR0131)*; Taedong Credit Bank *(a.k.a., UK DPR0131)*
- **Non-Latin names**: none on either list
- **Excluded weak aliases**: DCB
- **Addresses**
  - Suite 401, Potonggang Hotel, Ansan-Dong, Pyongchon District, Pyongyang; country Korea, North → `KP` (OFAC 16085)
  - Ansan-dong, Botongang Hotel, Pongchon, Pyongyang; country Korea, North → `KP` (OFAC 16085)
  - Ansan-dong, Botonggang Hotel, Pongchon, Pyongyang; country North Korea → `KP` (UK DPR0131)
  - Suite 401, Potonggang Hotel, Ansan-Dong, Pyongchon District, Pyongyang; country North Korea → `KP` (UK DPR0131)
- **BICs**: `DCBKKPPY` (OFAC 16085)
- **GLEIF LEI**: none found

#### `bandes` (Bank)

- **Listings**
  - OFAC SDN UID `26587`: programmes `VENEZUELA-EO13850`; SDN listing date 2019-03-22
- **Primary name**: BANCO DE DESARROLLO ECONOMICO Y SOCIAL DE VENEZUELA (OFAC 26587)
- **Aliases** (weak and low-quality excluded): BANDES *(a.k.a., OFAC 26587)*; Banco Bandes *(a.k.a., OFAC 26587)*; Fondo de Inversiones de Venezuela *(f.k.a., OFAC 26587)*
- **Non-Latin names**: none on either list
- **Addresses**
  - Av. Universidad, Esq. de Traposos a Colon, P-1, Torre BANDES, CARACAS, DISTRITO FEDERAL, 1010; country Venezuela → `VE` (OFAC 26587)
  - Edificio Fondo de Inversiones de Venezuela Avenida Norte 1, Esquina Colon a Traposos, Caracas; country Venezuela → `VE` (OFAC 26587)
- **BICs**: `FIVVVECA` (OFAC 26587)
- **GLEIF LEI records**
  - `52990049IEUGB01L0409`: Banco de Desarrollo Economico y Social de Venezuela; VE; registeredAs —; entity ACTIVE, registration LAPSED (last update 2021-09-17); found via GLEIF BIC-to-LEI mapping (lei-bic-20260828T000000.csv) for FIVVVECA

### Corporates

#### `evraz-plc` (Corporate)

- **Listings**
  - UK Sanctions List `RUS1027`: The Russia (Sanctions) (EU Exit) Regulations 2019; designated 2022-05-05; last updated 2025-04-09; source UK; OFSI Group ID 15380
- **Primary name**: Evraz PLC (UK RUS1027)
- **Aliases**: none
- **Non-Latin names**: Евраз *(UK non-Latin name; script Cyrillic (inferred); language not stated; UK RUS1027)*
- **Addresses**
  - 2 Portman Street, London, W1H 6DU; country United Kingdom → `GB` (UK RUS1027)
- **Registration numbers and LEIs on the Listings**: Business registration number `07784342` (UK RUS1027)
- **UK type of entity**: Public Limited Company (PLC)
- **GLEIF LEI records**
  - `5493005B7DAN39RXLK23`: EVRAZ PLC; GB; registeredAs 07784342; entity ACTIVE, registration LAPSED (last update 2023-07-31); found via GLEIF lei-records filter[entity.registeredAs]=07784342

#### `evraz-ntmk` (Corporate)

- **Listings**
  - OFAC SDN UID `50054`: programmes `RUSSIA-EO14024`; SDN listing date 2024-08-23
- **Primary name**: AKTSIONERNOE OBSHCHESTVO EVRAZ NIZHNETAGILSKI METALLURGICHESKI KOMBINAT (OFAC 50054)
- **Aliases** (weak and low-quality excluded): Joint Stock Company Evraz Nizhny Tagil Metallurgical Plant *(a.k.a., OFAC 50054)*
- **Non-Latin names**: none on either list
- **Excluded weak aliases**: Evraz NTMK AO
- **Addresses**
  - d.1, ul. Metallurgov, Nizhni Tagil, Sverdlovsk region, 622025; country Russia → `RU` (OFAC 50054)
- **Registration numbers and LEIs on the Listings**: Registration Number `1026601367539` (Russia) (OFAC 50054); Tax ID No. `6623000680` (Russia) (OFAC 50054)
- **GLEIF LEI records**
  - `25340007CAJLLJ6YBV26`: Публичное акционерное общество "ЕВРАЗ"; RU; registeredAs 1026601367539; entity ACTIVE, registration LAPSED (last update 2026-01-16); found via GLEIF lei-records filter[entity.registeredAs]=1026601367539

#### `rosneft` (Corporate)

- **Listings**
  - OFAC SDN UID `17022`: programmes `UKRAINE-EO13662`, `RUSSIA-EO14024`; SDN listing date 2025-10-22
  - UK Sanctions List `RUS3064`: The Russia (Sanctions) (EU Exit) Regulations 2019; designated 2025-10-15; last updated 2025-10-15; source UK; OFSI Group ID 17169
- **Primary name**: Open Joint-Stock Company Rosneft Oil Company (OFAC 17022); PJSC Rosneft Oil Company (UK RUS3064)
- **Aliases** (weak and low-quality excluded): OJSC Rosneft Oil Company *(a.k.a., OFAC 17022)*; Rosneft Oil Company *(a.k.a., OFAC 17022)*; OAO Rosneft Oil Company *(a.k.a., OFAC 17022)*; Oil Company Rosneft *(a.k.a., OFAC 17022)*; Rosneft *(a.k.a., OFAC 17022)*; PJSC Oil and Gas Company Rosneft *(primary variation, UK RUS3064)*; ROSNEFT *(primary variation, UK RUS3064)*
- **Non-Latin names**: ПАО НК РОСНЕФТЬ *(UK non-Latin name; script Cyrillic; language Russian; UK RUS3064)*; Публичное акционерное общество "Нефтегазовая компания" "Роснефть" *(UK non-Latin name; script Cyrillic; language Russian; UK RUS3064)*; Роснефть *(UK non-Latin name; script Cyrillic; language Russian; UK RUS3064)*
- **Addresses**
  - 26/1 Sofiyskaya Embankment, Moscow, 115035; country Russia → `RU` (OFAC 17022)
  - 26/1, Sofiyskaya Embankment, Moscow, 115035; country Russia → `RU` (UK RUS3064)
- **Registration numbers and LEIs on the Listings**: Registration ID `1027700043502` (Russia) (OFAC 17022); Government Gazette Number `00044428` (Russia) (OFAC 17022); Tax ID No. `7706107510` (Russia) (OFAC 17022)
- **GLEIF LEI records**
  - `253400JT3MQWNDKMJE44`: публичное акционерное общество "Нефтяная компания "Роснефть"; RU; registeredAs 1027700043502; entity ACTIVE, registration ISSUED (last update 2025-10-17); found via GLEIF lei-records filter[entity.registeredAs]=1027700043502

#### `rostec` (Corporate)

- **Listings**
  - OFAC SDN UID `17260`: programmes `UKRAINE-EO13662`, `RUSSIA-EO14024`; SDN listing date 2022-06-28
  - UK Sanctions List `RUS0238`: The Russia (Sanctions) (EU Exit) Regulations 2019; designated 2022-02-24; last updated 2025-04-09; source UK; OFSI Group ID 14185
- **Primary name**: State Corporation Rostec (OFAC 17260); State Corporation for the Promotion of the Development, Manufacture and Export of High Technology Products "Rostec" (UK RUS0238)
- **Aliases** (weak and low-quality excluded): State Corporation for the Promotion of the Development, Manufacture, and Export of High Tech Products Rostec *(a.k.a., OFAC 17260)*; Rostec *(primary variation, UK RUS0238)*
- **Non-Latin names**: Государственная корпорация по содействию разработке, производству и экспорту высокотехнологичной промышленной продукции Ростех *(a.k.a.; script Cyrillic; language not stated; OFAC 17260)*; Государственная корпорация по содействию разработке, производству и экспорту высокотехнологичной промышленной продукции «Ростех» *(UK non-Latin name; script Cyrillic (inferred); language not stated; UK RUS0238)*
- **Addresses**
  - 24 Usacheva Str., Moscow, 119048; country Russia → `RU` (OFAC 17260)
  - 21 Gogolevsky Blvd., Moscow, 119991; country Russia → `RU` (OFAC 17260)
  - 24 Usacheva Street, Moscow, 119048; country Russia → `RU` (UK RUS0238)
- **Registration numbers and LEIs on the Listings**: Registration ID `1077799030847` (Russia) (OFAC 17260); Tax ID No. `7704274402` (Russia) (OFAC 17260); Government Gazette Number `94137372` (Russia) (OFAC 17260); Business registration number `1077799030847` (UK RUS0238)
- **UK type of entity**: State Corporation
- **GLEIF LEI**: none found

#### `gazprom-neft` (Corporate)

- **Listings**
  - OFAC SDN UID `17143`: programmes `UKRAINE-EO13662`, `RUSSIA-EO14024`; SDN listing date 2025-01-10
  - UK Sanctions List `RUS2383`: The Russia (Sanctions) (EU Exit) Regulations 2019; designated 2025-01-10; last updated 2025-04-09; source UK; OFSI Group ID 16736
- **Primary name**: Public Joint Stock Company Gazprom Neft (OFAC 17143); GAZPROM NEFT (UK RUS2383)
- **Aliases** (weak and low-quality excluded): Publichnoe Aktsionernoe Obshchestvo Gazprom Neft *(a.k.a., OFAC 17143)*; Gazprom Neft PJSC *(a.k.a., OFAC 17143)*; GAZPROM NEFT PAO *(a.k.a., OFAC 17143)*; Gazprom Neft Joint Stock Company *(a.k.a., OFAC 17143)*; GAZPROM NEFT PAO *(primary variation, UK RUS2383)*; PUBLIC JOINT STOCK COMPANY GAZPROM NEFT *(primary variation, UK RUS2383)*
- **Non-Latin names**: ГАЗПРОМ НЕФТЬ *(UK non-Latin name; script Cyrillic; language Russian; UK RUS2383)*
- **Addresses**
  - 5, Let. A, Galernaya, Saint Petersburg, 190000; country Russia → `RU` (OFAC 17143)
  - d. 3-5 litera A Ch. Pom. 1N kab. 2401, ul. Pochtamtskaya, St. Petersburg, 190000; country Russia → `RU` (OFAC 17143)
  - 5 Let. A. Galernaya, Saint Petersburg, 190000; country Russia → `RU` (UK RUS2383)
- **Registration numbers and LEIs on the Listings**: Registration Number `1025501701686` (Russia) (OFAC 17143); Government Gazette Number `42045241` (Russia) (OFAC 17143); Tax ID No. `5504036333` (Russia) (OFAC 17143); Business registration number `Russia TIN: 5504036333` (UK RUS2383)
- **GLEIF LEI records**
  - `253400KXA9P2AN72P004`: Публичное акционерное общество "Газпром нефть"; RU; registeredAs 1025501701686; entity ACTIVE, registration LAPSED (last update 2026-08-14); found via GLEIF lei-records filter[entity.registeredAs]=1025501701686

#### `sovcomflot` (Corporate)

- **Listings**
  - OFAC SDN UID `34741`: programmes `RUSSIA-EO14024`, `UKRAINE-EO13662`; SDN listing date 2024-02-23
  - UK Sanctions List `RUS1097`: The Russia (Sanctions) (EU Exit) Regulations 2019; designated 2022-03-24; last updated 2025-04-09; source UK; OFSI Group ID 15040
- **Primary name**: JOINT STOCK COMPANY SOVCOMFLOT (OFAC 34741); PUBLIC JOINT STOCK COMPANY SOVCOMFLOT (UK RUS1097)
- **Aliases** (weak and low-quality excluded): PAO Sovcomflot *(a.k.a., OFAC 34741)*; Publichnoe Aktsionernoe Obschestvo Sovremennyy Kommercheskiy Flot *(a.k.a., OFAC 34741)*; JSC Sovcomflot *(a.k.a., OFAC 34741)*; Public Joint Stock Company Modern Commercial Fleet *(a.k.a., OFAC 34741)*; PAO SOVCOMFLOT *(primary variation, UK RUS1097)*; PJSC SOVCOMFLOT *(primary variation, UK RUS1097)*; PUBLICHNOE AKSIONERNOE OBSCHESTVO SOVREMENNYY KOMMERCHESKIY FLOT *(primary variation, UK RUS1097)*
- **Non-Latin names**: Публичное акционерное общество Современный коммерческий флот *(UK non-Latin name; script Cyrillic; language Russian; UK RUS1097)*; ПАО СОВКОМФЛОТ *(UK non-Latin name; script Cyrillic; language Russian; UK RUS1097)*; ПУБЛИЧНОЕ АКЦИОНЕРНОЕ ОБЩЕСТВО СОВРЕМЕННЫЙ КОММЕРЧЕСКИЙ ФЛОТ *(UK non-Latin name; script Cyrillic; language Russian; UK RUS1097)*
- **Excluded weak aliases**: SCF Group; SCF
- **Addresses**
  - Ul. Gasheka D. 6, Moscow, 125047; country Russia → `RU` (OFAC 34741)
  - Nab. Reki Moiki d.3, Lit. A, Saint Petersburg, 191186; country Russia → `RU` (OFAC 34741)
  - Building 3, Letter A, Moyka River Embankment, Saint Petersburg, 191186; country Russia → `RU` (OFAC 34741)
  - 3A Moyka River Embankment, St Petersburg, 191186; country Russia → `RU` (UK RUS1097)
- **Registration numbers and LEIs on the Listings**: Tax ID No. `7702060116` (Russia) (OFAC 34741); Registration Number `1027739028712` (Russia) (OFAC 34741); Legal Entity Number `253400DYLWR5A6YAWJ69` (OFAC 34741)
- **UK type of entity**: Public Joint Stock Company
- **GLEIF LEI records**
  - `253400DYLWR5A6YAWJ69`: публичное акционерное общество "Современный коммерческий флот"; RU; registeredAs 1027739028712; entity ACTIVE, registration LAPSED (last update 2024-09-30); found via OFAC 34741 Legal Entity Number; GLEIF lei-records filter[entity.registeredAs]=1027739028712

#### `alrosa` (Corporate)

- **Listings**
  - OFAC SDN UID `34644`: programmes `RUSSIA-EO14024`; SDN listing date 2022-04-07
  - UK Sanctions List `RUS1075`: The Russia (Sanctions) (EU Exit) Regulations 2019; designated 2022-03-24; last updated 2025-04-09; source UK; OFSI Group ID 15018
- **Primary name**: PUBLIC JOINT STOCK COMPANY ALROSA (OFAC 34644); Alrosa (UK RUS1075)
- **Aliases** (weak and low-quality excluded): AK ALROSA PAO *(a.k.a., OFAC 34644)*; PJSC ALROSA *(a.k.a., OFAC 34644)*; ALROSA Group *(a.k.a., OFAC 34644)*; AK Alrosa PAO *(primary variation, UK RUS1075)*; Aktsionernaya kompaniya ALROSA PAO *(primary variation, UK RUS1075)*; ALROSA Company PJSC *(primary variation, UK RUS1075)*
- **Non-Latin names**: Акционерная Компания Алроса Публичное Акционерное Общество *(primary; script Cyrillic; language not stated; OFAC 34644)*; АК АЛРОСА ПАО *(a.k.a.; script Cyrillic; language not stated; OFAC 34644)*; Алроса *(UK non-Latin name; script Cyrillic; language not stated; UK RUS1075)*
- **Addresses**
  - 24 Ozerkovskaya Naberezhnaya, Moscow, 115184; country Russia → `RU` (OFAC 34644)
  - 6 ulitsa Lenina, Mirny, Republic of Sakha (Yakutia), 678174; country Russia → `RU` (OFAC 34644)
  - ul. Lenina, 6, Republic of Sakha (Yakutia), Mirny, 678174; country Russia → `RU` (UK RUS1075)
- **Registration numbers and LEIs on the Listings**: Registration Number `1021400967092` (Russia) (OFAC 34644); Tax ID No. `1433000147` (Russia) (OFAC 34644); Legal Entity Number `894500DKUWVBYZLLE651` (Russia) (OFAC 34644)
- **GLEIF LEI records**
  - `894500DKUWVBYZLLE651`: АКЦИОНЕРНАЯ КОМПАНИЯ "АЛРОСА" (ПУБЛИЧНОЕ АКЦИОНЕРНОЕ ОБЩЕСТВО); RU; registeredAs 1021400967092; entity ACTIVE, registration LAPSED (last update 2026-06-15); found via OFAC 34644 Legal Entity Number; GLEIF lei-records filter[entity.registeredAs]=1021400967092

#### `belaruskali` (Corporate)

- **Listings**
  - UK Sanctions List `BEL0111`: The Republic of Belarus (Sanctions) (EU Exit) Regulations 2019; designated 2021-12-02; last updated 2025-04-09; source UK; OFSI Group ID 14154
- **Primary name**: Open Joint Stock Company "Belaruskali" (UK BEL0111)
- **Aliases** (weak and low-quality excluded): Open Joint Stock Company "Belaruskali" *(primary variation, UK BEL0111)*; OJSC "Belaruskali" *(a.k.a., UK BEL0111)*
- **Non-Latin names**: Открытое акционерное общество "Беларуськалий" *(UK non-Latin name; script Cyrillic (inferred); language not stated; UK BEL0111)*; Адкрытае акцыянернае таварыства "Беларуськалiй" *(UK non-Latin name; script Cyrillic (inferred); language not stated; UK BEL0111)*; ААТ "Беларуськалiй" *(UK non-Latin name; script Cyrillic (inferred); language not stated; UK BEL0111)*; ОАО "Беларуськалий" *(UK non-Latin name; script Cyrillic (inferred); language not stated; UK BEL0111)*
- **Addresses**
  - OJSC Belaruskali, 5 Korzha Street, Soligorsk, Minsk Region, 223710; country Belarus → `BY` (UK BEL0111)
- **UK type of entity**: Open Joint Stock Company (OJSC)
- **GLEIF LEI**: none found

#### `national-iranian-oil-company` (Corporate)

- **Listings**
  - OFAC SDN UID `11317`: programmes `IRAN`, `IFCA`, `IFSR`, `SDGT`; SDN listing date 2008-11-26
  - UK Sanctions List `INU0318`: The Iran (Sanctions) (Nuclear) (EU Exit) Regulations 2019; designated 2025-09-29; last updated 2025-09-29; source UK; OFSI Group ID 12741
- **Primary name**: NATIONAL IRANIAN OIL COMPANY (OFAC 11317); NATIONAL IRANIAN OIL COMPANY (UK INU0318)
- **Aliases** (weak and low-quality excluded): NIOC *(a.k.a., OFAC 11317)*; National Iranian Oil Co *(primary variation, UK INU0318)*; NIOC *(primary variation, UK INU0318)*
- **Non-Latin names**: شرکت ملّی نفت ایران *(UK non-Latin name; script Arabic (inferred); language Persian; UK INU0318)*
- **Addresses**
  - Hafez Crossing, Taleghani Avenue, P.O. Box 1863 and 2501, Tehran; country Iran → `IR` (OFAC 11317)
  - National Iranian Oil Company Building, Taleghani Avenue, Hafez Street, Tehran; country Iran → `IR` (OFAC 11317)
  - Hafez Crossing, Taleghani Avenue, Tehran, P.O. Box 1863 and 2501; country Iran → `IR` (UK INU0318)
  - National Iranian Oil Company Building 214, Khorramshahr Avenue, Tehran, 1533743911; country Iran → `IR` (UK INU0318)
  - NIOC Central Building, Junction Of Taleghani Avenue And Hafez Avenue, Tehran, 15875-1863; country Iran → `IR` (UK INU0318)
- **Registration numbers and LEIs on the Listings**: Business registration number `1863 4976 EPTDKB2J3TX1` (UK INU0318)
- **GLEIF LEI**: none found

#### `irisl` (Corporate)

- **Listings**
  - OFAC SDN UID `25396`: programmes `IRAN`, `IFCA`, `NPWMD`, `IFSR`; SDN listing date 2018-11-05
  - UK Sanctions List `IRN0241`: The Iran (Sanctions) Regulations 2023; designated 2024-11-18; last updated 2025-04-09; source UK; OFSI Group ID 16693
- **Primary name**: Islamic Republic of Iran Shipping Lines (OFAC 25396); The Islamic Republic of Iran Shipping Lines (IRISL) (UK IRN0241)
- **Aliases** (weak and low-quality excluded): IRISL *(a.k.a., OFAC 25396)*
- **Non-Latin names**: none on either list
- **Addresses**
  - Asseman Tower, Pasdaran Street, Tehran; country Iran → `IR` (OFAC 25396)
  - P.O. Box 19395-177, Tehran; country Iran → `IR` (OFAC 25396)
  - P.O. Box 1957614114, Tehran; country Iran → `IR` (OFAC 25396)
  - No 523, Al Seman Tower Building, No 8: Narenjestan, Laveltani Street, Sayya Shirazi Square, Pasdaran Street, Tehran, 1957617114; country Iran → `IR` (OFAC 25396)
  - No 37 Aseman Tower Sayyade Shirazee Square, Pasdaran Avenue, PO Box 19395-1311, Tehran; country Iran → `IR` (OFAC 25396)
  - ; country Iran → `IR` (UK IRN0241)
- **GLEIF LEI**: none found

#### `mahan-air` (Corporate)

- **Listings**
  - OFAC SDN UID `12927`: programmes `NPWMD`, `IFSR`, `SDGT`; SDN listing date 2011-10-12
- **Primary name**: MAHAN AIR (OFAC 12927)
- **Aliases** (weak and low-quality excluded): MAHAN AIR CO. *(a.k.a., OFAC 12927)*
- **Non-Latin names**: none on either list
- **Addresses**
  - No. 21, Mahan Air Tower, Azadegan Street, Jenah Expressway, Beginning of Sheykh Fazlollah Exp. Way, First of Karaj High Way, Tehran, Tehran, 1481655761; country Iran → `IR` (OFAC 12927)
  - Mahan Air Tower, 21st Floor, Azadeghan Street, Karaj Highway, P.O. Box 14515-411, Tehran, Tehran; country Iran → `IR` (OFAC 12927)
  - Mahan Air Tower, Azadegan St., Karaj Highway, P.O. Box 411-14515, Tehran, Tehran, 1481655761; country Iran → `IR` (OFAC 12927)
- **GLEIF LEI**: none found

#### `komid` (Corporate)

- **Listings**
  - OFAC SDN UID `9345`: programmes `NPWMD`, `DPRK2`; SDN listing date 2005-06-29
  - UK Sanctions List `DPR0157`: The Democratic People's Republic of Korea (Sanctions) (EU Exit) Regulations 2019; designated 2009-04-24; last updated 2022-01-14; source UN; OFSI Group ID 10892; UN ref KPe.001
- **Primary name**: KOREA MINING DEVELOPMENT TRADING CORPORATION (OFAC 9345); KOREA MINING DEVELOPMENT TRADING CORPORATION (UK DPR0157)
- **Aliases** (weak and low-quality excluded): NORTH KOREAN MINING DEVELOPMENT TRADING CORPORATION *(a.k.a., OFAC 9345)*; CHANGGWANG SINYONG CORPORATION *(a.k.a., OFAC 9345)*; EXTERNAL TECHNOLOGY GENERAL CORPORATION *(a.k.a., OFAC 9345)*; KOREA KUMRYONG TRADING COMPANY *(a.k.a., OFAC 9345)*; DPRKN Mining Development Trading Cooperation *(a.k.a., OFAC 9345)*; Korean Mining and Industrial Development Corporation *(a.k.a., OFAC 9345)*; CHANGGWANG SINYONG CORPORATION *(a.k.a., UK DPR0157)*; DPRKN MINING DEVELOPMENT TRADING COOPERATION *(a.k.a., UK DPR0157)*; EXTERNAL TECHNOLOGY GENERAL CORPORATION *(a.k.a., UK DPR0157)*; KOMID *(a.k.a., UK DPR0157)*
- **Non-Latin names**: none on either list
- **Excluded weak aliases**: KOMID
- **Addresses**
  - Central District, Pyongyang; country Korea, North → `KP` (OFAC 9345)
  - Beijing; country China → `CN` (OFAC 9345)
  - Moscow; country Russia → `RU` (OFAC 9345)
  - Tehran; country Iran → `IR` (OFAC 9345)
  - Damascus; country Syria → `SY` (OFAC 9345)
  - Central District, Pyongyang; country North Korea → `KP` (UK DPR0157)
- **GLEIF LEI**: none found

#### `dandong-hongxiang` (Corporate)

- **Listings**
  - OFAC SDN UID `20564`: programmes `NPWMD`; SDN listing date 2016-09-26
- **Primary name**: Dandong Hongxiang Industrial Development Co Ltd (OFAC 20564)
- **Aliases**: none
- **Non-Latin names**: none on either list
- **Addresses**
  - Dandong; country China → `CN` (OFAC 20564)
- **GLEIF LEI**: none found

#### `pdvsa` (Corporate)

- **Listings**
  - OFAC SDN UID `26367`: programmes `VENEZUELA-EO13850`; SDN listing date 2019-01-28
- **Primary name**: Petroleos De Venezuela, S.A. (OFAC 26367)
- **Aliases** (weak and low-quality excluded): PDVSA *(a.k.a., OFAC 26367)*; Petroleos de Venezuela S.A *(a.k.a., OFAC 26367)*; Refineria El Palito *(a.k.a., OFAC 26367)*; PETROLEOS DE VENEZUELA S A *(a.k.a., OFAC 26367)*
- **Non-Latin names**: none on either list
- **Addresses**
  - Edificio Petroleos De Venezuela, Torre Este, Piso 9, Avenida Libertador con calle El Empalme, La Campina, Caracas, 1010; country Venezuela → `VE` (OFAC 26367)
  - Torre Este Piso 9, Edif Petroleos de Venezuela, Avenida Libertador, Urb La Campina, Caracas, Distrito Federal; country Venezuela → `VE` (OFAC 26367)
- **GLEIF LEI records**
  - `549300YWR8TN1OFD4P06`: Petróleos de Venezuela S.A.; VE; registeredAs —; entity ACTIVE, registration LAPSED (last update 2024-09-16); found via GLEIF filter[fulltext]=Petroleos de Venezuela; legal address VE

#### `cham-holding` (Corporate)

- **Listings**
  - OFAC SDN UID `12744`: programmes `PAARSSR-EO13894`; SDN listing date 2011-05-18
  - UK Sanctions List `SYR0287`: The Syria (Sanctions) (EU Exit) Regulations 2019; designated 2020-12-31; last updated 2025-05-01; source UK; OFSI Group ID 12152
- **Primary name**: CHAM HOLDING (OFAC 12744); Cham Holding (UK SYR0287)
- **Aliases** (weak and low-quality excluded): CHAM INVESTMENT GROUP *(a.k.a., OFAC 12744)*; AL SHAM COMPANY *(a.k.a., OFAC 12744)*; SHAM HOLDING COMPANY SAL *(a.k.a., OFAC 12744)*; AL-SHAM COMPANY *(a.k.a., OFAC 12744)*; Al Sham Company *(a.k.a., UK SYR0287)*; Al-Sham Company *(a.k.a., UK SYR0287)*; Cham *(a.k.a., UK SYR0287)*; Cham Investment Group *(a.k.a., UK SYR0287)*; Sham Holding *(a.k.a., UK SYR0287)*; Sham Holding Company Sal *(a.k.a., UK SYR0287)*
- **Non-Latin names**: none on either list
- **Excluded weak aliases**: SHAM HOLDING; CHAM
- **Addresses**
  - Cham Holding Building, Daraa Highway, Sahnaya Area, P.O. Box 9525, Damascus; country Syria → `SY` (OFAC 12744)
  - Cham Holding Building, Daraa Highway, Ashrafiyat Sahnaya Rif Dimashq, P.O. Box 9525; country not stated → `??` (UK SYR0287)
- **UK type of entity**: Private, Investment
- **GLEIF LEI**: none found

#### `syriatel` (Corporate)

- **Listings**
  - UK Sanctions List `SYR0336`: The Syria (Sanctions) (EU Exit) Regulations 2019; designated 2020-12-31; last updated 2025-05-01; source UK; OFSI Group ID 12153
- **Primary name**: Syriatel (UK SYR0336)
- **Aliases**: none
- **Non-Latin names**: none on either list
- **Addresses**
  - Thawra Street, Ste Building 6th Floor, BP 2900; country not stated → `??` (UK SYR0336)
- **GLEIF LEI**: none found

### Individuals

#### `roman-abramovich` (Individual)

- **Listings**
  - UK Sanctions List `RUS0270`: The Russia (Sanctions) (EU Exit) Regulations 2019; designated 2022-03-10; last updated 2025-04-09; source UK; OFSI Group ID 14212
- **Primary name**: Roman Arkadyevich ABRAMOVICH (UK RUS0270)
- **Aliases** (weak and low-quality excluded): Roman ABRAMOVICH *(primary variation, UK RUS0270)*
- **Non-Latin names**: Роман Аркадьевич АБРАМОВИЧ *(UK non-Latin name; script Cyrillic (inferred); language not stated; UK RUS0270)*
- **Date of birth**: 1966-10-24 (UK RUS0270)
- **Place of birth**: Saratov, Russia (UK RUS0270)
- **Nationalities**: Russia (UK RUS0270); Israel (UK RUS0270); Portugal (UK RUS0270)
- **Country of residence**: not listed
- **Positions (UK)**: Stakeholder in Evraz PLC and Norilsk Nickel

#### `alexander-abramov` (Individual)

- **Listings**
  - UK Sanctions List `RUS1656`: The Russia (Sanctions) (EU Exit) Regulations 2019; designated 2022-11-02; last updated 2025-04-09; source UK; OFSI Group ID 15610
- **Primary name**: Alexander Grigoryevich ABRAMOV (UK RUS1656)
- **Aliases**: none
- **Non-Latin names**: АБРАМОВ Александр Григорьевич *(UK non-Latin name; script Cyrillic; language Russian; UK RUS1656)*
- **Date of birth**: 1959-02-20 (UK RUS1656)
- **Place of birth**: not listed
- **Nationalities**: Russia (UK RUS1656)
- **Country of residence**: not listed
- **Positions (UK)**: Former Non-Executive Chairman and Director, Evraz Plc

#### `andrey-kostin` (Individual)

- **Listings**
  - OFAC SDN UID `24063`: programmes `UKRAINE-EO13661`; SDN listing date 2018-04-06
  - UK Sanctions List `RUS0267`: The Russia (Sanctions) (EU Exit) Regulations 2019; designated 2022-03-10; last updated 2025-04-09; source UK; OFSI Group ID 14217
- **Primary name**: KOSTIN Andrey Leonidovich (OFAC 24063); Andrei Leonidovich KOSTIN (UK RUS0267)
- **Aliases** (weak and low-quality excluded): Andrei KOSTIN *(primary variation, UK RUS0267)*; Andrey KOSTIN *(primary variation, UK RUS0267)*; Andrey Leonidovich KOSTIN *(primary variation, UK RUS0267)*
- **Non-Latin names**: Андрей Леонидович КОСТИН *(UK non-Latin name; script Cyrillic (inferred); language not stated; UK RUS0267)*
- **Date of birth**: 1956-09-21 (OFAC 24063); 1956-09-21 (UK RUS0267)
- **Place of birth**: Moscow, Russian Federation (OFAC 24063); Moscow, Russia (UK RUS0267)
- **Nationalities**: Russia (UK RUS0267)
- **Country of residence**: Russia (RU); country of listed address, neither list has a residence field (OFAC 24063)
- **Positions (UK)**: President of VTB Bank (PJSC); Chairman of VTB Bank (PJSC) Management Board; Chairman of the Strategy and Corporate Governance Committee; Member of the Supervisory Council of VTB Bank (PJSC)

#### `herman-gref` (Individual)

- **Listings**
  - OFAC SDN UID `34796`: programmes `RUSSIA-EO14024`; SDN listing date 2022-03-24
  - UK Sanctions List `RUS1057`: The Russia (Sanctions) (EU Exit) Regulations 2019; designated 2022-03-24; last updated 2025-04-09; source UK; OFSI Group ID 15000
- **Primary name**: Gref Herman Oskarovich (OFAC 34796); Herman Oskarovich GREF (UK RUS1057)
- **Aliases** (weak and low-quality excluded): Gref German Oskarovich *(a.k.a., OFAC 34796)*; Graf Herman *(a.k.a., OFAC 34796)*
- **Non-Latin names**: Греф Герман Оскарович *(primary; script Cyrillic; language not stated; OFAC 34796)*; Герман Оскарович Греф *(UK non-Latin name; script Cyrillic; language Russian; UK RUS1057)*
- **Date of birth**: 1964-02-08 (OFAC 34796); 1964-02-08 (UK RUS1057)
- **Place of birth**: Panfilovo, Kazakhstan (OFAC 34796)
- **Nationalities**: Russia (nationality) (OFAC 34796); Germany (UK RUS1057); Russia (UK RUS1057)
- **Country of residence**: Russia (RU); country of listed address, neither list has a residence field (OFAC 34796)
- **Positions (UK)**: Chief Executive Officer and Chairman of the Board of PJSC SberBank

#### `andrey-akimov` (Individual)

- **Listings**
  - OFAC SDN UID `24316`: programmes `UKRAINE-EO13661`, `RUSSIA-EO14024`; SDN listing date 2018-04-06
  - UK Sanctions List `RUS1122`: The Russia (Sanctions) (EU Exit) Regulations 2019; designated 2022-04-06; last updated 2025-04-09; source UK; OFSI Group ID 15071
- **Primary name**: Akimov Andrey Igorevich (OFAC 24316); Andrey Igorevich AKIMOV (UK RUS1122)
- **Aliases** (weak and low-quality excluded): Akimov Andrei Igorevich *(a.k.a., OFAC 24316)*; Andrei Igorevich AKIMOV *(primary variation, UK RUS1122)*
- **Non-Latin names**: Андрей Игоревич Акимов *(UK non-Latin name; script Cyrillic (inferred); language not stated; UK RUS1122)*
- **Date of birth**: 1953-09-22 (OFAC 24316); 1953-09-22 (UK RUS1122)
- **Place of birth**: Leningrad, Russia (OFAC 24316); Leningrad (St Petersburg), Russia (UK RUS1122)
- **Nationalities**: Russia (UK RUS1122)
- **Country of residence**: Russia (RU); country of listed address, neither list has a residence field (OFAC 24316)
- **Positions (UK)**: Chairman of the Management Board and Board member for Gazprombank; Member of the Board of Directors of Novatek; Member of the Board of Directors of Gazprom
- **Title (OFAC)**: Chairman of the Management Board of Gazprombank

#### `mikhail-fridman` (Individual)

- **Listings**
  - OFAC SDN UID `44291`: programmes `RUSSIA-EO14024`; SDN listing date 2023-08-11
  - UK Sanctions List `RUS0664`: The Russia (Sanctions) (EU Exit) Regulations 2019; designated 2022-03-15; last updated 2026-06-24; source UK; OFSI Group ID 14615
- **Primary name**: Fridman Mikhail Maratovich (OFAC 44291); Mikhail Maratovic FRIDMAN (UK RUS0664)
- **Aliases** (weak and low-quality excluded): Mikhail Maratovic FRIEDMAN *(primary variation, UK RUS0664)*
- **Non-Latin names**: Фридман Михаил Маратович *(primary; script Cyrillic; language not stated; OFAC 44291)*; Михаил Маратович ФРИДМАН *(UK non-Latin name; script Cyrillic; language Russian; UK RUS0664)*
- **Date of birth**: 1964-04-21 (OFAC 44291); 1964-04-21 (UK RUS0664)
- **Place of birth**: Lviv, Ukraine (OFAC 44291); Lviv, Ukraine (UK RUS0664)
- **Nationalities**: Russia (nationality) (OFAC 44291); Israel (nationality) (OFAC 44291); Russia (UK RUS0664); Israel (UK RUS0664)
- **Country of residence**: Russia (RU), United Kingdom (GB); country of listed address, neither list has a residence field (OFAC 44291)
- **Positions (UK)**: Former Member of the Board of Directors of Alfa-Bank Russia; Shareholder of ABH Holdings S.A; Former Chairman of the Supervisory Board of Alfa Group Consortium; Former Member of the Board of Directors of ABH Holdings S.A

#### `yuri-kovalchuk` (Individual)

- **Listings**
  - OFAC SDN UID `16680`: programmes `UKRAINE-EO13661`, `RUSSIA-EO14024`; SDN listing date 2014-03-20
  - UK Sanctions List `RUS0007`: The Russia (Sanctions) (EU Exit) Regulations 2019; designated 2020-12-31; last updated 2025-04-09; source UK; OFSI Group ID 13075
- **Primary name**: KOVALCHUK Yuri Valentinovich (OFAC 16680); Yuriy Valentinovich Kovalchuk (UK RUS0007)
- **Aliases** (weak and low-quality excluded): Kovalchuk Yuriy Valentynovych *(a.k.a., OFAC 16680)*; Kovalchuk Yury Valentinovich *(a.k.a., OFAC 16680)*; Yuri Valentinovich Kovalchuk *(primary variation, UK RUS0007)*; Yury Valentinovich Kovalchuk *(primary variation, UK RUS0007)*
- **Non-Latin names**: Ковалчук Юрий Валентинович *(primary; script Cyrillic; language not stated; OFAC 16680)*; Ковальчук Юрій Валентинович *(a.k.a.; script Cyrillic; language not stated; OFAC 16680)*; Юрий Валентинович Ковальчук *(UK non-Latin name; script Cyrillic; language not stated; UK RUS0007)*
- **Date of birth**: 1951-07-25 (OFAC 16680); 1951-07-25 (UK RUS0007)
- **Place of birth**: St. Petersburg, Russia (OFAC 16680); Leningrad (St Petersburg), Russia (UK RUS0007)
- **Nationalities**: Russia (nationality) (OFAC 16680); Russia (UK RUS0007)
- **Country of residence**: Russia (RU); country of listed address, neither list has a residence field (OFAC 16680, UK RUS0007)
- **Positions (UK)**: Major shareholder of Bank Rossiya and the National Media Group

#### `igor-sechin` (Individual)

- **Listings**
  - OFAC SDN UID `16692`: programmes `UKRAINE-EO13661`, `RUSSIA-EO14024`; SDN listing date 2014-04-28
  - UK Sanctions List `RUS0273`: The Russia (Sanctions) (EU Exit) Regulations 2019; designated 2022-03-10; last updated 2025-04-09; source UK; OFSI Group ID 14213
- **Primary name**: SECHIN Igor Ivanovich (OFAC 16692); Igor Ivanovich SECHIN (UK RUS0273)
- **Aliases** (weak and low-quality excluded): Sechin Igor *(a.k.a., OFAC 16692)*; Igor SECHIN *(primary variation, UK RUS0273)*
- **Non-Latin names**: Сечин Игорь Иванович *(primary; script Cyrillic; language not stated; OFAC 16692)*; Игорь Иванович СЕЧИН *(UK non-Latin name; script Cyrillic (inferred); language not stated; UK RUS0273)*
- **Date of birth**: 1960-09-07 (OFAC 16692); 1960-09-07 (UK RUS0273)
- **Place of birth**: St. Petersburg, Russia (OFAC 16692); Leningrad / St. Petersburg, Russia (UK RUS0273)
- **Nationalities**: Russia (nationality) (OFAC 16692); Russia (UK RUS0273)
- **Country of residence**: Russia (RU); country of listed address, neither list has a residence field (OFAC 16692)
- **Positions (UK)**: Chief Executive Officer; Chairman of the Management Board; Deputy Chairman of the Board of Directors, Rosneft

#### `sergey-chemezov` (Individual)

- **Listings**
  - OFAC SDN UID `16685`: programmes `UKRAINE-EO13661`, `RUSSIA-EO14024`; SDN listing date 2014-04-28
  - UK Sanctions List `RUS0088`: The Russia (Sanctions) (EU Exit) Regulations 2019; designated 2020-12-31; last updated 2025-04-09; source UK; OFSI Group ID 13115
- **Primary name**: CHEMEZOV Sergei (OFAC 16685); Sergey Viktorovich Chemezov (UK RUS0088)
- **Aliases** (weak and low-quality excluded): CHEMEZOV Sergey Victorovich *(a.k.a., OFAC 16685)*; Chemezov Sergey *(a.k.a., OFAC 16685)*
- **Non-Latin names**: none on either list
- **Date of birth**: 1952-08-20 (OFAC 16685); 1952-08-20 (UK RUS0088)
- **Place of birth**: Cheremkhovo, Irkutsk, Russia (OFAC 16685); Irkutsk Oblast, Russia (UK RUS0088)
- **Nationalities**: Russia (nationality) (OFAC 16685); Russia (UK RUS0088)
- **Country of residence**: Russia (RU); country of listed address, neither list has a residence field (OFAC 16685)
- **Positions (UK)**: Chair of the Rostec conglomerate

#### `rami-makhlouf` (Individual)

- **Listings**
  - OFAC SDN UID `10725`: programmes `PAARSSR-EO13894`; SDN listing date 2008-02-21
  - UK Sanctions List `SYR0204`: The Syria (Sanctions) (EU Exit) Regulations 2019; designated 2020-12-31; last updated 2025-05-01; source UK; OFSI Group ID 11913
- **Primary name**: MAKHLUF Rami (OFAC 10725); Rami Makhlouf (UK SYR0204)
- **Aliases** (weak and low-quality excluded): MAKHLOUF Rami *(a.k.a., OFAC 10725)*; MAKHLOUF Rami Bin Mohammed *(a.k.a., OFAC 10725)*; MAKHLOUF Rami Mohammad *(a.k.a., OFAC 10725)*
- **Non-Latin names**: رامي مخلوف *(UK non-Latin name; script Arabic (inferred); language not stated; UK SYR0204)*
- **Date of birth**: 1969-07-10 (OFAC 10725); 1969-07-10 (UK SYR0204)
- **Place of birth**: Syria (OFAC 10725); Damascus, Syria (UK SYR0204)
- **Nationalities**: Syria (citizenship) (OFAC 10725); Syria (nationality) (OFAC 10725)
- **Country of residence**: not listed

#### `fares-chehabi` (Individual)

- **Listings**
  - UK Sanctions List `SYR0041`: The Syria (Sanctions) (EU Exit) Regulations 2019; designated 2020-12-31; last updated 2025-05-01; source UK; OFSI Group ID 12058
- **Primary name**: Fares Chehabi (UK SYR0041)
- **Aliases** (weak and low-quality excluded): Fares Al-Chibabi *(primary variation, UK SYR0041)*; Fares Al-Shihabi *(primary variation, UK SYR0041)*; Fares Chihabi *(primary variation, UK SYR0041)*; Fares Shihabi *(primary variation, UK SYR0041)*
- **Non-Latin names**: فارس الشهابي *(UK non-Latin name; script Arabic; language Arabic; UK SYR0041)*
- **Date of birth**: 1972-09-07 (UK SYR0041)
- **Place of birth**: not listed
- **Nationalities**: Syria (UK SYR0041)
- **Country of residence**: not listed
- **Positions (UK)**: President of Aleppo Chamber of Industry; Chairman of the Federation of Chambers of Industry. Appointed in 16 December 2018; Vice-chairman of Cham Holding

#### `ahmad-derakhshandeh` (Individual)

- **Listings**
  - UK Sanctions List `INU0275`: The Iran (Sanctions) (Nuclear) (EU Exit) Regulations 2019; designated 2023-10-18; last updated 2025-10-01; source UK|UN; OFSI Group ID 16160; UN ref IRi.013
- **Primary name**: AHMAD DERAKHSHANDEH (UK INU0275)
- **Aliases**: none
- **Non-Latin names**: none on either list
- **Date of birth**: 1956-08-11 (UK INU0275)
- **Place of birth**: not listed
- **Nationalities**: Iran (UK INU0275)
- **Country of residence**: Iran (IR); country of listed address, neither list has a residence field (UK INU0275)
- **Positions (UK)**: Former Chairman and Managing Director of Bank Sepah

#### `simon-zerpa` (Individual)

- **Listings**
  - OFAC SDN UID `22746`: programmes `VENEZUELA`; SDN listing date 2017-07-26
- **Primary name**: ZERPA DELGADO Simon Alejandro (OFAC 22746); ZERPA DELGADO Simón Alejandro (OFAC 22746)
- **Aliases**: none
- **Non-Latin names**: none on either list
- **Date of birth**: 1983-08-28 (OFAC 22746)
- **Place of birth**: not listed
- **Nationalities**: not listed
- **Country of residence**: Venezuela (VE); country of listed address, neither list has a residence field (OFAC 22746)
- **Title (OFAC)**: Vice President of Finance for Petroleos de Venezuela, S.A. (PDVSA) ; President of Venezuela's Economic and Social Development Bank (BANDES); President of Venezuela's National Development Fund (FONDEN)

#### `kim-chol-sam` (Individual)

- **Listings**
  - OFAC SDN UID `16084`: programmes `NPWMD`; SDN listing date 2013-06-27
  - UK Sanctions List `DPR0226`: The Democratic People's Republic of Korea (Sanctions) (EU Exit) Regulations 2019; designated 2016-11-30; last updated 2022-08-01; source UN; OFSI Group ID 13420; UN ref KPi.035
- **Primary name**: KIM Chol Sam (OFAC 16084); KIM CHOL SAM (UK DPR0226)
- **Aliases** (weak and low-quality excluded): Jin Tiesan *(a.k.a., UK DPR0226)*
- **Non-Latin names**: (金铁三) *(UK non-Latin name; script Han (inferred); language Korean; UK DPR0226)*
- **Date of birth**: 1971-03-11 (OFAC 16084); 1971-03-11 (UK DPR0226)
- **Place of birth**: not listed
- **Nationalities**: Korea, North (nationality) (OFAC 16084); North Korea (UK DPR0226)
- **Country of residence**: not listed
- **Positions (UK)**: Representative of Daedong Credit Bank (DCB)
- **Title (OFAC)**: Treasurer, Daedong Credit Bank


## Sources

- OFAC Sanctions List Service exports: https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN_ADVANCED.XML and https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN.XML (DateOfIssue 2026-09-14)
- FCDO UK Sanctions List XML: https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.xml (DateGenerated 11/09/2026)
- GLEIF BIC-to-LEI relationship file: https://mapping.gleif.org/api/v2/bic-lei/latest/download (`LEI-BIC-20260828.zip`)
- GLEIF API, LEI records: https://api.gleif.org/api/v1/lei-records (queried 2026-09-16; golden copy publish date 2026-09-16)
- Prior research: `docs/research/sanctions-list-entry-shape.md` on branch `research/sanctions-list-entry-shape` (#3), for list formats, weak-alias semantics and licensing
- Schema and criteria: #6 resolution comment
