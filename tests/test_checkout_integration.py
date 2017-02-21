from django.core.urlresolvers import reverse
from django.forms import model_to_dict
from django.utils.encoding import smart_text

from payments import FraudStatus, PaymentStatus
from saleor.shipping.models import ShippingMethod
from saleor.userprofile.models import User
from tests.utils import get_redirect_location


def test_checkout_flow(request_cart_with_item, client, shipping_method, valid_address):  # pylint: disable=W0613,R0914
    """Basic test case that confirms if core checkout flow works"""

    # Enter checkout
    checkout_index = client.get(reverse('checkout:index'), follow=True)
    # Checkout index redirects directly to shipping address step
    shipping_address = client.get(checkout_index.request['PATH_INFO'])

    # Enter shipping address data
    shipping_response = client.post(shipping_address.request['PATH_INFO'],
                                    data=valid_address, follow=True)

    # Select shipping method
    shipping_method_page = client.get(shipping_response.request['PATH_INFO'])

    # Redirect to summary after shipping method selection
    shipping_method_data = {'method': shipping_method.pk}
    shipping_method_response = client.post(shipping_method_page.request['PATH_INFO'],
                                           data=shipping_method_data, follow=True)

    # Summary page asks for Billing address, default is the same as shipping
    address_data = {'address': 'shipping_address'}
    summary_response = client.post(shipping_method_response.request['PATH_INFO'],
                                   data=address_data, follow=True)

    # After summary step, order is created and it waits for payment
    order = summary_response.context['order']

    # Select payment method
    payment_page = client.post(summary_response.request['PATH_INFO'],
                               data={'method': 'default'}, follow=True)
    assert len(payment_page.redirect_chain) == 1
    assert payment_page.status_code == 200
    # Go to payment details page, enter payment data
    payment_page_url = payment_page.redirect_chain[0][0]
    payment_data = {
        'status': PaymentStatus.PREAUTH,
        'fraud_status': FraudStatus.UNKNOWN,
        'gateway_response': '3ds-disabled',
        'verification_result': 'waiting'}
    payment_response = client.post(payment_page_url, data=payment_data)
    assert payment_response.status_code == 302
    order_password = reverse('order:create-password',
                             kwargs={'token': order.token})
    assert get_redirect_location(payment_response) == order_password


def test_checkout_flow_authenticated_user(authorized_client, billing_address,  # pylint: disable=R0914
                                          request_cart_with_item, customer_user,
                                          shipping_method):
    """Checkout with authenticated user and previously saved address"""

    # Prepare some data
    customer_user.addresses.add(billing_address)
    request_cart_with_item.user = customer_user
    request_cart_with_item.save()

    # Enter checkout
    # Checkout index redirects directly to shipping address step
    shipping_address = authorized_client.get(reverse('checkout:index'), follow=True)

    # Enter shipping address data
    shipping_data = {'address': billing_address.pk}
    shipping_method_page = authorized_client.post(shipping_address.request['PATH_INFO'],
                                                  data=shipping_data, follow=True)

    # Select shipping method
    shipping_method_data = {'method': shipping_method.pk}
    shipping_method_response = authorized_client.post(shipping_method_page.request['PATH_INFO'],
                                                      data=shipping_method_data, follow=True)

    # Summary page asks for Billing address, default is the same as shipping
    payment_method_data = {'address': 'shipping_address'}
    payment_method_page = authorized_client.post(shipping_method_response.request['PATH_INFO'],
                                                 data=payment_method_data, follow=True)

    # After summary step, order is created and it waits for payment
    order = payment_method_page.context['order']

    # Select payment method
    payment_page = authorized_client.post(payment_method_page.request['PATH_INFO'],
                                          data={'method': 'default'}, follow=True)

    # Go to payment details page, enter payment data
    payment_data = {
        'status': PaymentStatus.PREAUTH,
        'fraud_status': FraudStatus.UNKNOWN,
        'gateway_response': '3ds-disabled',
        'verification_result': 'waiting'}
    payment_response = authorized_client.post(payment_page.request['PATH_INFO'],
                                              data=payment_data)

    assert payment_response.status_code == 302
    order_password = reverse('order:create-password',
                             kwargs={'token': order.token})
    assert get_redirect_location(payment_response) == order_password


def test_address_without_shipping(request_cart_with_item, client, monkeypatch):  # pylint: disable=W0613
    """User tries to get shipping address step in checkout without shipping -
     if is redirected to summary step

    """

    monkeypatch.setattr('saleor.checkout.core.Checkout.is_shipping_required',
                        False)

    response = client.get(reverse('checkout:shipping-address'))
    assert response.status_code == 302
    assert get_redirect_location(response) == reverse('checkout:summary')


def test_shipping_method_without_shipping(request_cart_with_item, client, monkeypatch):  # pylint: disable=W0613
    """User tries to get shipping method step in checkout without shipping -
     if is redirected to summary step

    """

    monkeypatch.setattr('saleor.checkout.core.Checkout.is_shipping_required',
                        False)

    response = client.get(reverse('checkout:shipping-method'))
    assert response.status_code == 302
    assert get_redirect_location(response) == reverse('checkout:summary')


def test_shipping_method_without_address(request_cart_with_item, client):  # pylint: disable=W0613
    """User tries to get shipping method step without saved shipping address -
     if is redirected to shipping address step

    """

    response = client.get(reverse('checkout:shipping-method'))
    assert response.status_code == 302
    assert get_redirect_location(response) == reverse('checkout:shipping-address')


def test_summary_without_address(request_cart_with_item, client):  # pylint: disable=W0613
    """User tries to get summary step without saved shipping method -
     if is redirected to shipping method step

    """

    response = client.get(reverse('checkout:summary'))
    assert response.status_code == 302
    assert get_redirect_location(response) == reverse('checkout:shipping-method')


def test_summary_without_shipping_method(request_cart_with_item, client, monkeypatch):  # pylint: disable=W0613
    """User tries to get summary step without saved shipping method -
     if is redirected to shipping method step

    """

    # address test return true
    monkeypatch.setattr('saleor.checkout.core.Checkout.email',
                        True)

    response = client.get(reverse('checkout:summary'))
    assert response.status_code == 302
    assert get_redirect_location(response) == reverse('checkout:shipping-method')


def test_unauthorized_email_is_saved_shipping(client, customer_user,  # pylint: disable=W0613
                                              request_cart_with_item, shipping_method, valid_address):  # pylint: disable=W0613
    """Unauthorized user provide valid email address in shipping step -
      if is save in order
      if is save in session storage

    """

    # Enter checkout
    checkout_index = client.get(reverse('checkout:index'), follow=True)
    # Checkout index redirects directly to shipping address step
    shipping_address = client.get(checkout_index.request['PATH_INFO'])

    # Enter shipping address data
    shipping_response = client.post(shipping_address.request['PATH_INFO'],
                                    data=valid_address, follow=True)

    # Select shipping method
    shipping_method_page = client.get(shipping_response.request['PATH_INFO'])

    # Redirect to summary after shipping method selection
    shipping_method_data = {'method': shipping_method.pk}
    shipping_method_response = client.post(shipping_method_page.request['PATH_INFO'],
                                           data=shipping_method_data, follow=True)

    # Summary page asks for Billing address, default is the same as shipping
    address_data = {'country_form': 'true', 'preview': 'true'}
    summary_response = client.post(shipping_method_response.request['PATH_INFO'],
                                   data=address_data, follow=True)

    # After summary step, order is created and it waits for payment
    checkout = summary_response.context['checkout']
    assert checkout.storage['email'] == 'test@example.com'


    # Summary page asks for Billing address, default is the same as shipping
    address_data = {'address': 'shipping_address'}
    summary_response = client.post(shipping_method_response.request['PATH_INFO'],
                                   data=address_data, follow=True)
    order = summary_response.context['order']
    assert order.user_email == 'test@example.com'


def test_email_is_saved_in_order(authorized_client, billing_address, customer_user,  # pylint: disable=R0914
                                 request_cart_with_item, shipping_method):
    """Authorized user change own email after checkout - if is not changed in order"""

    # Prepare some data
    customer_user.addresses.add(billing_address)
    request_cart_with_item.user = customer_user
    request_cart_with_item.save()

    # Enter checkout
    # Checkout index redirects directly to shipping address step
    shipping_address = authorized_client.get(reverse('checkout:index'), follow=True)

    # Enter shipping address data
    shipping_data = {'address': billing_address.pk}
    shipping_method_page = authorized_client.post(shipping_address.request['PATH_INFO'],
                                                  data=shipping_data, follow=True)

    # Select shipping method
    shipping_method_data = {'method': shipping_method.pk}
    shipping_method_response = authorized_client.post(shipping_method_page.request['PATH_INFO'],
                                                      data=shipping_method_data, follow=True)

    # Summary page asks for Billing address, default is the same as shipping
    payment_method_data = {'address': 'shipping_address'}
    payment_method_page = authorized_client.post(shipping_method_response.request['PATH_INFO'],
                                                 data=payment_method_data, follow=True)

    # After summary step, order is created and it waits for payment
    order = payment_method_page.context['order']
    assert order.user_email == customer_user.email


def test_voucher_invalid(client, request_cart_with_item, shipping_method, valid_address, voucher):  # pylint: disable=W0613,R0914
    """Look: #549 #544"""

    voucher.usage_limit = 3
    voucher.save()
    # Enter checkout
    checkout_index = client.get(reverse('checkout:index'), follow=True)
    # Checkout index redirects directly to shipping address step
    shipping_address = client.get(checkout_index.request['PATH_INFO'])

    # Enter shipping address data
    shipping_response = client.post(shipping_address.request['PATH_INFO'],
                                    data=valid_address, follow=True)

    # Select shipping method
    shipping_method_page = client.get(shipping_response.request['PATH_INFO'])

    # Redirect to summary after shipping method selection
    shipping_method_data = {'method': shipping_method.pk}
    shipping_method_response = client.post(shipping_method_page.request['PATH_INFO'],
                                           data=shipping_method_data, follow=True)

    # Summary page asks for Billing address, default is the same as shipping
    url = shipping_method_response.request['PATH_INFO']
    discount_data = {'discount-voucher': voucher.code}
    voucher_response = client.post('{url}?next={url}'.format(url=url),
                                   follow=True, data=discount_data, HTTP_REFERER=url)
    assert voucher_response.context['checkout'].voucher_code == voucher.code
    voucher.used = 3
    voucher.save()
    address_data = {'address': 'shipping_address'}
    assert url == reverse('checkout:summary')
    summary_response = client.post(url, data=address_data, follow=True)
    assert summary_response.context['checkout'].voucher_code is None

    summary_response = client.post(url, data=address_data, follow=True)
    assert summary_response.context['order'].voucher is None


def test_remove_voucher(client, request_cart_with_item, shipping_method, valid_address, voucher):  # pylint: disable=W0613,R0914
    # Enter checkout
    checkout_index = client.get(reverse('checkout:index'), follow=True)
    # Checkout index redirects directly to shipping address step
    shipping_address = client.get(checkout_index.request['PATH_INFO'])

    # Enter shipping address data
    shipping_response = client.post(shipping_address.request['PATH_INFO'],
                                    data=valid_address, follow=True)

    # Select shipping method
    shipping_method_page = client.get(shipping_response.request['PATH_INFO'])

    # Redirect to summary after shipping method selection
    shipping_method_data = {'method': shipping_method.pk}
    shipping_method_response = client.post(shipping_method_page.request['PATH_INFO'],
                                           data=shipping_method_data, follow=True)

    # Summary page asks for Billing address, default is the same as shipping
    url = shipping_method_response.request['PATH_INFO']
    discount_data = {'discount-voucher': voucher.code}
    voucher_response = client.post('{url}?next={url}'.format(url=url),
                                   follow=True, data=discount_data, HTTP_REFERER=url)
    assert voucher_response.context['checkout'].voucher_code is not None
    # Remove voucher from checkout
    voucher_response = client.post(reverse('checkout:remove-voucher'),
                                   follow=True, HTTP_REFERER=url)
    assert voucher_response.status_code == 200
    assert voucher_response.context['checkout'].voucher_code is None


def test_user_pass_new_valid_shipping_address(authorized_client, customer_user,  # pylint: disable=W0613,R0914
                                              request_cart_with_item, shipping_method, valid_address):  # pylint: disable=W0613

    # Enter checkout
    checkout_index = authorized_client.get(reverse('checkout:index'), follow=True)
    # Checkout index redirects directly to shipping address step
    shipping_address = authorized_client.get(checkout_index.request['PATH_INFO'])

    # Enter shipping address data
    del valid_address['email']
    shipping_data_prepared = valid_address.copy()
    shipping_data_prepared['address'] = 'new_address'
    shipping_response = authorized_client.post(shipping_address.request['PATH_INFO'],
                                               data=shipping_data_prepared, follow=True)
    # Select shipping method
    shipping_method_page = authorized_client.get(shipping_response.request['PATH_INFO'])

    # Redirect to summary after shipping method selection
    shipping_method_data = {'method': shipping_method.pk}
    shipping_method_response = authorized_client.post(shipping_method_page.request['PATH_INFO'],
                                                      data=shipping_method_data, follow=True)

    # Summary page asks for Billing address, default is the same as shipping
    address_data = {'country_form': 'true', 'preview': 'true'}
    summary_response = authorized_client.post(shipping_method_response.request['PATH_INFO'],
                                              data=address_data, follow=True)

    # After summary step, order is created and it waits for payment
    checkout = summary_response.context['checkout']
    del checkout.storage['shipping_address']['id']
    assert checkout.storage['shipping_address'] == valid_address


    # Summary page asks for Billing address, default is the same as shipping
    address_data = {'address': 'shipping_address'}
    summary_response = authorized_client.post(shipping_method_response.request['PATH_INFO'],
                                              data=address_data, follow=True)
    order = summary_response.context['order']
    order_dict = model_to_dict(order.shipping_address, exclude=['id'])
    assert order_dict == valid_address

    user = User.objects.get(pk=customer_user.pk)
    default_shipping_address_dict = model_to_dict(user.default_shipping_address, exclude=['id'])
    shipping_address_dict = model_to_dict(order.shipping_address, exclude=['id'])
    assert default_shipping_address_dict == shipping_address_dict


def test_user_pass_new_valid_billing_address(authorized_client, customer_user,  # pylint: disable=W0613,R0914
                                             request_cart_with_item, shipping_method, valid_address):  # pylint: disable=W0613
    # Enter checkout
    checkout_index = authorized_client.get(reverse('checkout:index'), follow=True)
    # Checkout index redirects directly to shipping address step
    shipping_address = authorized_client.get(checkout_index.request['PATH_INFO'])

    # Enter shipping address data
    del valid_address['email']
    shipping_data_prepared = valid_address.copy()
    shipping_data_prepared['address'] = 'new_address'
    shipping_response = authorized_client.post(shipping_address.request['PATH_INFO'],
                                               data=shipping_data_prepared, follow=True)
    # Select shipping method
    shipping_method_page = authorized_client.get(shipping_response.request['PATH_INFO'])

    # Redirect to summary after shipping method selection
    shipping_method_data = {'method': shipping_method.pk}
    shipping_method_response = authorized_client.post(shipping_method_page.request['PATH_INFO'],
                                                      data=shipping_method_data, follow=True)

    # Summary page asks for Billing address, default is the same as shipping
    billing_data_prepared = valid_address.copy()
    billing_data_prepared['address'] = 'new_address'
    summary_response = authorized_client.post(shipping_method_response.request['PATH_INFO'],
                                              data=billing_data_prepared, follow=True)
    order = summary_response.context['order']
    order_dict = model_to_dict(order.billing_address, exclude=['id'])
    assert order_dict == valid_address

    user = User.objects.get(pk=customer_user.pk)
    assert model_to_dict(user.default_billing_address, exclude=['id']) == order_dict


def test_user_choose_existing_shipping_address(authorized_client, billing_address, customer_user,  # pylint: disable=W0613,R0914
                                               request_cart_with_item, shipping_method):  # pylint: disable=W0613
    customer_user.addresses.add(billing_address)

    # Enter checkout
    checkout_index = authorized_client.get(reverse('checkout:index'), follow=True)
    # Checkout index redirects directly to shipping address step
    shipping_address = authorized_client.get(checkout_index.request['PATH_INFO'])

    # Enter shipping address data
    shipping_data = {'address': billing_address.pk}
    shipping_response = authorized_client.post(shipping_address.request['PATH_INFO'],
                                               data=shipping_data, follow=True)
    # Select shipping method
    shipping_method_page = authorized_client.get(shipping_response.request['PATH_INFO'])

    # Redirect to summary after shipping method selection
    shipping_method_data = {'method': shipping_method.pk}
    shipping_method_response = authorized_client.post(shipping_method_page.request['PATH_INFO'],
                                                      data=shipping_method_data, follow=True)

    # Summary page asks for Billing address, default is the same as shipping
    address_data = {'address': 'shipping_address'}
    summary_response = authorized_client.post(shipping_method_response.request['PATH_INFO'],
                                              data=address_data, follow=True)
    order = summary_response.context['order']
    order_dict = model_to_dict(billing_address, exclude=['id'])
    assert order_dict == model_to_dict(order.shipping_address, exclude=['id'])

    default_shipping_address_dict = model_to_dict(order.shipping_address, exclude=['id'])
    shipping_address_dict = model_to_dict(order.shipping_address, exclude=['id'])
    assert default_shipping_address_dict == shipping_address_dict



def test_user_choose_existing_billing_address(authorized_client, billing_address, customer_user,  # pylint: disable=R0914
                                              request_cart_with_item, shipping_method, valid_address):  # pylint: disable=W0613
    customer_user.addresses.add(billing_address)

    # Enter checkout
    checkout_index = authorized_client.get(reverse('checkout:index'), follow=True)
    # Checkout index redirects directly to shipping address step
    shipping_address = authorized_client.get(checkout_index.request['PATH_INFO'])
    # Enter shipping address data
    valid_address['address'] = 'new_address'

    shipping_response = authorized_client.post(shipping_address.request['PATH_INFO'],
                                               data=valid_address, follow=True)
    # Select shipping method
    shipping_method_page = authorized_client.get(shipping_response.request['PATH_INFO'])

    # Redirect to summary after shipping method selection
    shipping_method_data = {'method': shipping_method.pk}
    shipping_method_response = authorized_client.post(shipping_method_page.request['PATH_INFO'],
                                                      data=shipping_method_data, follow=True)

    # Summary page asks for Billing address, default is the same as shipping
    address_data = {'address': billing_address.pk}
    summary_response = authorized_client.post(shipping_method_response.request['PATH_INFO'],
                                              data=address_data, follow=True)
    order = summary_response.context['order']
    order_dict = model_to_dict(order.billing_address, exclude=['id'])
    assert order_dict == model_to_dict(billing_address, exclude=['id'])

    user = User.objects.get(pk=customer_user.pk)
    assert model_to_dict(user.default_billing_address, exclude=['id']) ==\
           model_to_dict(billing_address, exclude=['id'])


def test_user_choose_existing_shipping_method(authorized_client, billing_address, customer_user,  # pylint: disable=R0914
                                              request_cart_with_item, shipping_method, valid_address):  # pylint: disable=W0613
    customer_user.addresses.add(billing_address)

    # Enter checkout
    checkout_index = authorized_client.get(reverse('checkout:index'), follow=True)
    # Checkout index redirects directly to shipping address step
    shipping_address = authorized_client.get(checkout_index.request['PATH_INFO'])
    # Enter shipping address data
    valid_address['address'] = 'new_address'
    shipping_response = authorized_client.post(shipping_address.request['PATH_INFO'],
                                               data=valid_address, follow=True)
    # Select shipping method
    shipping_method_page = authorized_client.get(shipping_response.request['PATH_INFO'])

    # Redirect to summary after shipping method selection
    shipping_method_data = {'method': shipping_method.pk}
    shipping_method_response = authorized_client.post(shipping_method_page.request['PATH_INFO'],
                                                      data=shipping_method_data, follow=True)

    # Summary page asks for Billing address, default is the same as shipping
    address_data = {'country_form': 'true', 'preview': 'true'}
    summary_response = authorized_client.post(shipping_method_response.request['PATH_INFO'],
                                              data=address_data, follow=True)

    assert summary_response.context['checkout'].shipping_method ==\
           shipping_method.price_per_country.all()[0]

    address_data = {'address': billing_address.pk}
    summary_response = authorized_client.post(shipping_method_response.request['PATH_INFO'],
                                              data=address_data, follow=True)
    order = summary_response.context['order']
    assert order.groups.count() == 1
    name = order.groups.all()[0].shipping_method_name
    assert name == smart_text(shipping_method.price_per_country.all()[0])

    shipping_method.delete()
    assert order.groups.all()[0].shipping_method_name == name


def test_user_choose_existing_shipping_method_then_change_it(authorized_client, billing_address,  # pylint: disable=R0914
                                                             customer_user, request_cart_with_item,  # pylint: disable=W0613
                                                             shipping_method, valid_address):
    customer_user.addresses.add(billing_address)

    # Enter checkout
    checkout_index = authorized_client.get(reverse('checkout:index'), follow=True)
    # Checkout index redirects directly to shipping address step
    shipping_address = authorized_client.get(checkout_index.request['PATH_INFO'])
    # Enter shipping address data
    valid_address['address'] ='new_address'
    shipping_response = authorized_client.post(shipping_address.request['PATH_INFO'],
                                               data=valid_address, follow=True)
    # Select shipping method
    shipping_method_page = authorized_client.get(shipping_response.request['PATH_INFO'])

    # Redirect to summary after shipping method selection
    shipping_method_data = {'method': shipping_method.pk}
    shipping_method_response = authorized_client.post(shipping_method_page.request['PATH_INFO'],
                                                      data=shipping_method_data, follow=True)

    shipping_method = ShippingMethod.objects.create(name='Post')
    shipping_method.price_per_country.create(price=10)

    shipping_method_data = {'method': shipping_method.pk}
    shipping_method_response = authorized_client.post(shipping_method_page.request['PATH_INFO'],
                                                      data=shipping_method_data, follow=True)

    # Summary page asks for Billing address, default is the same as shipping
    address_data = {'country_form': 'true', 'preview': 'true'}
    summary_response = authorized_client.post(shipping_method_response.request['PATH_INFO'],
                                              data=address_data, follow=True)
    shipping_method_price = shipping_method.price_per_country.all()[0]
    assert summary_response.context['checkout'].shipping_method == shipping_method_price

    address_data = {'address': billing_address.pk}
    summary_response = authorized_client.post(shipping_method_response.request['PATH_INFO'],
                                              data=address_data, follow=True)
    order = summary_response.context['order']
    assert order.groups.count() == 1
    name = order.groups.all()[0].shipping_method_name
    assert name == smart_text(shipping_method.price_per_country.all()[0])


def test_invalid_shipping_address(authorized_client, request_cart_with_item):  # pylint: disable=R0914,W0613

    # Enter checkout
    checkout_index = authorized_client.get(reverse('checkout:index'), follow=True)
    # Checkout index redirects directly to shipping address step
    shipping_address = authorized_client.get(checkout_index.request['PATH_INFO'])
    # Enter shipping address data
    shipping_data = {
        'address': 'new_address',
        'country': 'PL'}
    shipping_response = authorized_client.post(shipping_address.request['PATH_INFO'],
                                               data=shipping_data, follow=True)
    form = shipping_response.context['address_form']
    assert form['street_address_1'].errors == ['This field is required.']
    assert form['street_address_2'].errors == ['This field is required.']
    assert form['postal_code'].errors == ['This field is required.']
    assert form['city'].errors == ['This field is required.']

    shipping_data = {
        'address': '-1',
        'country': 'PL'}
    shipping_response = authorized_client.post(shipping_address.request['PATH_INFO'],
                                               data=shipping_data, follow=True)
    assert shipping_response.context['user_form']['address'].errors ==\
           ['Select a valid choice. -1 is not one of the available choices.']


def test_invalid_billing_address(authorized_client, billing_address, customer_user,  # pylint: disable=R0914
                                 request_cart_with_item, shipping_method, valid_address):  # pylint: disable=W0613
    customer_user.addresses.add(billing_address)

    # Enter checkout
    checkout_index = authorized_client.get(reverse('checkout:index'), follow=True)
    # Checkout index redirects directly to shipping address step
    shipping_address = authorized_client.get(checkout_index.request['PATH_INFO'])
    # Enter shipping address data
    shipping_response = authorized_client.post(shipping_address.request['PATH_INFO'],
                                               data=valid_address, follow=True)
    # Select shipping method
    shipping_method_page = authorized_client.get(shipping_response.request['PATH_INFO'])

    # Redirect to summary after shipping method selection
    shipping_method_data = {'method': shipping_method.pk}
    shipping_method_response = authorized_client.post(shipping_method_page.request['PATH_INFO'],
                                                      data=shipping_method_data, follow=True)

    # Summary page asks for Billing address, default is the same as shipping
    address_data = {'address': '-1'}
    summary_response = authorized_client.post(shipping_method_response.request['PATH_INFO'],
                                              data=address_data, follow=True)
    assert summary_response.context['addresses_form']['address'].errors ==\
           ['Select a valid choice. -1 is not one of the available choices.']

    address_data = {
        'address': 'new_address',
        'country': 'PL'}
    summary_response = authorized_client.post(shipping_method_response.request['PATH_INFO'],
                                              data=address_data, follow=True)
    form = summary_response.context['address_form']
    assert form['street_address_1'].errors == ['This field is required.']
    assert form['street_address_2'].errors == ['This field is required.']
    assert form['postal_code'].errors == ['This field is required.']
    assert form['city'].errors == ['This field is required.']


def test_language_is_saved_in_order(authorized_client, billing_address, customer_user,  # pylint: disable=R0913, R0914
                                    request_cart_with_item, settings, shipping_method):
    """
    authorized user change own email after checkout - if is not changed in order
    """
    # Prepare some data
    user_language = 'fr'
    settings.LANGUAGE_CODE = 'en'
    customer_user.addresses.add(billing_address)
    request_cart_with_item.user = customer_user
    request_cart_with_item.save()

    # Enter checkout
    # Checkout index redirects directly to shipping address step
    shipping_address = authorized_client.get(reverse('checkout:index'),
                                             follow=True, HTTP_ACCEPT_LANGUAGE=user_language)

    # Enter shipping address data
    shipping_data = {'address': billing_address.pk}
    shipping_method_page = authorized_client.post(shipping_address.request['PATH_INFO'],
                                                  data=shipping_data, follow=True,
                                                  HTTP_ACCEPT_LANGUAGE=user_language)

    # Select shipping method
    shipping_method_data = {'method': shipping_method.pk}
    shipping_method_response = authorized_client.post(shipping_method_page.request['PATH_INFO'],
                                                      data=shipping_method_data, follow=True,
                                                      HTTP_ACCEPT_LANGUAGE=user_language)

    # Summary page asks for Billing address, default is the same as shipping
    payment_method_data = {'address': 'shipping_address'}
    payment_method_page = authorized_client.post(shipping_method_response.request['PATH_INFO'],
                                                 data=payment_method_data, follow=True,
                                                 HTTP_ACCEPT_LANGUAGE=user_language)

    # After summary step, order is created and it waits for payment
    order = payment_method_page.context['order']
    assert order.language_code == user_language
