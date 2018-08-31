import json
from unittest.mock import MagicMock, Mock

import graphene
import pytest
from django.shortcuts import reverse
from tests.utils import get_graphql_content

from saleor.account.models import Address
from saleor.graphql.order.mutations.draft_orders import (
    check_for_draft_order_errors)
from saleor.graphql.order.mutations.orders import (
    clean_refund_payment, clean_release_payment)
from saleor.order import CustomPaymentChoices
from saleor.order.models import Order, OrderStatus, Payment, PaymentStatus
from .utils import assert_read_only_mode


def test_order_query(admin_api_client, fulfilled_order):
    order = fulfilled_order
    query = """
    query OrdersQuery {
        orders(first: 1) {
            edges {
                node {
                    number
                    status
                    statusDisplay
                    paymentStatus
                    paymentStatusDisplay
                    userEmail
                    isPaid
                    shippingPrice {
                        gross {
                            amount
                        }
                    }
                    lines {
                        totalCount
                    }
                    notes {
                        totalCount
                    }
                    fulfillments {
                        fulfillmentOrder
                    }
                    history {
                        totalCount
                    }
                    total {
                        net {
                            amount
                        }
                    }
                }
            }
        }
    }
    """
    response = admin_api_client.post(
        reverse('api'), {'query': query})
    content = get_graphql_content(response)
    assert 'errors' not in content
    order_data = content['data']['orders']['edges'][0]['node']
    assert order_data['number'] == str(order.pk)
    assert order_data['status'] == order.status.upper()
    assert order_data['statusDisplay'] == order.get_status_display()
    assert order_data['paymentStatus'] == order.get_last_payment_status()
    payment_status_display = order.get_last_payment_status_display()
    assert order_data['paymentStatusDisplay'] == payment_status_display
    assert order_data['isPaid'] == order.is_fully_paid()
    assert order_data['userEmail'] == order.user_email
    expected_price = order_data['shippingPrice']['gross']['amount']
    assert expected_price == order.shipping_price.gross.amount
    assert order_data['lines']['totalCount'] == order.lines.count()
    assert order_data['notes']['totalCount'] == order.notes.count()
    fulfillment = order.fulfillments.first().fulfillment_order
    fulfillment_order = order_data[
        'fulfillments'][0]['fulfillmentOrder']
    assert fulfillment_order == fulfillment


def test_non_staff_user_can_only_see_his_order(user_api_client, order):
    # FIXME: Remove client.login() when JWT authentication is re-enabled.
    user_api_client.login(username=order.user.email, password='password')

    query = """
    query OrderQuery($id: ID!) {
        order(id: $id) {
            number
        }
    }
    """
    ID = graphene.Node.to_global_id('Order', order.id)
    variables = json.dumps({'id': ID})
    response = user_api_client.post(
        reverse('api'), {'query': query, 'variables': variables})
    content = get_graphql_content(response)
    order_data = content['data']['order']
    assert order_data['number'] == str(order.pk)

    order.user = None
    order.save()
    response = user_api_client.post(
        reverse('api'), {'query': query, 'variables': variables})
    content = get_graphql_content(response)
    order_data = content['data']['order']
    assert not order_data


def test_draft_order_create(
        admin_api_client, customer_user, product_without_shipping,
        shipping_method, variant, voucher):
    variant_0 = variant
    query = """
    mutation draftCreate(
        $user: ID, $discount: Decimal, $lines: [OrderLineInput],
        $shippingAddress: AddressInput, $shippingMethod: ID, $voucher: ID) {
            draftOrderCreate(
                input: {user: $user, discount: $discount,
                lines: $lines, shippingAddress: $shippingAddress,
                shippingMethod: $shippingMethod, voucher: $voucher}) {
                    errors {
                        field
                        message
                    }
                    order {
                        discountAmount {
                            amount
                        }
                        discountName
                        lines {
                            edges {
                                node {
                                    productName
                                    productSku
                                    quantity
                                }
                            }
                        }
                        status
                        voucher {
                            code
                        }

                    }
                }
        }
    """
    user_id = graphene.Node.to_global_id('User', customer_user.id)
    variant_0_id = graphene.Node.to_global_id('ProductVariant', variant_0.id)
    variant_1 = product_without_shipping.variants.first()
    variant_1.quantity = 2
    variant_1.save()
    variant_1_id = graphene.Node.to_global_id('ProductVariant', variant_1.id)
    discount = '10'
    variant_list = [
        {'variantId': variant_0_id, 'quantity': 2},
        {'variantId': variant_1_id, 'quantity': 1}]
    shipping_address = {
        'firstName': 'John', 'country': 'PL'}
    shipping_id = graphene.Node.to_global_id(
        'ShippingMethod', shipping_method.id)
    voucher_id = graphene.Node.to_global_id('Voucher', voucher.id)
    variables = json.dumps(
        {
            'user': user_id, 'discount': discount,
            'lines': variant_list, 'shippingAddress': shipping_address,
            'shippingMethod': shipping_id, 'voucher': voucher_id})
    response = admin_api_client.post(
        reverse('api'), {'query': query, 'variables': variables})
    assert_read_only_mode(response)


def test_draft_order_update(admin_api_client, order_with_lines):
    order = order_with_lines
    query = """
        mutation draftUpdate($id: ID!, $email: String) {
            draftOrderUpdate(id: $id, input: {userEmail: $email}) {
                errors {
                    field
                    message
                }
                order {
                    userEmail
                }
            }
        }
        """
    email = 'not_default@example.com'
    order_id = graphene.Node.to_global_id('Order', order.id)
    variables = json.dumps({'id': order_id, 'email': email})
    response = admin_api_client.post(
        reverse('api'), {'query': query, 'variables': variables})
    assert_read_only_mode(response)


def test_draft_order_delete(admin_api_client, order_with_lines):
    order = order_with_lines
    query = """
        mutation draftDelete($id: ID!) {
            draftOrderDelete(id: $id) {
                order {
                    id
                }
            }
        }
        """
    order_id = graphene.Node.to_global_id('Order', order.id)
    variables = json.dumps({'id': order_id})
    response = admin_api_client.post(
        reverse('api'), {'query': query, 'variables': variables})
    assert_read_only_mode(response)


def test_check_for_draft_order_errors(order_with_lines):
    errors = check_for_draft_order_errors(order_with_lines, [])
    assert not errors


def test_check_for_draft_order_errors_wrong_shipping(order_with_lines):
    order = order_with_lines
    shipping_zone = order.shipping_method.shipping_zone
    shipping_zone.countries = ['DE']
    shipping_zone.save()
    assert order.shipping_address.country.code not in shipping_zone.countries
    errors = check_for_draft_order_errors(order, [])
    msg = 'Shipping method is not valid for chosen shipping address'
    assert errors[0].message == msg


def test_check_for_draft_order_errors_no_order_lines(order):
    errors = check_for_draft_order_errors(order, [])
    assert errors[0].message == 'Could not create order without any products.'


def test_draft_order_complete(admin_api_client, draft_order):
    order = draft_order
    query = """
        mutation draftComplete($id: ID!) {
            draftOrderComplete(id: $id) {
                order {
                    status
                }
            }
        }
        """
    order_id = graphene.Node.to_global_id('Order', order.id)
    variables = json.dumps({'id': order_id})
    response = admin_api_client.post(
        reverse('api'), {'query': query, 'variables': variables})
    assert_read_only_mode(response)


def test_order_update(admin_api_client, order_with_lines):
    order = order_with_lines
    query = """
        mutation orderUpdate(
        $id: ID!, $email: String, $first_name: String, $last_name: String,
        $country_code: String) {
            orderUpdate(
                id: $id, input: {
                    userEmail: $email, shippingAddress:
                    {firstName: $first_name, country: $country_code},
                    billingAddress:
                    {lastName: $last_name, country: $country_code}}) {
                errors {
                    field
                    message
                }
                order {
                    userEmail
                }
            }
        }
        """
    email = 'not_default@example.com'
    first_name = 'Test fname'
    last_name = 'Test lname'
    assert not order.user_email == email
    assert not order.shipping_address.first_name == first_name
    assert not order.billing_address.last_name == last_name
    order_id = graphene.Node.to_global_id('Order', order.id)
    variables = json.dumps(
        {'id': order_id, 'email': email, 'first_name': first_name,
         'last_name': last_name, 'country_code': 'PL'})
    response = admin_api_client.post(
        reverse('api'), {'query': query, 'variables': variables})
    assert_read_only_mode(response)


def test_order_add_note(admin_api_client, order_with_lines, admin_user):
    order = order_with_lines
    query = """
        mutation addNote(
        $id: ID!, $note: String, $user: ID) {
            orderAddNote(
            input: {order: $id, content: $note, user: $user}) {
                orderNote {
                    content
                    user {
                        email
                    }
                }
            }
        }
        """
    assert not order.notes.all()
    order_id = graphene.Node.to_global_id('Order', order.id)
    note = 'nuclear note'
    user = graphene.Node.to_global_id('User', admin_user.id)
    variables = json.dumps({'id': order_id, 'user': user, 'note': note})
    response = admin_api_client.post(
        reverse('api'), {'query': query, 'variables': variables})
    assert_read_only_mode(response)


def test_order_cancel(admin_api_client, order_with_lines):
    order = order_with_lines
    query = """
        mutation cancelOrder($id: ID!, $restock: Boolean!) {
            orderCancel(id: $id, restock: $restock) {
                order {
                    status
                }
            }
        }
    """
    order_id = graphene.Node.to_global_id('Order', order.id)
    restock = True
    quantity = order.get_total_quantity()
    variables = json.dumps({'id': order_id, 'restock': restock})
    response = admin_api_client.post(
        reverse('api'), {'query': query, 'variables': variables})
    assert_read_only_mode(response)


def test_order_capture(admin_api_client, payment_preauth):
    order = payment_preauth.order
    query = """
        mutation captureOrder($id: ID!, $amount: Decimal!) {
            orderCapture(id: $id, amount: $amount) {
                order {
                    paymentStatus
                    isPaid
                    capturedAmount {
                        amount
                    }
                }
            }
        }
    """
    order_id = graphene.Node.to_global_id('Order', order.id)
    amount = str(payment_preauth.get_total_price().gross.amount)
    variables = json.dumps({'id': order_id, 'amount': amount})
    response = admin_api_client.post(
        reverse('api'), {'query': query, 'variables': variables})
    assert_read_only_mode(response)


def test_paid_order_mark_as_paid(
        admin_api_client, payment_preauth):
    order = payment_preauth.order
    query = """
            mutation markPaid($id: ID!) {
                orderMarkAsPaid(id: $id) {
                    errors {
                        field
                        message
                    }
                    order {
                        isPaid
                    }
                }
            }
        """
    order_id = graphene.Node.to_global_id('Order', order.id)
    variables = json.dumps({'id': order_id})
    response = admin_api_client.post(
        reverse('api'), {'query': query, 'variables': variables})
    assert_read_only_mode(response)


def test_order_mark_as_paid(
        admin_api_client, order_with_lines):
    order = order_with_lines
    query = """
            mutation markPaid($id: ID!) {
                orderMarkAsPaid(id: $id) {
                    errors {
                        field
                        message
                    }
                    order {
                        isPaid
                    }
                }
            }
        """
    assert not order.is_fully_paid()
    order_id = graphene.Node.to_global_id('Order', order.id)
    variables = json.dumps({'id': order_id})
    response = admin_api_client.post(
        reverse('api'), {'query': query, 'variables': variables})
    assert_read_only_mode(response)


def test_order_release(admin_api_client, payment_preauth):
    order = payment_preauth.order
    query = """
            mutation releaseOrder($id: ID!) {
                orderRelease(id: $id) {
                    order {
                        paymentStatus
                    }
                }
            }
        """
    order_id = graphene.Node.to_global_id('Order', order.id)
    variables = json.dumps({'id': order_id})
    response = admin_api_client.post(
        reverse('api'), {'query': query, 'variables': variables})
    assert_read_only_mode(response)


def test_order_refund(admin_api_client, payment_confirmed):
    order = order = payment_confirmed.order
    query = """
        mutation refundOrder($id: ID!, $amount: Decimal!) {
            orderRefund(id: $id, amount: $amount) {
                order {
                    paymentStatus
                    isPaid
                }
            }
        }
    """
    order_id = graphene.Node.to_global_id('Order', order.id)
    amount = str(payment_confirmed.get_total_price().gross.amount)
    variables = json.dumps({'id': order_id, 'amount': amount})
    response = admin_api_client.post(
        reverse('api'), {'query': query, 'variables': variables})
    assert_read_only_mode(response)


def test_clean_order_release_payment():
    payment = MagicMock(spec=Payment)
    payment.status = 'not preauth'
    errors = clean_release_payment(payment, [])
    assert errors[0].field == 'payment'
    assert errors[0].message == 'Only pre-authorized payments can be released'

    payment.status = PaymentStatus.PREAUTH
    error_msg = 'error has happened.'
    payment.release = Mock(side_effect=ValueError(error_msg))
    errors = clean_release_payment(payment, [])
    assert errors[0].field == 'payment'
    assert errors[0].message == error_msg


def test_clean_order_refund_payment():
    payment = MagicMock(spec=Payment)
    payment.variant = CustomPaymentChoices.MANUAL
    amount = Mock(spec='string')
    errors = clean_refund_payment(payment, amount, [])
    assert errors[0].field == 'payment'
    assert errors[0].message == 'Manual payments can not be refunded.'

    payment.variant = None
    error_msg = 'error has happened.'
    payment.refund = Mock(side_effect=ValueError(error_msg))
    errors = clean_refund_payment(payment, amount, [])
    assert errors[0].field == 'payment'
    assert errors[0].message == error_msg
