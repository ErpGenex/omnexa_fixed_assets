# Universal Frappe Compatibility Layer

This app includes an additive compatibility layer under `compat/`.

## What It Provides

- Lazy version detection for Frappe, Bench, Python, Node, Redis, MariaDB, and Yarn.
- Lazy import helpers and API resolver maps for Frappe API changes.
- Wrapper modules for database, cache, permissions, files, scheduler, jobs, desk, reports, translation, and related namespaces.
- Static compatibility scanner with JSON report generation.
- Structured logs in `logs/compatibility/`.
- Safe hook entrypoints for install, migrate, uninstall, tests, and scheduler phases.
- Dry-run upgrade and rollback plans that deployment automation can execute explicitly.

## Non-Destructive Policy

The layer does not rename apps, modules, DocTypes, workspaces, Python packages, tables, hooks, patches, or configurations. It does not modify data and does not run service restarts automatically.

## Recommended Usage

New code should import Frappe APIs through `compat.imports`, `compat.resolver`, or the specific wrapper module. Existing business logic can continue working unchanged while compatibility risks are reported before upgrades.
