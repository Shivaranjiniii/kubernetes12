from ..channel.utils import create_channel
from ..products.utils import create_digital_product_type


def test_process_checkout_with_digital_product(
    staff_api_client,
    permission_manage_product_types_and_attributes,
    permission_manage_channels,
):
    channel_data = create_channel(staff_api_client, [permission_manage_channels])
    channel_id = channel_data["id"]
    assert channel_id is not None
    product_type_data = create_digital_product_type(
        staff_api_client, [permission_manage_product_types_and_attributes]
    )
    product_type_id = product_type_data["id"]
    assert product_type_id is not None
