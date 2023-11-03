import datetime
import json

import pytest
import pytz

from ....tests.utils import dummy_editorjs
from ..attributes.utils import prepare_all_attributes
from ..pages.utils import create_page, create_page_type
from ..product.utils.preparing_product import prepare_product
from ..shop.utils.preparing_shop import prepare_shop
from ..utils import assign_permissions


@pytest.mark.e2e
def test_order_cancel_fulfillment_core_0220(
    e2e_staff_api_client,
    permission_manage_page_types_and_attributes,
    permission_manage_pages,
    permission_manage_products,
    permission_manage_channels,
    permission_manage_shipping,
    permission_manage_product_types_and_attributes,
    permission_manage_discounts,
):
    # Before
    permissions = [
        permission_manage_page_types_and_attributes,
        permission_manage_pages,
        permission_manage_products,
        permission_manage_channels,
        permission_manage_shipping,
        permission_manage_product_types_and_attributes,
        permission_manage_discounts,
    ]
    assign_permissions(e2e_staff_api_client, permissions)

    (
        warehouse_id,
        channel_id,
        _channel_slug,
        _shipping_method_id,
    ) = prepare_shop(e2e_staff_api_client)

    (
        product_id,
        _product_variant_id,
        _product_variant_price,
    ) = prepare_product(
        e2e_staff_api_client,
        warehouse_id,
        channel_id,
        23,
    )

    (
        attr_dropdown_id,
        attr_multiselect_id,
        attr_date_id,
        attr_date_time_id,
        attr_plain_text_id,
        attr_rich_text_id,
        attr_numeric_id,
        attr_bool_id,
        attr_swatch_id,
        attr_reference_id,
        attr_file_id,
    ) = prepare_all_attributes(e2e_staff_api_client, attribute_type="PAGE_TYPE")

    # Step 1 - Create page type with attributes
    add_attributes = [
        attr_dropdown_id,
        attr_multiselect_id,
        attr_date_id,
        attr_date_time_id,
        attr_plain_text_id,
        attr_rich_text_id,
        attr_numeric_id,
        attr_bool_id,
        attr_swatch_id,
        attr_reference_id,
        attr_file_id,
    ]
    page_type_data = create_page_type(e2e_staff_api_client, "Page Type", add_attributes)
    page_type_id = page_type_data["id"]

    # Step 2 - Create page
    expected_base_text = "Test rich attribute text"
    expected_rich_text = json.dumps(dummy_editorjs(expected_base_text))
    attributes = [
        {"id": attr_dropdown_id, "values": ["Freddy Torres"]},
        {"id": attr_multiselect_id, "values": ["security", "support"]},
        {"id": attr_date_id, "date": "2021-01-01"},
        {
            "id": attr_date_time_id,
            "dateTime": datetime.datetime(2023, 1, 1, tzinfo=pytz.utc),
        },
        {"id": attr_plain_text_id, "plainText": "test plain text"},
        {"id": attr_rich_text_id, "richText": expected_rich_text},
        {"id": attr_numeric_id, "numeric": 10},
        {"id": attr_bool_id, "boolean": True},
        {"id": attr_swatch_id, "values": ["blue"]},
        {"id": attr_reference_id, "references": [product_id]},
        # {"id": attr_file_id, "file": image, "contentFile": image_name},
    ]

    page = create_page(
        e2e_staff_api_client,
        page_type_id,
        title="test Page",
        is_published=True,
        attributes=attributes,
    )
    assert page["title"] == "test Page"
