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
A real party or bank drawn from a sanctions list (OFAC, OFSI/FCDO), such as Sberbank or Evraz PLC, deliberately placed in a Sample File.
_Avoid_: Bad actor, hit, SDN

**Entity Catalogue**:
The curated set of Sanctioned Entities shipped with the app, each traceable to its source list and list entry.
_Avoid_: Seed list, sanctions list, watchlist, blacklist

**Hit Count**:
The number of Sanctioned Entity Placements requested in a Sample File; zero yields a clean file.
_Avoid_: Hit rate, density

**Placement**:
The party role a Sanctioned Entity occupies in a transaction (debtor, creditor, ultimate debtor/creditor, debtor/creditor/intermediary agent, or remittance information).
_Avoid_: Position, slot, location

**Name Variant**:
How a Sanctioned Entity's name is rendered in a Placement: exact, alias, transliteration, or fuzzed.
_Avoid_: Mutation, spelling, obfuscation

**Answer Key**:
The record accompanying a Sample File that states each Placement of a Sanctioned Entity and its Name Variant, i.e. what the Screening Tool should flag.
_Avoid_: Manifest, ground truth, expected results

**Seed**:
The value that makes generating a Sample File reproducible: same request plus same Seed yields the identical file and Answer Key.
_Avoid_: Random state, nonce (and never for the Entity Catalogue)

**Screening Tool**:
The external sanctions payment screening system that Sample Files are fed into; the system under test, not part of this app.
_Avoid_: Scanner, filter, checker
