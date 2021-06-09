import logging
from decimal import Decimal
from typing import Optional, Tuple
from urllib.parse import urljoin

import stripe
from django.contrib.sites.models import Site
from django.urls import reverse
from stripe.error import AuthenticationError, InvalidRequestError, StripeError
from stripe.stripe_object import StripeObject

from saleor.core.utils import build_absolute_uri

from ...utils import price_to_minor_unit
from .consts import (
    AUTOMATIC_CAPTURE_METHOD,
    MANUAL_CAPTURE_METHOD,
    METADATA_IDENTIFIER,
    PLUGIN_ID,
    WEBHOOK_EVENTS,
    WEBHOOK_PATH,
)

logger = logging.getLogger(__name__)


def is_secret_api_key_valid(api_key: str):
    """Call api to check if api_key is a correct key."""
    try:
        stripe.WebhookEndpoint.list(api_key)
        return True
    except AuthenticationError:
        return False


def subscribe_webhook(api_key: str) -> StripeObject:
    domain = Site.objects.get_current().domain
    api_path = reverse("plugins", kwargs={"plugin_id": PLUGIN_ID})

    base_url = build_absolute_uri(api_path)
    webhook_url = urljoin(base_url, WEBHOOK_PATH)  # type: ignore

    return stripe.WebhookEndpoint.create(
        api_key=api_key,
        url=webhook_url,
        enabled_events=WEBHOOK_EVENTS,
        metadata={METADATA_IDENTIFIER: domain},
    )


def delete_webhook(api_key: str, webhook_id: str):
    try:
        stripe.WebhookEndpoint.delete(webhook_id, api_key=api_key)
    except InvalidRequestError:
        # webhook doesn't exist
        pass


def get_or_create_customer(
    api_key: str,
    customer_id: Optional[str] = None,
    customer_email: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> Optional[StripeObject]:
    try:
        if customer_id:
            return stripe.Customer.retrieve(customer_id, api_key=api_key)
        return stripe.Customer.create(
            api_key=api_key, email=customer_email, metadata=metadata
        )
    except StripeError:
        return None


def create_payment_intent(
    api_key: str,
    amount: Decimal,
    currency: str,
    auto_capture: bool = True,
    customer: Optional[StripeObject] = None,
    payment_method_id: Optional[str] = None,
) -> Tuple[Optional[StripeObject], Optional[StripeError]]:

    capture_method = AUTOMATIC_CAPTURE_METHOD if auto_capture else MANUAL_CAPTURE_METHOD
    additional_params = {}  # type: ignore
    if customer:
        additional_params = {
            "customer": customer,
            "setup_future_usage": "on_session",
        }

    if payment_method_id and customer:
        additional_params["payment_method"] = payment_method_id

    try:
        intent = stripe.PaymentIntent.create(
            api_key=api_key,
            amount=price_to_minor_unit(amount, currency),
            currency=currency,
            capture_method=capture_method,
            **additional_params,
        )
        return intent, None
    except StripeError as error:
        return None, error


def list_customer_payment_methods(
    api_key: str, customer_id: str
) -> Tuple[Optional[StripeObject], Optional[StripeError]]:
    try:
        payment_methods = stripe.PaymentMethod.list(
            api_key=api_key,
            customer=customer_id,
            type="card",  # we support only cards for now
        )
        return payment_methods, None
    except StripeError as error:
        return None, error


def retrieve_payment_intent(
    api_key: str, payment_intent_id: str
) -> Tuple[Optional[StripeObject], Optional[StripeError]]:
    try:
        payment_intent = stripe.PaymentIntent.retrieve(
            payment_intent_id, api_key=api_key
        )
        return payment_intent, None
    except StripeError as error:
        logger.warning("Unable to retrieve a payment intent (%s)", payment_intent_id)
        return None, error


def capture_payment_intent(
    api_key: str, payment_intent_id: str, amount_to_capture: int
) -> Tuple[Optional[StripeObject], Optional[StripeError]]:
    try:
        payment_intent = stripe.PaymentIntent.capture(
            payment_intent_id, amount_to_capture=amount_to_capture, api_key=api_key
        )
        return payment_intent, None
    except StripeError as error:
        logger.warning(
            "Unable to capture a payment intent (%s), error", payment_intent_id
        )
        return None, error


def refund_payment_intent(
    api_key: str, payment_intent_id: str, amount_to_refund: int
) -> Tuple[Optional[StripeObject], Optional[StripeError]]:
    try:
        payment_intent = stripe.Refund.create(
            payment_intent=payment_intent_id, amount=amount_to_refund, api_key=api_key
        )
        return payment_intent, None
    except StripeError as error:
        logger.warning(
            "Unable to refund a payment intent (%s), error", payment_intent_id
        )
        return None, error


def cancel_payment_intent(
    api_key: str, payment_intent_id: str
) -> Tuple[Optional[StripeObject], Optional[StripeError]]:
    try:
        payment_intent = stripe.PaymentIntent.cancel(payment_intent_id, api_key=api_key)
        return payment_intent, None
    except StripeError as error:
        logger.warning(
            "Unable to cancel a payment intent (%s), error", payment_intent_id
        )
        return None, error


def construct_stripe_event(
    api_key: str, payload: bytes, sig_header: str, endpoint_secret: str
) -> StripeObject:
    return stripe.Webhook.construct_event(
        payload, sig_header, endpoint_secret, api_key=api_key
    )
