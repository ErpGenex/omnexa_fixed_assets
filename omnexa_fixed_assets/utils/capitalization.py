# Copyright (c) 2026, Omnexa and contributors
# License: See license.txt

"""Journal Entry helpers for fixed asset capitalization (separate from inventory)."""

import frappe
from frappe import _
from frappe.utils import flt


def _set_journal_entry_currency_from_company(je):
	"""Fill ``currency`` / ``conversion_rate`` when present (Omnexa compliance_guard requires currency)."""
	if not je.meta.has_field("currency"):
		return
	company = je.get("company")
	if not company:
		return
	ccy = (
		frappe.db.get_value("Company", company, "default_currency")
		or frappe.db.get_value("Company", company, "currency")
		or ""
	).strip()
	if not ccy:
		frappe.throw(
			_("Company {0} has no default currency; cannot post Journal Entry.").format(company),
			title=_("Currency"),
		)
	je.currency = ccy
	if je.meta.has_field("conversion_rate"):
		je.conversion_rate = 1.0


def post_capitalization_journal_entry(
	*,
	company: str,
	branch: str | None,
	posting_date,
	debit_account: str,
	credit_account: str,
	amount: float,
	reference: str,
	remarks: str,
) -> str:
	"""Create and submit a balanced Journal Entry: Dr asset, Cr source account. Returns JE name."""
	amt = flt(amount)
	if amt <= 0:
		frappe.throw(_("Amount must be positive."), title=_("Capitalization"))

	je = frappe.new_doc("Journal Entry")
	je.company = company
	je.branch = branch
	je.posting_date = posting_date
	je.reference = reference
	je.remarks = remarks
	je.append("accounts", {"account": debit_account, "debit": amt, "credit": 0})
	je.append("accounts", {"account": credit_account, "debit": 0, "credit": amt})
	_set_journal_entry_currency_from_company(je)
	je.insert()
	je.submit()
	return je.name


def post_gl_journal(
	*,
	company: str,
	branch: str | None,
	posting_date,
	reference: str,
	remarks: str,
	lines: list[dict],
) -> str:
	"""Balanced journal with arbitrary lines: each item ``account``, ``debit``, ``credit``."""
	je = frappe.new_doc("Journal Entry")
	je.company = company
	je.branch = branch
	je.posting_date = posting_date
	je.reference = reference
	je.remarks = remarks
	for row in lines:
		je.append(
			"accounts",
			{
				"account": row["account"],
				"debit": flt(row.get("debit") or 0),
				"credit": flt(row.get("credit") or 0),
			},
		)
	_set_journal_entry_currency_from_company(je)
	je.insert()
	je.submit()
	return je.name
