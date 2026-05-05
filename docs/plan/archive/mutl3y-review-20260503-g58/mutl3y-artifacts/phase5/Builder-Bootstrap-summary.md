Builder-Bootstrap summary for G58-C01.

- Root fix: serialized first default-registry initialization with a bootstrap lock and staged bootstrap work on a temporary registry snapshot before atomically copying state into the canonical singleton.
- Fail-closed behavior preserved: entry-point discovery or invariant-validation failures leave the canonical registry unpublished and unchanged.
- Compatibility preserved: pre-bootstrap registrations already present on the canonical registry are copied into the staged bootstrap state before built-ins and discovery run, so lazy explicit-access semantics remain intact.
- Registry support: added typed snapshot/replace helpers on PluginRegistry so bootstrap can publish a fully validated state without rebinding the canonical singleton object.
- Tests: strengthened entry-point discovery coverage to assert unpublished state on failure and atomic concurrent first initialization; validated with the required narrow bootstrap/registry gate and plugin-kernel parity file.
