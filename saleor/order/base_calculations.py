from typing import TYPE_CHECKING, Iterable

from prices import Money, TaxedMoney

from ..core.taxes import zero_money
from ..discount import DiscountValueType, OrderDiscountType
from ..discount.utils import apply_discount_to_value
from .interface import OrderTaxedPricesData

if TYPE_CHECKING:
    from .models import Order, OrderLine


def base_order_shipping(order: "Order") -> Money:
    if not order.shipping_method:
        return zero_money(order.currency)
    channel_listing = order.shipping_method.channel_listings.filter(
        channel_id=order.channel_id
    ).first()
    if not channel_listing:
        return zero_money(order.currency)
    return channel_listing.price


def _base_order_subtotal(order: "Order", lines: Iterable["OrderLine"]) -> Money:
    currency = order.currency
    subtotal = zero_money(currency)
    for line in lines:
        quantity = line.quantity
        price_with_discounts = line.base_unit_price * quantity
        subtotal += price_with_discounts
    return subtotal


def base_order_total(order: "Order", lines: Iterable["OrderLine"]) -> Money:
    currency = order.currency
    subtotal = _base_order_subtotal(order, lines)
    shipping_price = base_order_shipping(order)
    order_discounts = order.discounts.all()
    for order_discount in order_discounts:
        if order_discount.type == OrderDiscountType.VOUCHER:
            subtotal = apply_discount_to_value(
                value=order_discount.value,
                value_type=order_discount.value_type,
                currency=currency,
                price_to_discount=subtotal,
            )
        else:
            if order_discount.value_type == DiscountValueType.PERCENTAGE:
                subtotal = apply_discount_to_value(
                    value=order_discount.value,
                    value_type=order_discount.value_type,
                    currency=currency,
                    price_to_discount=subtotal,
                )
                shipping_price = apply_discount_to_value(
                    value=order_discount.value,
                    value_type=order_discount.value_type,
                    currency=currency,
                    price_to_discount=shipping_price,
                )
            else:
                temporary_undiscounted_total = subtotal + shipping_price
                temporary_total = apply_discount_to_value(
                    value=order_discount.value,
                    value_type=order_discount.value_type,
                    currency=currency,
                    price_to_discount=temporary_undiscounted_total,
                )
                total_discount = temporary_undiscounted_total - temporary_total
                subtotal_discount = (
                    subtotal / temporary_undiscounted_total
                ) * total_discount
                shipping_discount = total_discount - subtotal_discount

                subtotal -= subtotal_discount
                shipping_price -= shipping_discount

    return max(subtotal + shipping_price, zero_money(currency))


def base_order_total_without_order_discount(
    order: "Order", lines: Iterable["OrderLine"]
) -> Money:
    subtotal = _base_order_subtotal(order, lines)
    base_shipping_price = base_order_shipping(order)
    return subtotal + base_shipping_price


def base_order_line_total(order_line: "OrderLine") -> OrderTaxedPricesData:
    quantity = order_line.quantity
    price_with_discounts = (
        TaxedMoney(order_line.base_unit_price, order_line.base_unit_price) * quantity
    )
    undiscounted_price = (
        TaxedMoney(
            order_line.undiscounted_base_unit_price,
            order_line.undiscounted_base_unit_price,
        )
        * quantity
    )
    return OrderTaxedPricesData(
        undiscounted_price=undiscounted_price,
        price_with_discounts=price_with_discounts,
    )
