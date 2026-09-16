# pain.001 Sample Generator

Generates sample ISO 20022 pain.001 payment initiation files used to test and prove a sanctions payment screening tool.

## Language

**Sample File**:
A pain.001 XML document produced by this app for testing, never for real payment submission.
_Avoid_: Payment file, test file, output

**Message Version**:
The specific pain.001 schema revision a Sample File conforms to (e.g. pain.001.001.03, the default).
_Avoid_: Format, variant, schema

**Generated Data**:
Payment content fabricated by the app (fake names, accounts, amounts) rather than supplied by a user.
_Avoid_: Random data, mock data, dummy data

**Supplied Data**:
Payment content provided by a user through the web form or API.
_Avoid_: Custom data, manual data, input data

**Sanctioned Entity**:
A real Entity with at least one Listing, such as Sberbank or Evraz PLC, deliberately placed in a Sample File.
_Avoid_: Bad actor, hit, SDN

**Entity**:
Any party that can be sanctioned. Every Entity has an Entity Type.
_Avoid_: Party (reserved for pain.001 roles), person, target

**Entity Type**:
The classification of an Entity: an Individual, or a Legal Entity that is either a Bank or a Corporate.
_Avoid_: Entity kind, category

**Individual**:
An Entity that is a natural person, such as an ultimate beneficial owner or controlling party of a Legal Entity.
_Avoid_: Person, natural person, UBO (a relationship, not a type)

**Legal Entity**:
An Entity that is not a natural person; for now either a Bank or a Corporate.
_Avoid_: Organisation, company, firm

**Bank**:
A Legal Entity that is a financial institution able to hold accounts and act as a payment agent.
_Avoid_: Financial institution, FI

**Corporate**:
A Legal Entity that is not a Bank.
_Avoid_: Company, business, non-bank

**Sanctions List**:
An official published list of sanctioned parties; in scope are the OFAC SDN List and the UK Sanctions List.
_Avoid_: Watchlist, blacklist, OFSI list (closed January 2026)

**Listing**:
One Entity's entry on one Sanctions List, identified by that list and its entry ID (OFAC UID or UK Unique ID).
_Avoid_: Designation, record, SDN entry

**Control Relationship**:
A sourced link stating that one Entity controls or acts for a Legal Entity (as ultimate beneficial owner, controlling shareholder, director, officer or parent company), currently, formerly, or as stated in a Listing.
_Avoid_: Ownership, affiliation, link, UBO relationship

**Entity Catalogue**:
The curated set of Sanctioned Entities shipped with the app, each traceable through its Listings, plus the Control Relationships between them.
_Avoid_: Seed list, sanctions list, watchlist, blacklist

**Hit**:
One Placement of a Sanctioned Entity in a Sample File, either file-level (Debtor, Debtor Agent) or in one transaction. A Hit is either drawn by the app or named in the request.
_Avoid_: Match, alert (those belong to the Screening Tool), injection

**Hit Count**:
The number of Hits requested in a Sample File, named ones included; zero yields a clean file.
_Avoid_: Hit rate, density

**Placement**:
The party role a Sanctioned Entity occupies in a transaction (debtor, creditor, ultimate debtor/creditor, debtor/creditor/intermediary agent, or remittance information).
_Avoid_: Position, slot, location

**Name Variant**:
How a Sanctioned Entity's name is rendered in a Placement: exact (a listed primary name), alias (a listed non-primary name), Native Script, Transliteration, or fuzzed (a listed Latin name altered by named operations).
_Avoid_: Mutation, spelling, obfuscation

**Native Script**:
The Name Variant that uses a listed non-Latin name of a Sanctioned Entity verbatim, such as its Cyrillic name.
_Avoid_: Original script, local name, foreign name

**Transliteration**:
The Name Variant that romanises a listed non-Latin name under a named scheme, producing a Latin string that is itself on no Sanctions List.
_Avoid_: Romanisation (the act, not the variant), translation

**Answer Key**:
The record accompanying a Sample File that states each Placement of a Sanctioned Entity and its Name Variant, i.e. what the Screening Tool should flag.
_Avoid_: Manifest, ground truth, expected results

**Effective Request**:
A request with every default resolved (Seed, timestamps, counts, countries) as echoed back with its Sample File; replaying it on the same Generator Version reproduces the file exactly.
_Avoid_: Resolved request, normalised request, echo

**Seed**:
The value that makes generating a Sample File reproducible: same request plus same Seed yields the identical file and Answer Key within one Generator Version.
_Avoid_: Random state, nonce (and never for the Entity Catalogue)

**Generator Version**:
The identity of everything that shapes generated output: the app release, the exact versions of its data libraries, and the Entity Catalogue snapshot. The Seed promise holds only within one.
_Avoid_: Build, engine version, fingerprint

**Screening Tool**:
The external sanctions payment screening system that Sample Files are fed into; the system under test, not part of this app.
_Avoid_: Scanner, filter, checker
