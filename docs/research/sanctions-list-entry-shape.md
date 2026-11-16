# Sanctions list entry shape for banks and corporates

Research for issue #3. It covers what OFAC SDN and UK sanctions list entries look like for a bank (Sberbank) and a corporate (Evraz PLC): identifiers, programmes and regimes, names, aliases, non-Latin names, addresses, SWIFT/BIC codes and official download formats. The findings feed the Entity Catalogue schema and the alias and transliteration Name Variants.

Snapshot: files downloaded on 2026-09-16. OFAC `SDN.XML` shows `Publish_Date` 09/14/2026. The UK Sanctions List XML shows `DateGenerated` 11/09/2026. Entries can change after these dates.

## TL;DR

- **UK: the OFSI Consolidated List is closed.** Since 28 January 2026 the FCDO **UK Sanctions List (UKSL)** has been the only UK source. The OFSI list is frozen and kept only "for reference purposes". New UK designations get no OFSI Group ID; the UKSL **Unique ID** is the identifier to use. [gov.uk: moving to a single list](https://www.gov.uk/guidance/moving-to-a-single-list-for-uk-sanctions-designations-28-january-2026)
- **Sberbank is listed on both.**
  - OFAC SDN: UID `17018`, "PUBLIC JOINT STOCK COMPANY SBERBANK OF RUSSIA", programmes `UKRAINE-EO13662` and `RUSSIA-EO14024`, SWIFT/BIC `SABRRUMM`.
  - UKSL: Unique ID `RUS0256`, OFSI Group ID `15076`, "PJSC Sberbank (Public Joint-Stock Company Sberbank)", Russia regime.
- **Evraz PLC is on the UK list only.**
  - UKSL: Unique ID `RUS1027`, OFSI Group ID `15380`.
  - OFAC SDN (and OFAC's non-SDN Consolidated list) has **no Evraz PLC entry**. OFAC lists only several Russian Evraz subsidiaries under `RUSSIA-EO14024`, for example UID `50054` "AKTSIONERNOE OBSHCHESTVO EVRAZ NIZHNETAGILSKI METALLURGICHESKI KOMBINAT".
- **Non-Latin (Cyrillic) names.** OFAC puts these only in the *advanced* XML (`SDN_ADVANCED.XML`); the legacy `SDN.XML` and CSV have none. UKSL has a `Name non-latin script` field with script type and language.
- **SWIFT/BIC.** OFAC has a structured identifier (legacy `idType` "SWIFT/BIC"; advanced Feature "SWIFT/BIC"). UKSL has **no SWIFT field**: Sberbank's UK entry has no BIC, and BICs appear only as free text in `Other Information` for a few (mostly DPRK) banks.
- **Alias quality.**
  - OFAC marks every a.k.a./f.k.a. as `strong` or `weak`. In the advanced XML this is `LowQuality`.
  - UKSL separates `Primary Name Variation` (spelling variants) from `Alias`. Its `Alias strength` field is filled only for UN listings. Sberbank's and Evraz's UK names carry no strength.
- **Licence.**
  - UK data is © Crown copyright under the Open Government Licence v3.0, which needs an attribution statement.
  - OFAC data is a US federal government work (17 U.S.C. §105). No Treasury-specific reuse terms were found.
  - Both lists contain personal data about individuals, which OGL excludes. Excerpts of Sberbank's and Evraz's entity entries are low risk.

## 1. Official sources and download formats

### OFAC (US Treasury)

OFAC publishes through the Sanctions List Service (SLS). Static export URLs sit under `https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/<FILE>`, which redirect to a signed S3 URL. Files used here:

| File | What it is |
|---|---|
| `SDN.XML` | Legacy XML, one `sdnEntry` per listing |
| `SDN_ADVANCED.XML` | Advanced XML on the UN-sponsored Sanctions Data Model, with multiple scripts and more metadata |
| `SDN.CSV`, `ADD.CSV`, `ALT.CSV`, `SDN_COMMENTS.CSV` | Legacy relational CSV: primary, addresses, aliases, remarks overflow |
| `CONSOLIDATED.XML` (plus `CONS_ADVANCED.XML`, CSVs) | Non-SDN lists, such as the Sectoral Sanctions Identifications (SSI) list |

Sources:
- SDN list in "XML, fixed-field and delimited formats"; CSV "compatible with Excel"; `.CSV` comma-delimited and `.FF` fixed width; delta files available via SLS; UIDs link primary entries to addresses and aliases. [OFAC FAQ topic 1641](https://ofac.treasury.gov/faqs/topic/1641)
- Advanced XML files (`sdn_advanced.xml` and advanced Consolidated non-SDN files) use a UN-sponsored data model that supports "multiple languages and multiple character sets". Information in non-Latin character sets "will also have a basic Latin version". [OFAC FAQ on Advanced Sanctions List Standard](https://ofac.treasury.gov/sdn-list-data-formats-data-schemas/frequently-asked-questions-on-advanced-sanctions-list-standard)
- Namespace and schema location change for `SDN.XML`, `CONSOLIDATED.XML`, `SDN_ADVANCED.XML` and `CONS_ADVANCED.XML`. [OFAC recent action 20240507_44](https://ofac.treasury.gov/recent-actions/20240507_44)
- PIP, DEL and SDALL.ZIP formats were retired in September 2023. [OFAC recent action 20230706](https://ofac.treasury.gov/recent-actions/20230706)
- Advanced XML data model documentation. [OFAC SDN Advanced Sanctions Data Model XML (PDF)](https://ofac.treasury.gov/media/10391/download?inline=)
- The treasury.gov "SDN list data formats" page now redirects to the SLS single-page app at `https://sanctionslist.ofac.treas.gov/Home/SdnList`, which needs JavaScript. The export URLs above were fetched directly.

### UK (FCDO UK Sanctions List; OFSI Consolidated List closed)

- UKSL comes in 7 formats with static URLs: ODT, ODS, XML, HTML, TXT, CSV and PDF, at `https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.{odt,ods,xml,html,txt,csv,pdf}`. There is also an XSD (`SanctionsListSchema-4.33.3.xsd`). "The data provided in each format is identical." [The UK Sanctions List](https://www.gov.uk/government/publications/the-uk-sanctions-list), [Format guide](https://www.gov.uk/guidance/format-guide-for-the-uk-sanctions-list)
- The OFSI Consolidated List of Asset Freeze Targets "closed on Wednesday 28 January 2026 and is no longer being updated". Its files (`https://ofsistorage.blob.core.windows.net/publishlive/2022format/ConList.{csv,xml,xlsx,html,pdf,txt}`) still download but are frozen. [OFSI Consolidated List page](https://www.gov.uk/government/publications/financial-sanctions-consolidated-list-of-targets), [Consolidated list of targets (withdrawn)](https://www.gov.uk/government/publications/financial-sanctions-consolidated-list-of-targets/consolidated-list-of-targets)
- "Any systems that use 'OFSI Group ID' as an identifier now need to use the UK Sanctions List's 'Unique ID' for new DPs." Historic Group IDs stay in all UKSL formats. [Moving to a single list](https://www.gov.uk/guidance/moving-to-a-single-list-for-uk-sanctions-designations-28-january-2026)
- The separate "Russia: list of persons named in relation to financial and investment restrictions" (11 entities, Schedule 2) is **not** part of UKSL. [Moving to a single list](https://www.gov.uk/guidance/moving-to-a-single-list-for-uk-sanctions-designations-28-january-2026)

## 2. Entry shape: OFAC

### Legacy XML (`SDN.XML`)

Checked in the downloaded file:
- `sdnEntry` fields: `uid`, `lastName` (the full entity name), `sdnType` (`Entity` / `Individual` / `Vessel` / `Aircraft`), optional `remarks`, and `programList/program[]`.
- `idList/id[]` has `uid`, `idType`, `idNumber`, optional `idCountry`. `idType` is overloaded. It holds real identifiers ("Registration Number", "Tax ID No.", "SWIFT/BIC"), attributes ("Website", "Target Type", "Organization Established Date") and regulatory notes ("Secondary sanctions risk:", "Executive Order 14024 Directive Information", "Listing Date (EO 14024 Directive 2):").
- `akaList/aka[]` has `uid`, `type` (`a.k.a.` / `f.k.a.` / `n.k.a.`), `category` (`strong` / `weak`) and `lastName`.
- `addressList/address[]` has `uid`, `address1..3`, `city`, `stateOrProvince`, `postalCode`, `country`. The country is an English name, not an ISO code.
- The file contains no Cyrillic characters: legacy XML names are Latin, uppercase transliterations only.

### Legacy CSV

Field spec from the [SDN List Data Specification File](https://ofac.treasury.gov/media/29976/download?inline=):
- `SDN.CSV`: `ent_num` ("unique record identifier/unique listing identifier"), `SDN_Name`, `SDN_Type`, `Program`, `Title`, vessel fields, `Remarks` (1000 chars, "may be truncated").
- `ALT.CSV`: `ent_num`, `alt_num`, `alt_type` (aka/fka/nka), `alt_name`, `alt_remarks`.
- `ADD.CSV`: `Ent_num`, `Add_num`, `Address`, `City/State/Province/Postal Code`, `Country`, `Add_remarks`.
- The null value is `-0-`. Remarks over 1000 characters spill into `sdn_comments.csv`.

In practice:
- `ent_num` equals the XML `uid`.
- Multiple programmes are packed into one field as `"UKRAINE-EO13662] [RUSSIA-EO14024"`.
- SWIFT/BIC and registration numbers appear only inside `Remarks` text.
- **Weak aliases are not in `ALT.CSV`.** They sit in `Remarks` as `a.k.a. 'SBERBANK INDIA'`. OFAC confirms that in the CSV formats "weak AKAs are listed in the Remarks field". For Sberbank these weak aliases are past the 1000-character cut and appear only in `SDN_COMMENTS.CSV`. [OFAC FAQ 123](https://ofac.treasury.gov/faqs/123)

### Advanced XML (`SDN_ADVANCED.XML`)

Checked in the downloaded file:
- `DistinctParty FixedRef` equals the legacy UID (`17018` for Sberbank).
- `Profile PartySubTypeID` refers to a `PartyType` of Individual / Entity / Location / Transport / Other Entity.
- `Identity/Alias` has `AliasTypeID` (A.K.A., F.K.A., N.K.A., or Name for the primary), `Primary` and `LowQuality`.
- Each alias holds one or more `DocumentedName` elements. Their `NamePartValue` has a `ScriptID` (Latin 215, Cyrillic 220, Arabic 160, Chinese Simplified/Traditional, and others). So an alias can carry a Latin and a Cyrillic rendering side by side. There are 7,141 Cyrillic name parts in this file.
- `Feature` elements carry typed attributes: "SWIFT/BIC", "Website", "Target Type", "Organization Established Date", and addresses as `Location` references.
- `IDRegDocument` holds registration and tax IDs (for example type "Registration ID", with issuing country).
- `SanctionsEntry` has `ListID` (SDN List, Sectoral Sanctions Identifications List, ...), `EntryEvent` (with the legal basis and a listing date) and `SanctionsMeasure` (Program comment such as `RUSSIA-EO14024`).
- `ProfileRelationship` holds links such as subsidiaries "Linked To" Sberbank.
- Case differs from legacy: advanced aliases use mixed case ("Sberbank of Russia"), and legacy uses uppercase.

OFAC alias quality: "In the legacy XML … The Type can either be 'weak' or 'strong'… In the advanced XML list standard … 'LowQuality' … If the LowQuality attribute is true then the alias is weak." A weak AKA is "a relatively broad or generic alias that may generate a large volume of false hits". OFAC generally will not issue a civil penalty where a weak AKA is the only sanctions reference in a transaction, subject to the conditions in the FAQ. [OFAC FAQ 122](https://ofac.treasury.gov/faqs/122), [FAQ 123](https://ofac.treasury.gov/faqs/123), [Weak Aliases topic](https://ofac.treasury.gov/faqs/topic/1646)

## 3. Entry shape: UK Sanctions List

The field definitions come from the [Format guide for the UK Sanctions List](https://www.gov.uk/guidance/format-guide-for-the-uk-sanctions-list). What the downloaded XML and CSV show is noted inline.

### Identifiers and designation data

- **`Unique ID`** (for example `RUS0256`): the regime prefix plus a number. "If an entry is designated under multiple regimes, there may be different Unique IDs for one 'designated person'."
- **`OFSI Group ID`**: legacy only, and absent for persons designated after 28 Jan 2026. It appears on 5,138 of 6,340 designations in this snapshot.
- **`UN Reference Number`**.
- **`Regime Name`**: the full statutory title, for example "The Russia (Sanctions) (EU Exit) Regulations 2019".
- **`Individual, Entity, Ship`** (XML `IndividualEntityShip`).
- **`Designation source`**: `UK`, `UN` or `UK|UN`.
- **`Sanctions Imposed`**: pipe-separated. The XML adds boolean `SanctionsImposedIndicators`.
- **`Date Designated`** and **`Last Updated`**: `dd/mm/yyyy`.
- Free text: **`Other Information`** and **`UK Statement of Reasons`**.

### Names

- **`Name 6`** holds the entity's full name. `Name 1`..`5` are for individuals.
- **`Name type`** is `Primary Name`, `Primary Name Variation` ("spelling variations of the primary name") or `Alias` ("substantively different from the primary name"). The data has inconsistent case, for example `Primary name variation`, and one `ALias`.
- **`Alias strength`**: "Good quality a.k.a" / "Low quality a.k.a". It is "only included for UN listings".
- **`Name non-latin script`**, **`Non-latin script type`** (Cyrillic, Arabic, Chinese, ...) and **`Non-latin script language`** (Russian, Persian, ...).

### Contact details and addresses

- `Address Line 1..6`, `Address Postal Code`, `Address Country` (an English country name).
- `Phone number`, `Website`, `Email address`.

### Entity details

- `Type of entity`, `Subsidiaries`, `Parent company`, `Business registration number (s)`.
- **No SWIFT/BIC field.** A search of the XML found "SWIFT" only inside `OtherInformation` free text, in 21 places.

### CSV quirks

Checked in the downloaded file:
- The first row is `Report Date: …`, then the header.
- The CSV is **denormalised**: one row per combination of name × address × entity type, and so on. Sberbank `RUS0256` gives 8 rows: 4 names × 2 entity types.
- `Sanctions Imposed` values can repeat within the cell.
- Registration numbers can carry a leading `'` (Evraz shows `'07784342`).
- XML is the cleaner source: it nests `Names/Name[]`, `NonLatinNames/NonLatinName[]`, `Addresses/Address[]` and `EntityDetails/Entity/TypeOfEntities[]`.

## 4. Recorded entries

### Sberbank on OFAC SDN

Legacy `SDN.XML` fields:
- **UID / ent_num:** `17018`
- **Name:** PUBLIC JOINT STOCK COMPANY SBERBANK OF RUSSIA
- **Type:** Entity
- **Programmes:** `UKRAINE-EO13662`, `RUSSIA-EO14024`
- **Identifiers:**
  - SWIFT/BIC `SABRRUMM`
  - Registration Number `1027700132195` (Russia)
  - Tax ID No. `7707083893` (Russia)
  - Target Type "Financial Institution"
  - Websites `www.sberbank.ru`, `www.sberbank.com`
- **Other notes:** directive notes (EO 13662 Directive 1; EO 14024 Directives 2 and 3, listing date 24 Feb 2022, effective 26 Mar 2022) and secondary sanctions risk notes.

Aliases:

| Alias UID | Type | Category | Name |
|---|---|---|---|
| 26102 | a.k.a. | strong | SBERBANK ROSSII |
| 26103 | f.k.a. | strong | SBERBANK ROSSII OAO |
| 26104 | f.k.a. | strong | OTKRYTOE AKTSIONERNOE OBSHCHESTVO SBERBANK ROSSII |
| 54948 | a.k.a. | strong | SBERBANK OF RUSSIA |
| 54949 | a.k.a. | strong | PJSC SBERBANK |
| 54950 | f.k.a. | strong | OPEN JOINT STOCK COMPANY SBERBANK OF RUSSIA |
| 54951 | f.k.a. | strong | OJSC SBERBANK OF RUSSIA |
| 54952 | f.k.a. | strong | JOINT STOCK COMMERCIAL SAVINGS BANK OF THE RUSSIAN FEDERATION |
| 54953 | f.k.a. | strong | JOINT STOCK COMMERCIAL SAVINGS BANK OF THE RUSSIAN SOVIET FEDERATIVE SOCIALIST REPUBLIC |
| 54954 | f.k.a. | strong | SBERBANK OF RSFSR |
| 77192 | a.k.a. | **weak** | SBERBANK INDIA |
| 77193 | a.k.a. | **weak** | SBERBANK MUMBAI |

Addresses:

| Addr UID | Address |
|---|---|
| 52487 | 19 ul. Vavilova, Moscow 117312, Russia |
| 74652 | C305/306A Lufthansa Centre 50 Liangmaqiao Rd., Chaoyang District, Beijing 100027, China |
| 74653 | upper ground floor and fourth floor, Birla Tower, 25-Barakhamba Road, New Delhi 110001, India |
| 74654 | 81-B, 8th Floor, 5th North Avenue, Maker Maxity, Bandra Kurla Complex, Bandra East, Mumbai, Maharashtra 400051, India |

Only in `SDN_ADVANCED.XML`:
- **Cyrillic primary name:** `ПУБЛИЧНОЕ АКЦИОНЕРНОЕ ОБЩЕСТВО СБЕРБАНК РОССИИ`
- **Cyrillic form of the "PJSC Sberbank" a.k.a.:** `ПАО Сбербанк`
- **Listing:** a `SanctionsEntry` on the SDN List created 2022-04-06 under EO 13662 and EO 14024.
- **Other list entries for the same party:** Sectoral Sanctions Identifications List (2014-09-12) and Consolidated List (2014-10-10).
- **Linked parties:** many subsidiaries point to it via `ProfileRelationship`, for example UIDs 18669, 18708, 18709, 18710, 18714, 18715 and 18716. The legacy CSV shows these as "Linked To: PUBLIC JOINT STOCK COMPANY SBERBANK OF RUSSIA". Some subsidiaries carry their own BICs, for example Sberbank Europe AG `SABRATWW`, JSC Sberbank (Ukraine) `SABRUAUK` and BPS-Sberbank `BPSBBY2X`.

Sberbank (UID 17018) also appears in OFAC's non-SDN `CONSOLIDATED.XML`.

### Evraz PLC on OFAC SDN: not listed

Neither `SDN.XML` nor `CONSOLIDATED.XML` (publish date 09/14/2026) has an entry for Evraz PLC. Every "EVRAZ" hit in `SDN.XML` is a Russian subsidiary or an unrelated "Evraziya" organisation:

| UID | Primary name | Programme | Aliases (quality) | Address |
|---|---|---|---|---|
| 50051 | AKTSIONERNOE OBSHCHESTVO EVRAZ KACHKANARSKI GORNO OBOGATITELNY KOMBINAT | RUSSIA-EO14024 | JOINT STOCK COMPANY EVRAZ KACHKANARCKY ORE MINING AND PROCESSING PLANT (strong); EVRAZ KGOK AO (weak) | d. 2, ul. Sverdlova, Kachkanar, Sverdlovsk region 624351, Russia |
| 50054 | AKTSIONERNOE OBSHCHESTVO EVRAZ NIZHNETAGILSKI METALLURGICHESKI KOMBINAT | RUSSIA-EO14024 | JOINT STOCK COMPANY EVRAZ NIZHNY TAGIL METALLURGICAL PLANT (strong); EVRAZ NTMK AO (weak) | d.1, ul. Metallurgov, Nizhni Tagil, Sverdlovsk region 622025, Russia |
| 50055 | AKTSIONERNOE OBSHCHESTVO EVRAZ OBEDINENNY ZAPADNO SIBIRSKI METALLURGICHESKI KOMBINAT | RUSSIA-EO14024 | JOINT STOCK COMPANY EVRAZ CONSOLIDATED WEST SIBERIAN METALLURGICAL PLANT (strong); EVRAZ ZSMK AO (weak) | d.16, shosse Kosmicheskoe (Zavodskoi R-N), Novokuznetsk, Kemerovo region 654043, Russia |
| 50056 | AKTSIONERNOE OBSHCHESTVO EVRAZ VANADI TULA | RUSSIA-EO14024 | JOINT STOCK COMPANY EVRAZ VANADY TULA; EVRAZ VANADI TULA AO; EVRAZ VANADII TULA (all strong) | d.1, ul. Przhevalskogo, Tula 300016, Russia |
| 50125 | AO EVRAZ MARKET | RUSSIA-EO14024 | f.k.a. EVRAZ METALL INPROM OAO (strong) | Taganrog and Moscow, Russia |
| 50126 | OBSHCHESTVO S OGRANICHENNOI OTVETSTVENNOSTYU EVRAZKHOLDING FINANS | RUSSIA-EO14024 | EVRAZKHOLDING FINANS OOO; EVRAZHOLDING FINANCE (strong) | Novokuznetsk, Russia |

These subsidiaries were listed on 2024-08-23 (advanced XML `EntryEvent`). Each has a Russian Registration Number and Tax ID, and none has a Cyrillic name or SWIFT/BIC. Several match subsidiaries named in the UK statement of reasons for Evraz plc: NTMK, ZSMK and Kachkanar. **Evraz PLC can only be an OFAC-sourced Sanctioned Entity through one of these subsidiaries.**

### Sberbank on the UK Sanctions List

From `UK-Sanctions-List.xml`:
- **Unique ID:** `RUS0256`
- **OFSI Group ID:** `15076`
- **Regime:** The Russia (Sanctions) (EU Exit) Regulations 2019
- **Type / Source:** Entity / UK
- **Date Designated:** 01/03/2022
- **Last Updated:** 09/04/2025

Names:

| Name type | Name 6 |
|---|---|
| Primary Name | PJSC Sberbank (Public Joint-Stock Company Sberbank) |
| Primary Name Variation | ` PJSC Sberbank of Russia` (leading space in the source) |
| Primary Name Variation | Sberbank |
| Primary Name Variation | Sberbank of Russia |
| Non-Latin | `ПАО Сбербанк ` (trailing space in the source; the XML gives no script type or language here) |

- **Sanctions Imposed:** Asset freeze | Trust Services Sanctions | Director Disqualification Sanction | Prohibition on Correspondent banking relationships and processing payments
- **Address:** 19 Vavilova St., Moscow, 117997, Russia
- **Contact:** phone +8 (800) 555-55-50; email media@Sberbank.ru
- **Type of entity:** Bank; Financial Services Company
- **Business registration number:** 1027700132195. This matches OFAC's Registration Number, so it can be used to reconcile the two lists.
- **SWIFT/BIC:** none.
- **Statement of reasons:** "Russia's largest bank by assets… The Government of Russia has a controlling share…"

The frozen OFSI Consolidated List (`ConList.xml`) shows `GroupID` 15076, `UKSanctionsListRef` RUS0256, `AliasType` "Primary name" / "Primary name variation", `Entity_Type` "(1) Bank (2) Financial Services Company", and `DateDesignated` 2022-04-06. That date differs from UKSL's 01/03/2022. `OtherInformation` refers to the separate "List of persons named in relation to further restrictions Group ID: 13079".

### Evraz PLC on the UK Sanctions List

From `UK-Sanctions-List.xml`:
- **Unique ID:** `RUS1027`
- **OFSI Group ID:** `15380`
- **Regime:** The Russia (Sanctions) (EU Exit) Regulations 2019
- **Type / Source:** Entity / UK
- **Date Designated:** 05/05/2022
- **Last Updated:** 09/04/2025
- **Names:** Primary Name "Evraz PLC" (no variations or aliases); non-Latin `Евраз`
- **Sanctions Imposed:** Asset freeze | Trust Services Sanctions | Director Disqualification Sanction
- **Address:** 2 Portman Street, London, W1H 6DU, United Kingdom
- **Contact:** phone +74953631963; website www.evraz.com/en; email info@evraz.com
- **Type of entity:** Public Limited Company (PLC)
- **Business registration number:** 07784342 (the CSV shows `'07784342`)
- **Statement of reasons:** "UK-incorporated holding company of a multinational steel manufacturing and mining company group", owning JSC Evraz NTMK, PJSC Raspadskaya, JSC Evraz ZSMK, JSC Evraz United Coal Company Yuzhkuzbassugol and JSC Evraz Kachkanar Mining and Processing Plant.

UKSL has no separate entries for those subsidiaries: the only other name containing "Evraz" is GAC0072 "Evrazia", which is unrelated. The frozen OFSI list shows the same Group ID 15380, RUS1027 and DateDesignated 2022-05-05.

## 5. Field comparison (implications for the Entity Catalogue)

| Concept | OFAC SDN | UK Sanctions List |
|---|---|---|
| Stable entry ID | `uid` / `ent_num` / `FixedRef` (integer) | `Unique ID` (e.g. `RUS0256`); legacy `OFSI Group ID` |
| Programme / regime | `program` codes (`RUSSIA-EO14024`) | `Regime Name` (full statutory title) |
| Entity type | `sdnType` = Entity; advanced adds `Target Type` feature (e.g. Financial Institution) | `Individual, Entity, Ship` = Entity; `Type of entity` free text (Bank, PLC) |
| Primary name | `lastName` (uppercase Latin) | `Name 6` + `Name type` = Primary Name |
| Spelling variants | not distinguished from a.k.a. | `Primary Name Variation` |
| Aliases | `aka` with type a.k.a./f.k.a./n.k.a. and quality strong/weak | `Alias`; strength only for UN listings |
| Former names | `f.k.a.` | not distinguished |
| Non-Latin names | advanced XML only (`ScriptID`), attached to a specific alias | `Name non-latin script` + script type + language, not tied to a specific Latin name |
| Addresses | structured (address1-3, city, state, postcode, country) | Address Line 1-6, postcode, country |
| Country | English country name (advanced also has ISO-2 via `AreaCode`) | English country name |
| SWIFT/BIC | structured `SWIFT/BIC` id / feature | none (free text in `Other Information` for a few) |
| Registration / tax IDs | structured `idType` | `Business registration number (s)` free text |
| Links to parents/subsidiaries | "Linked To" remarks / `ProfileRelationship` | `Subsidiaries` / `Parent company` free text |

Suggested catalogue fields:
- `source_list` (`OFAC_SDN` | `UK_SL`), `source_entry_id` (OFAC UID or UK Unique ID), and optionally `legacy_ofsi_group_id`.
- `programmes[]`, `entity_kind` (bank/corporate), `primary_name`.
- `names[]` with `{kind: primary_variation | aka | fka | nka, quality: strong | weak | null, script}`.
- `non_latin_names[]`, `addresses[]` with country, `bic`, `registration_numbers[]`, and `list_snapshot_date`.

Name Variants for these entities:
- The "alias" variant can use OFAC a.k.a./f.k.a. and UK Primary Name Variations.
- The "transliteration" variant can use the published Cyrillic forms (`ПАО Сбербанк`, `ПУБЛИЧНОЕ АКЦИОНЕРНОЕ ОБЩЕСТВО СБЕРБАНК РОССИИ`, `Евраз`) and the OFAC Latin transliterations ("Sberbank Rossii", "Otkrytoe Aktsionernoe Obshchestvo Sberbank Rossii").

## 6. Licence and terms for excerpts in a repo

- **UK:** GOV.UK content is "subject to Crown copyright protection and is published under the Open Government Licence (OGL)". [GOV.UK terms](https://www.gov.uk/help/terms-conditions) The UK Sanctions List page footer reads "All content is available under the Open Government Licence v3.0, except where otherwise stated". [UK Sanctions List](https://www.gov.uk/government/publications/the-uk-sanctions-list)
  - OGL v3 lets you "copy, publish, distribute and transmit", adapt, and use the information commercially.
  - You must include the provider's attribution statement, or by default: "Contains public sector information licensed under the Open Government Licence v3.0."
  - It does **not** cover "personal data in the Information" or "third party rights". [OGL v3](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/)
  - Company entries (Sberbank, Evraz PLC) are not personal data. Individual designations would be.
- **US:** a US government work "is something created by a U.S. government officer or employee as part of their official duties" and has no US copyright protection (17 U.S.C. §§101, 105). Content on federal sites may still include protected third-party material. Use must not imply agency endorsement, and agency logos cannot be used without permission. [USAGov: government copyright](https://www.usa.gov/government-copyright)
  - No Treasury- or OFAC-specific reuse or attribution terms were found. The [Treasury Site Policies and Notices](https://home.treasury.gov/subfooter/site-policies-and-notices) page has no copyright statement.
  - Recommendation: cite the source file and publish date for each OFAC excerpt.

## Sources

- https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN.XML (and `SDN_ADVANCED.XML`, `SDN.CSV`, `ALT.CSV`, `ADD.CSV`, `SDN_COMMENTS.CSV`, `CONSOLIDATED.XML`)
- https://ofac.treasury.gov/faqs/topic/1641
- https://ofac.treasury.gov/faqs/122
- https://ofac.treasury.gov/faqs/123
- https://ofac.treasury.gov/faqs/topic/1646
- https://ofac.treasury.gov/media/29976/download?inline= (SDN List Data Specification)
- https://ofac.treasury.gov/media/10391/download?inline= (Advanced Sanctions Data Model)
- https://ofac.treasury.gov/sdn-list-data-formats-data-schemas/frequently-asked-questions-on-advanced-sanctions-list-standard
- https://ofac.treasury.gov/recent-actions/20240507_44
- https://ofac.treasury.gov/recent-actions/20230706
- https://www.gov.uk/government/publications/the-uk-sanctions-list
- https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.xml and `.csv`
- https://www.gov.uk/guidance/format-guide-for-the-uk-sanctions-list
- https://www.gov.uk/guidance/moving-to-a-single-list-for-uk-sanctions-designations-28-january-2026
- https://www.gov.uk/government/publications/financial-sanctions-consolidated-list-of-targets
- https://www.gov.uk/government/publications/financial-sanctions-consolidated-list-of-targets/consolidated-list-of-targets
- https://ofsistorage.blob.core.windows.net/publishlive/2022format/ConList.xml (frozen)
- https://www.gov.uk/help/terms-conditions
- https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/
- https://www.usa.gov/government-copyright
- https://home.treasury.gov/subfooter/site-policies-and-notices
