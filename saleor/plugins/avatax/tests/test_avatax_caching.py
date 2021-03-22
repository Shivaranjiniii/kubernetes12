from decimal import Decimal
from unittest.mock import Mock, patch

from django.test import override_settings
from prices import Money, TaxedMoney

from ....checkout.fetch import fetch_checkout_lines
from ...manager import get_plugins_manager
from .. import CACHE_KEY, generate_request_data_from_checkout
from ..plugin import AvataxPlugin


@override_settings(PLUGINS=["saleor.plugins.avatax.plugin.AvataxPlugin"])
@patch("saleor.plugins.avatax.cache.set")
def test_calculate_checkout_total_use_cache(
    mock_cache_set,
    checkout_with_items_and_shipping,
    checkout_with_items_and_shipping_info,
    address,
    site_settings,
    plugin_configuration,
    avalara_response_for_checkout_with_items_and_shipping,
    monkeypatch,
):
    # given
    checkout = checkout_with_items_and_shipping
    checkout_info = checkout_with_items_and_shipping_info
    plugin_configuration()
    manager = get_plugins_manager()
    plugin = manager.get_plugin(AvataxPlugin.PLUGIN_ID)
    site_settings.company_address = address
    site_settings.save()
    lines = fetch_checkout_lines(checkout)
    avalara_request_data = generate_request_data_from_checkout(
        checkout_info, lines, plugin.config, []
    )
    mocked_cache = Mock(
        return_value=(
            avalara_request_data,
            avalara_response_for_checkout_with_items_and_shipping,
        )
    )
    monkeypatch.setattr("saleor.plugins.avatax.cache.get", mocked_cache)

    # then
    result = manager.calculate_checkout_total(
        checkout_info, lines, checkout_info.shipping_address, []
    )

    # when
    assert result == TaxedMoney(net=Money("72.2", "USD"), gross=Money("75", "USD"))

    avalara_cache_key = CACHE_KEY + str(checkout.token)
    mocked_cache.assert_called_with(avalara_cache_key)
    mock_cache_set.assert_not_called()


@override_settings(PLUGINS=["saleor.plugins.avatax.plugin.AvataxPlugin"])
@patch("saleor.plugins.avatax.cache.set")
def test_calculate_checkout_subtotal_use_cache(
    mock_cache_set,
    checkout_with_items_and_shipping,
    checkout_with_items_and_shipping_info,
    address,
    site_settings,
    plugin_configuration,
    avalara_response_for_checkout_with_items_and_shipping,
    monkeypatch,
):
    # given
    checkout = checkout_with_items_and_shipping
    checkout_info = checkout_with_items_and_shipping_info
    plugin_configuration()
    manager = get_plugins_manager()
    plugin = manager.get_plugin(AvataxPlugin.PLUGIN_ID)
    site_settings.company_address = address
    site_settings.save()
    lines = fetch_checkout_lines(checkout)
    avalara_request_data = generate_request_data_from_checkout(
        checkout_info, lines, plugin.config, []
    )
    mocked_cache = Mock(
        return_value=(
            avalara_request_data,
            avalara_response_for_checkout_with_items_and_shipping,
        )
    )
    monkeypatch.setattr("saleor.plugins.avatax.cache.get", mocked_cache)

    # then
    result = manager.calculate_checkout_subtotal(
        checkout_info, lines, checkout_info.shipping_address, []
    )

    # when
    assert result == TaxedMoney(net=Money("64.07", "USD"), gross=Money("65", "USD"))

    avalara_cache_key = CACHE_KEY + str(checkout.token)
    mocked_cache.assert_called_with(avalara_cache_key)
    mock_cache_set.assert_not_called()


@override_settings(PLUGINS=["saleor.plugins.avatax.plugin.AvataxPlugin"])
@patch("saleor.plugins.avatax.cache.set")
def test_calculate_checkout_shipping_use_cache(
    mock_cache_set,
    checkout_with_items_and_shipping,
    checkout_with_items_and_shipping_info,
    address,
    site_settings,
    plugin_configuration,
    avalara_response_for_checkout_with_items_and_shipping,
    monkeypatch,
):
    # given
    checkout = checkout_with_items_and_shipping
    checkout_info = checkout_with_items_and_shipping_info
    plugin_configuration()
    manager = get_plugins_manager()
    plugin = manager.get_plugin(AvataxPlugin.PLUGIN_ID)
    site_settings.company_address = address
    site_settings.save()
    lines = fetch_checkout_lines(checkout)
    avalara_request_data = generate_request_data_from_checkout(
        checkout_info, lines, plugin.config, []
    )
    mocked_cache = Mock(
        return_value=(
            avalara_request_data,
            avalara_response_for_checkout_with_items_and_shipping,
        )
    )
    monkeypatch.setattr("saleor.plugins.avatax.cache.get", mocked_cache)

    # then
    result = manager.calculate_checkout_shipping(
        checkout_info, lines, checkout_info.shipping_address, []
    )

    # when
    assert result == TaxedMoney(net=Money("8.13", "USD"), gross=Money("10", "USD"))

    avalara_cache_key = CACHE_KEY + str(checkout.token)
    mocked_cache.assert_called_with(avalara_cache_key)
    mock_cache_set.assert_not_called()


@override_settings(PLUGINS=["saleor.plugins.avatax.plugin.AvataxPlugin"])
@patch("saleor.plugins.avatax.cache.set")
def test_calculate_checkout_line_total_use_cache(
    mock_cache_set,
    checkout_with_items_and_shipping,
    checkout_with_items_and_shipping_info,
    address,
    site_settings,
    plugin_configuration,
    avalara_response_for_checkout_with_items_and_shipping,
    monkeypatch,
):
    # given
    checkout = checkout_with_items_and_shipping
    checkout_info = checkout_with_items_and_shipping_info
    plugin_configuration()
    manager = get_plugins_manager()
    plugin = manager.get_plugin(AvataxPlugin.PLUGIN_ID)
    site_settings.company_address = address
    site_settings.save()
    lines = fetch_checkout_lines(checkout)
    checkout_line_info = lines[0]
    avalara_request_data = generate_request_data_from_checkout(
        checkout_info, lines, plugin.config, []
    )
    mocked_cache = Mock(
        return_value=(
            avalara_request_data,
            avalara_response_for_checkout_with_items_and_shipping,
        )
    )
    monkeypatch.setattr("saleor.plugins.avatax.cache.get", mocked_cache)

    # then
    result = manager.calculate_checkout_line_total(
        checkout_info, lines, checkout_line_info, checkout_info.shipping_address, []
    )

    # when
    assert result == TaxedMoney(net=Money("4.07", "USD"), gross=Money("5", "USD"))

    avalara_cache_key = CACHE_KEY + str(checkout.token)
    mocked_cache.assert_called_with(avalara_cache_key)
    mock_cache_set.assert_not_called()


@override_settings(PLUGINS=["saleor.plugins.avatax.plugin.AvataxPlugin"])
@patch("saleor.plugins.avatax.cache.set")
def test_calculate_checkout_line_unit_price_use_cache(
    mock_cache_set,
    checkout_with_items_and_shipping,
    checkout_with_items_and_shipping_info,
    address,
    site_settings,
    plugin_configuration,
    avalara_response_for_checkout_with_items_and_shipping,
    monkeypatch,
):
    # given
    checkout = checkout_with_items_and_shipping
    checkout_info = checkout_with_items_and_shipping_info
    plugin_configuration()
    manager = get_plugins_manager()
    plugin = manager.get_plugin(AvataxPlugin.PLUGIN_ID)
    site_settings.company_address = address
    site_settings.save()
    lines = fetch_checkout_lines(checkout)
    checkout_line_info = lines[0]
    avalara_request_data = generate_request_data_from_checkout(
        checkout_info, lines, plugin.config, []
    )
    mocked_cache = Mock(
        return_value=(
            avalara_request_data,
            avalara_response_for_checkout_with_items_and_shipping,
        )
    )
    monkeypatch.setattr("saleor.plugins.avatax.cache.get", mocked_cache)
    quantity = checkout_line_info.line.quantity
    total_line_price = checkout_line_info.channel_listing.price * quantity

    # then
    result = manager.calculate_checkout_line_unit_price(
        total_line_price,
        quantity,
        checkout_info,
        lines,
        checkout_line_info,
        checkout_info.shipping_address,
        [],
    )

    # when
    assert result == TaxedMoney(net=Money("4.07", "USD"), gross=Money("5", "USD"))

    avalara_cache_key = CACHE_KEY + str(checkout.token)
    mocked_cache.assert_called_with(avalara_cache_key)
    mock_cache_set.assert_not_called()


@override_settings(PLUGINS=["saleor.plugins.avatax.plugin.AvataxPlugin"])
@patch("saleor.plugins.avatax.cache.set")
def test_get_checkout_line_tax_rate_use_cache(
    mock_cache_set,
    checkout_with_items_and_shipping,
    checkout_with_items_and_shipping_info,
    address,
    site_settings,
    plugin_configuration,
    avalara_response_for_checkout_with_items_and_shipping,
    monkeypatch,
):
    # given
    checkout = checkout_with_items_and_shipping
    checkout_info = checkout_with_items_and_shipping_info
    plugin_configuration()
    manager = get_plugins_manager()
    plugin = manager.get_plugin(AvataxPlugin.PLUGIN_ID)
    site_settings.company_address = address
    site_settings.save()
    lines = fetch_checkout_lines(checkout)
    checkout_line_info = lines[0]
    avalara_request_data = generate_request_data_from_checkout(
        checkout_info, lines, plugin.config, []
    )
    mocked_cache = Mock(
        return_value=(
            avalara_request_data,
            avalara_response_for_checkout_with_items_and_shipping,
        )
    )
    monkeypatch.setattr("saleor.plugins.avatax.cache.get", mocked_cache)
    fake_unit_price = TaxedMoney(net=Money("2", "USD"), gross=Money("10", "USD"))

    # then
    result = manager.get_checkout_line_tax_rate(
        checkout_info,
        lines,
        checkout_line_info,
        checkout_info.shipping_address,
        [],
        fake_unit_price,
    )

    # when
    assert result == Decimal("0.23")

    avalara_cache_key = CACHE_KEY + str(checkout.token)
    mocked_cache.assert_called_with(avalara_cache_key)
    mock_cache_set.assert_not_called()


@override_settings(PLUGINS=["saleor.plugins.avatax.plugin.AvataxPlugin"])
@patch("saleor.plugins.avatax.cache.set")
def test_get_checkout_shipping_tax_rate_use_cache(
    mock_cache_set,
    checkout_with_items_and_shipping,
    checkout_with_items_and_shipping_info,
    address,
    site_settings,
    plugin_configuration,
    avalara_response_for_checkout_with_items_and_shipping,
    monkeypatch,
):
    # given
    checkout = checkout_with_items_and_shipping
    checkout_info = checkout_with_items_and_shipping_info
    plugin_configuration()
    manager = get_plugins_manager()
    plugin = manager.get_plugin(AvataxPlugin.PLUGIN_ID)
    site_settings.company_address = address
    site_settings.save()
    lines = fetch_checkout_lines(checkout)
    avalara_request_data = generate_request_data_from_checkout(
        checkout_info, lines, plugin.config, []
    )
    mocked_cache = Mock(
        return_value=(
            avalara_request_data,
            avalara_response_for_checkout_with_items_and_shipping,
        )
    )
    monkeypatch.setattr("saleor.plugins.avatax.cache.get", mocked_cache)
    fake_shipping_price = TaxedMoney(net=Money("2", "USD"), gross=Money("10", "USD"))

    # then
    result = manager.get_checkout_shipping_tax_rate(
        checkout_info, lines, checkout_info.shipping_address, [], fake_shipping_price
    )

    # when
    assert result == Decimal("0.23")

    avalara_cache_key = CACHE_KEY + str(checkout.token)
    mocked_cache.assert_called_with(avalara_cache_key)
    mock_cache_set.assert_not_called()
