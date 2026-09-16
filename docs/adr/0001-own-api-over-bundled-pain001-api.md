# Own REST API instead of pain001's bundled API

pain001 ships an optional FastAPI app (`pain001[api]`), but its `/generate` endpoints take and return server file paths, only its UI endpoint returns XML inline, and it knows nothing about Sanctioned Entities, Placements or Answer Keys. We expose our own versioned `/api/v1` as the sole public contract (used by both the React frontend and CI/scripts) and call pain001's in-memory functions (`pain001.corpus.build`, see ADR-0002) as a pinned internal dependency; the bundled API is not mounted.

## Consequences

- pain001 is pinned to an exact version (it is pre-1.0 and releases several times a day); upgrades are deliberate.
- Library request/response models never leak into our OpenAPI schema, so a library change cannot silently break API clients.
