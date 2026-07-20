# Copyright (c) 2026, Omnexa and contributors
# License: See license.txt

"""IAS 16 (PPE) depreciation helpers — cost model, systematic allocation over useful life."""

from __future__ import annotations

from frappe.utils import flt


def depreciable_amount(cost: float, salvage: float) -> float:
	"""IAS 16.53 — Depreciable amount is cost less residual value."""
	return max(0.0, flt(cost) - flt(salvage))


def remaining_depreciable(cost: float, salvage: float, accumulated_depreciation: float) -> float:
	"""Amount still to be depreciated before reaching residual value."""
	da = depreciable_amount(cost, salvage)
	rem = flt(da) - flt(accumulated_depreciation)
	return max(0.0, rem)


def monthly_straight_line(*, cost: float, salvage: float, useful_life_months: int) -> float:
	"""IAS 16.50 — Straight-line over useful life (equal monthly charge)."""
	if not useful_life_months or useful_life_months < 1:
		return 0.0
	da = depreciable_amount(cost, salvage)
	if da <= 0:
		return 0.0
	return flt(da / useful_life_months, 2)


def monthly_declining_balance(
	*,
	carrying_amount_before: float,
	salvage: float,
	annual_rate_percent: float,
) -> float:
	"""Diminishing balance: monthly charge = carrying amount × (annual% / 12), not below residual."""
	bv = flt(carrying_amount_before)
	sv = flt(salvage)
	if bv <= sv or annual_rate_percent is None or flt(annual_rate_percent) <= 0:
		return 0.0
	rate = flt(annual_rate_percent) / 100.0 / 12.0
	charge = flt(bv * rate, 2)
	return min(charge, max(0.0, bv - sv))


def units_of_production_charge(
	*,
	cost: float,
	salvage: float,
	units_this_period: float,
	total_estimated_units: float,
) -> float:
	"""IAS 16.56 — Units of production: depreciable amount × (units / total units)."""
	if not total_estimated_units or flt(total_estimated_units) <= 0:
		return 0.0
	if not units_this_period or flt(units_this_period) <= 0:
		return 0.0
	da = depreciable_amount(cost, salvage)
	if da <= 0:
		return 0.0
	return flt(da * (flt(units_this_period) / flt(total_estimated_units)), 2)


def suggest_monthly_depreciation(
	*,
	method: str,
	cost: float,
	salvage: float,
	accumulated_depreciation: float,
	useful_life_months: int | None,
	annual_declining_rate_percent: float | None,
	total_estimated_units: int | None,
	units_this_period: float | None,
) -> float:
	"""Suggest periodic depreciation for one month (or one UoP run if units_this_period set)."""
	method = (method or "").strip()
	carrying = flt(cost) - flt(accumulated_depreciation)
	rem = remaining_depreciable(cost, salvage, accumulated_depreciation)
	if rem <= 0:
		return 0.0

	if method in ("", "None"):
		return 0.0
	if method == "Straight Line":
		ch = monthly_straight_line(
			cost=cost, salvage=salvage, useful_life_months=int(useful_life_months or 0)
		)
		return min(ch, rem)
	if method == "Declining Balance":
		ch = monthly_declining_balance(
			carrying_amount_before=carrying,
			salvage=salvage,
			annual_rate_percent=flt(annual_declining_rate_percent),
		)
		return min(ch, rem)
	if method == "Units of Production":
		u = flt(units_this_period)
		if u <= 0:
			return 0.0
		ch = units_of_production_charge(
			cost=cost,
			salvage=salvage,
			units_this_period=u,
			total_estimated_units=flt(total_estimated_units),
		)
		return min(ch, rem)
	return 0.0
