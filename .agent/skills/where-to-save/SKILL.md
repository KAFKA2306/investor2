---
name: where-to-save
description: >
  MANDATORY TRIGGER: Invoke BEFORE any file write or path decision (CSV/JSON/DB/
  logs/artifacts) and before any code change that touches filesystem paths. If a
  request includes save location, output directory, hardcoded path, or new data
  category, this skill must be used to enforce PathRegistry and D-drive storage
  rules.
---

# Path Management (Where to Save) Skill

This skill ensures that all data, logs, and artifacts are directed to their specified directories, maintaining project organization and performance.

## 🚀 When to Use
- When saving new files (e.g., CSV, JSON, SQLite).
- When retrieving or validating filesystem paths.
- When offloading large datasets to the D-drive to manage local disk space.

## 📖 Usage Instructions

### Path Retrieval
- Input: Data type (e.g., price, cache, log).
- Procedure: 
    1. NEVER construct path strings manually because slight variations in slashes or names lead to "invisible" data fragmentation across the disk.
    2. Import `paths` from `ts-agent/src/system/path_registry.ts` because the registry serves as the only source of truth for the entire filesystem layout.
    3. Retrieve the target path because centralized resolution is mandatory for cross-OS compatibility (Windows vs. WSL).
- Output: The correct absolute path, typically pointing to the D-drive.

## 🛡️ Iron Rules

1.  NO HARDCODING: Explicitly writing paths like `/mnt/d/...` is prohibited because hardcoded paths will break as soon as the project is run on a different machine or user account.
2.  PathRegistry Compliance: The `path_registry.ts` file is the SINGLE source of truth because multiple definitions of the same directory lead to data loss during system upgrades.
3.  External Storage Priority: Large datasets must be stored on the D-drive because local WSL virtual disks expand dynamically but do not shrink, leading to permanent host-side disk exhaustion.

## Best Practices
- Directory Mapping: Follow the established hierarchy: `jquants/` for raw data, `preprocessed/` for cleaned data, and `logs/` for operational traces.
- Path Audit: Regularly execute `scripts/check_hardcoded_paths.sh` to identify and rectify any hardcoded path violations.
