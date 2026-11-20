# Released skill adapter source builds

The dedicated repository owns these adapters. Use an existing approved Python
3.9 or newer interpreter; the builder uses only the standard library. It does
not install dependencies, start skill scripts, contact services or publish.
Run the following commands from the repository root with a new output directory:

```text
python -B packaging/galen-release/build-owned-skill.py packaging/skills/digital-tracker NEW_OUTPUT/digital-tracker
python -B packaging/galen-release/build-owned-skill.py packaging/skills/digital-tracker-diagnostics NEW_OUTPUT/digital-tracker-diagnostics
```

`PACKAGING.json` is the source inventory and owner contract. All declared source
files must be present with matching hashes; unknown files and source drift fail
closed. Intentional owner-reviewed changes require a corresponding manifest and
skill-version update before a new Registry submission. `SOURCE-RECOVERY.json`
records the recovered release lineage and leaves unknown original build commits
null. Released SKILL metadata remains unchanged; the manifest records the agreed
current owner. Generated archives are review outputs, not replacements for
existing releases or employee installations.

Digital Tracker and Diagnostics have no external binary inputs in these source
snapshots. Their current owner is Meenakshi; their separate source directories
keep the analytics and diagnostics workflows distinct.

The builder reads only declared text source and individually declared external
binary members. Source, manifest, archive and output paths must not traverse a
symlink, junction or Windows reparse point. An existing output is preserved.
External archive bytes are hash-checked and consumed from that verified snapshot.

Run the offline fixture checks with:

```text
python -B packaging/galen-release/test-owned-skill.py
```

Symbolic-link and actual Windows-junction tests explicitly skip if the host
cannot create the required links; the reparse-attribute fallback test runs
without that privilege. Set `OWNED_SKILL_TEST_TMPDIR` to a writable scratch
directory if the host sandbox cannot use its default temporary directory.
Junction cleanup removes only the link itself. No test uses employee credentials
or a working skill installation.
