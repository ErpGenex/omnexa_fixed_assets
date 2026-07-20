# Copyright (c) 2026, Omnexa and contributors
# License: MIT. See license.txt

from omnexa_core.omnexa_core.branch_access import enforce_branch_access
from omnexa_core.omnexa_core.user_context import apply_company_branch_defaults


def enforce_branch_access_for_doc(doc, method=None):
	enforce_branch_access(doc)


def populate_company_branch_from_user_context(doc, method=None):
	apply_company_branch_defaults(doc)
