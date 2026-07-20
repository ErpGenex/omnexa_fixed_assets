# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

"""Re-nest Asset Insurance under Fixed Assets and sync desk layout."""


def execute() -> None:
	from omnexa_fixed_assets.workspace_enhancer import after_migrate

	after_migrate()
