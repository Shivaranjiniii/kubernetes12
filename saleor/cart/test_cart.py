from __future__ import unicode_literals
from decimal import Decimal

from prices import Price
import pytest
from mock import Mock, MagicMock
from satchless.item import InsufficientStock

from .models import Cart
from .context_processors import cart_counter
from . import utils
from ..product.models import Product, ProductVariant


@pytest.fixture
def cart(db):
    return Cart.objects.create()


@pytest.fixture
def product(db):
    product = Product(name='Big Ship', price=Price(10, currency='USD'),
                      weight=Decimal(123))
    product.save()
    return product

@pytest.fixture
def product(db):
    product = Product(name='Big Ship', price=Price(10, currency='USD'),
                      weight=Decimal(123))
    product.save()
    return product

@pytest.fixture
def variant(db, monkeypatch, product):
    variant = ProductVariant(name='Big Ship', product=product)
    variant.save()
    monkeypatch.setattr('saleor.product.models.ProductVariant.check_quantity',
                        Mock())
    return variant


def test_adding_without_checking(cart, variant):
    cart.add(variant, 1000, check_quantity=False)
    assert len(cart) == 1


def test_adding_zero_quantity(cart, variant):
    cart.add(variant, 0)
    assert len(cart) == 0


def test_adding_same_variant(cart, variant):
    cart.add(variant, 1)
    cart.add(variant, 2)
    price_total = 10 * 3
    assert len(cart) == 1
    assert cart.count() == {'total_quantity': 3}
    assert cart.get_total().gross == price_total


def test_replacing_same_variant(cart, variant):
    cart.add(variant, 1, replace=True)
    cart.add(variant, 2, replace=True)
    assert len(cart) == 1
    assert cart.count() == {'total_quantity': 2}


def test_adding_invalid_quantity(cart, variant):
    with pytest.raises(ValueError):
        cart.add(variant, -1)


def test_getting_line(cart, variant):
    assert cart.get_line(variant) is None

    line = cart.create_line(variant, 1, None)
    assert line == cart.get_line(variant)


def test_change_status(cart):
    with pytest.raises(ValueError):
        cart.change_status('spanish inquisition')

    cart.change_status(Cart.OPEN)
    assert cart.status == Cart.OPEN
    cart.change_status(Cart.CANCELED)
    assert cart.status == Cart.CANCELED


def test_shipping_detection(cart, variant):
    assert not cart.is_shipping_required()
    cart.add(variant, 1, replace=True)
    assert cart.is_shipping_required()


def test_cart_counter(db, monkeypatch):
    monkeypatch.setattr('saleor.cart.context_processors.get_cart_from_request',
                        Mock(return_value=Mock(quantity=4)))
    ret = cart_counter(Mock())
    assert ret == {'cart_counter': 4}


def test_get_product_variants_and_prices():
    product = Mock(product_id=1, id=1)
    cart = MagicMock()
    cart.__iter__.return_value = [Mock(quantity=1, product=product, get_price_per_item=Mock(return_value=10))]
    products = list(utils.get_product_variants_and_prices(cart, product))
    assert products == [(product, 10)]


def test_get_user_open_cart_token():
    cart = Mock()
    carts = []
    user = Mock(carts=Mock(open=Mock(return_value=Mock(values_list=Mock(return_value=carts)))))
    assert utils.get_user_open_cart_token(user) == None

    carts.append(cart)
    user = Mock(carts=Mock(open=Mock(return_value=Mock(values_list=Mock(return_value=carts)))))
    assert utils.get_user_open_cart_token(user) == cart


def test_contains_unavailable_products():
    missing_product = Mock(check_quantity=Mock(side_effect=InsufficientStock('')))
    cart = MagicMock()
    cart.__iter__.return_value = [Mock(product=missing_product)]
    assert utils.contains_unavailable_products(cart)

    product = Mock(check_quantity=Mock())
    cart.__iter__.return_value = [Mock(product=product)]
    assert not utils.contains_unavailable_products(cart)


def test_check_product_availability_and_warn(monkeypatch, cart, variant):
    cart.add(variant, 1)
    monkeypatch.setattr('django.contrib.messages.warning',
                        Mock(warning=Mock()))
    monkeypatch.setattr('saleor.cart.utils.contains_unavailable_products',
                        Mock(return_value=False))

    utils.check_product_availability_and_warn(MagicMock(), cart)
    assert len(cart) == 1

    monkeypatch.setattr('saleor.cart.utils.contains_unavailable_products',
                        Mock(return_value=True))
    monkeypatch.setattr('saleor.cart.utils.remove_unavailable_products',
                        lambda c: c.add(variant, 0, replace=True))

    utils.check_product_availability_and_warn(MagicMock(), cart)
    assert len(cart) == 0
