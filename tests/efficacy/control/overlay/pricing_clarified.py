"""The pricing algorithm: price(invoice, rules, jurisdiction) -> PricedInvoice."""

from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_EVEN

from .errors import PricingError
from .models import Jurisdiction, Product
from .rules import BulkRule, CouponRule, PercentageRule, TieredRule

CENT = Decimal("0.01")
ZERO = Decimal("0.00")

# The order the line rules apply in. Invoice rules apply percentage, then
# coupon, in `_apply_invoice_rules`.
LINE_RULE_KINDS = (TieredRule, BulkRule, PercentageRule)


@dataclass
class PricedLine:
    product: Product
    quantity: int
    gross: Decimal
    line_discount: Decimal
    net: Decimal
    invoice_discount: Decimal
    taxable: Decimal
    tax: Decimal
    total: Decimal
    applied: list


@dataclass
class PricedInvoice:
    currency: str
    jurisdiction: Jurisdiction
    lines: list
    subtotal: Decimal
    discount_total: Decimal
    taxable_total: Decimal
    tax_total: Decimal
    total: Decimal
    applied: list


@dataclass
class _DiscountedLine:
    """A line after its own rules, before the invoice's discount reaches it."""

    product: Product
    quantity: int
    gross: Decimal
    line_discount: Decimal
    net: Decimal
    applied: list


def _round_to_cents(amount: Decimal) -> Decimal:
    """Round half-even to two decimal places."""
    return amount.quantize(CENT, rounding=ROUND_HALF_EVEN)


def _truncate_to_cents(amount: Decimal) -> Decimal:
    """Drop everything past the second decimal place."""
    return amount.quantize(CENT, rounding=ROUND_DOWN)


def _total(amounts) -> Decimal:
    return sum(amounts, ZERO)


# One rule, applied to a running amount.

def _tiered_amount(rule: TieredRule, amount: Decimal, quantity: int) -> Decimal:
    """Every unit at the price of the highest tier the quantity reaches.

    Below the first tier the amount is unchanged.
    """
    reached_prices = [tier_price for min_quantity, tier_price in rule.tiers
                      if quantity >= min_quantity]
    if not reached_prices:
        return amount
    return reached_prices[-1] * quantity


def _bulk_amount(rule: BulkRule, amount: Decimal, quantity: int) -> Decimal:
    """Each complete group of `buy` units charged as `pay` units."""
    complete_groups, leftover_units = divmod(quantity, rule.buy)
    chargeable_units = complete_groups * rule.pay + leftover_units
    amount_per_unit = amount / quantity
    return amount_per_unit * chargeable_units


def _percentage_amount(percent: Decimal, amount: Decimal) -> Decimal:
    """The amount reduced by `percent`."""
    share_kept = Decimal(1) - percent / Decimal(100)
    return amount * share_kept


def _coupon_amount(rule: CouponRule, amount: Decimal) -> Decimal:
    """The amount reduced by the coupon's percentage, or by its fixed amount.

    A fixed amount larger than the invoice takes it to zero, never below.
    """
    if rule.percent is not None:
        return _percentage_amount(rule.percent, amount)
    return amount - min(rule.amount, amount)


def _line_rule_amount(rule, amount: Decimal, quantity: int) -> Decimal:
    if isinstance(rule, TieredRule):
        return _tiered_amount(rule, amount, quantity)
    if isinstance(rule, BulkRule):
        return _bulk_amount(rule, amount, quantity)
    return _percentage_amount(rule.percent, amount)


def _invoice_rule_amount(rule, amount: Decimal) -> Decimal:
    """What the invoice would carry after `rule`, rounded to cents."""
    if isinstance(rule, CouponRule):
        return _round_to_cents(_coupon_amount(rule, amount))
    return _round_to_cents(_percentage_amount(rule.percent, amount))


# Choosing one rule of a kind.

def _lowest(outcomes):
    """The `(amount, rule)` with the lowest amount; a tie goes to the lower
    rule_id."""
    return min(outcomes, key=lambda outcome: (outcome[0], outcome[1].rule_id))


def _line_rules_of_kind(rules, kind, sku):
    return [rule for rule in rules if isinstance(rule, kind) and rule.sku == sku]


def _invoice_percentage_rules(rules):
    return [rule for rule in rules
            if isinstance(rule, PercentageRule) and rule.sku is None]


def _carried_coupons(rules, coupon_codes):
    carried = {code.strip() for code in coupon_codes}
    return [rule for rule in rules
            if isinstance(rule, CouponRule) and rule.code.strip() in carried]


# The algorithm's steps, in the order `price` takes them.

def _refuse_bad_input(invoice, rules):
    """Raise for the inputs pricing refuses before it prices anything."""
    if not invoice.lines:
        raise PricingError("invoice has no lines")

    rule_ids = [rule.rule_id for rule in rules]
    if len(rule_ids) != len(set(rule_ids)):
        raise PricingError("two rules share a rule_id")

    known_codes = {rule.code.strip() for rule in rules
                   if isinstance(rule, CouponRule)}
    for code in invoice.coupon_codes:
        if code.strip() not in known_codes:
            raise PricingError(f"unknown coupon code {code!r}")


def _price_line(line, rules) -> _DiscountedLine:
    """Apply the line's own rules, the lowest of each kind, in kind order."""
    if line.quantity < 1:
        raise PricingError("line quantity must be at least one")

    gross = line.product.unit_price * line.quantity
    amount = gross
    applied = []
    for kind in LINE_RULE_KINDS:
        candidates = _line_rules_of_kind(rules, kind, line.product.sku)
        if not candidates:
            continue
        outcomes = [(_line_rule_amount(rule, amount, line.quantity), rule)
                    for rule in candidates]
        amount, chosen = _lowest(outcomes)
        applied.append(chosen.rule_id)

    net = _round_to_cents(amount)
    return _DiscountedLine(
        product=line.product,
        quantity=line.quantity,
        gross=gross,
        line_discount=_round_to_cents(gross) - net,
        net=net,
        applied=applied,
    )


def _apply_invoice_rules(subtotal: Decimal, invoice, rules):
    """Apply the invoice-wide percentage, then the coupon, rounding after each.

    Returns the discounted subtotal and the rule_ids that applied, in order.
    """
    amount = subtotal
    applied = []
    stages = (_invoice_percentage_rules(rules),
              _carried_coupons(rules, invoice.coupon_codes))
    for candidates in stages:
        if not candidates:
            continue
        outcomes = [(_invoice_rule_amount(rule, amount), rule)
                    for rule in candidates]
        amount, chosen = _lowest(outcomes)
        applied.append(chosen.rule_id)
    return amount, applied


def _allocate(discount_total: Decimal, subtotal: Decimal, nets: list) -> list:
    """Split the invoice's discount across the lines pro rata by net.

    Each line takes its exact share truncated to cents. The cents still owed
    go one each to the lines that lost most to the truncation, the earlier
    line first on a tie, so the shares sum to the discount exactly.
    """
    if subtotal == 0:
        return [ZERO] * len(nets)

    exact_shares = [discount_total * net / subtotal for net in nets]
    shares = [_truncate_to_cents(share) for share in exact_shares]
    lost_to_truncation = [exact - share
                          for exact, share in zip(exact_shares, shares)]
    cents_owed = int((discount_total - _total(shares)) / CENT)

    most_lost_first = sorted(range(len(nets)),
                             key=lambda index: (-lost_to_truncation[index], index))
    for index in most_lost_first[:cents_owed]:
        shares[index] += CENT
    return shares


def _tax_line(line: _DiscountedLine, invoice_discount: Decimal,
              jurisdiction: Jurisdiction) -> PricedLine:
    """Take the line's share of the invoice discount off, and tax the rest."""
    taxable = line.net - invoice_discount
    rate = jurisdiction.rates.get(line.product.tax_category,
                                  jurisdiction.default_rate)
    tax = _round_to_cents(taxable * rate)
    return PricedLine(
        product=line.product,
        quantity=line.quantity,
        gross=line.gross,
        line_discount=line.line_discount,
        net=line.net,
        invoice_discount=invoice_discount,
        taxable=taxable,
        tax=tax,
        total=taxable + tax,
        applied=line.applied,
    )


def price(invoice, rules, jurisdiction) -> PricedInvoice:
    """Price each line, discount the invoice, spread the discount, tax it."""
    _refuse_bad_input(invoice, rules)

    discounted_lines = [_price_line(line, rules) for line in invoice.lines]
    subtotal = _total(line.net for line in discounted_lines)
    discounted_subtotal, applied = _apply_invoice_rules(subtotal, invoice, rules)
    discount_total = subtotal - discounted_subtotal

    shares = _allocate(discount_total, subtotal,
                       [line.net for line in discounted_lines])
    priced_lines = [_tax_line(line, share, jurisdiction)
                    for line, share in zip(discounted_lines, shares)]
    tax_total = _total(line.tax for line in priced_lines)

    return PricedInvoice(
        currency=invoice.currency,
        jurisdiction=jurisdiction,
        lines=priced_lines,
        subtotal=subtotal,
        discount_total=discount_total,
        taxable_total=discounted_subtotal,
        tax_total=tax_total,
        total=discounted_subtotal + tax_total,
        applied=applied,
    )
