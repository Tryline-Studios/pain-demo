# corpus.build over pain001's flat template pipeline

pain001's headline generation path (`generate_xml_string` with the bundled per-version `template.xml`) cannot emit Intermediary Agents in any Message Version and emits only Debtor and Creditor names in pain.001.001.04 to .08. Supporting every Placement that way would mean maintaining eleven custom templates plus our own row preparer. pain001 0.0.67+ also ships `pain001.corpus.build(scenario, version)`, a version-aware dict-to-XML builder that emits every party and agent role in every version .03 to .13, renames `BIC`/`BICFI` per version, is deterministic and validates its output against the bundled XSD. It describes itself as a maintainer tool and needs the `fast` extra (lxml).

We build every Sample File with `corpus.build`, called from a single renderer module that maps our own resolved Sample File model to its scenario dict. The flat pipeline is not used, and writing our own builder was rejected as re-implementing what corpus.build already does.

## Consequences

- The dependency is `pain001[fast]` pinned to an exact version. Golden Sample Files (one fixed Seed in every Message Version) are byte-compared in CI, and the pin is bumped only through a `just` recipe that regenerates the goldens for review.
- Only the renderer imports pain001. The request model, Placement logic and Answer Key never see its types or scenario schema, so a change in corpus.build's shape is contained to one module (where our own builder could be substituted).
- A Sample File has one `PmtInf`: Debtor and Debtor Agent are file-level Placements, everything else is per transaction.
- ISO rules the XSD cannot express (Ultimate Debtor at one level only, Intermediary Agents contiguous from 1) are made unrepresentable in our model rather than checked after the fact; pain001's `evaluate_mdr` runs only in tests.
- XSD validation runs on every request. A dropped element that carried a Placement fails the request; other drops are returned as warnings.
- Identifiers come from our seeded RNG and are passed explicitly, so the engine adds no randomness and the Seed contract stays in our code. The `raw` element-merge escape hatch is not used.
