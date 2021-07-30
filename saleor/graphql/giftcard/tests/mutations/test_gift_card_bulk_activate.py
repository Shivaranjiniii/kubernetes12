import graphene

from .....giftcard import GiftCardEvents
from .....giftcard.models import GiftCard, GiftCardEvent
from ....tests.utils import assert_no_permission, get_graphql_content

MUTATION_GIFT_CARD_BULK_ACTIVATE = """
    mutation GiftCardBulkActivate($ids: [ID]!) {
        giftCardBulkActivate(ids: $ids) {
            count
            errors {
                code
                field
            }
        }
    }
"""


def test_gift_card_bulk_activate_by_staff(
    staff_api_client,
    gift_card,
    gift_card_expiry_period,
    gift_card_expiry_date,
    permission_manage_gift_card,
):
    # given
    gift_card.is_active = False
    gift_card_expiry_period.is_active = False
    gift_card_expiry_date.is_active = True
    gift_cards = [gift_card, gift_card_expiry_period, gift_card_expiry_date]
    GiftCard.objects.bulk_update(gift_cards, ["is_active"])

    ids = [graphene.Node.to_global_id("GiftCard", card.pk) for card in gift_cards]
    variables = {"ids": ids}

    # when
    response = staff_api_client.post_graphql(
        MUTATION_GIFT_CARD_BULK_ACTIVATE,
        variables,
        permissions=(permission_manage_gift_card,),
    )

    # then
    content = get_graphql_content(response)
    data = content["data"]["giftCardBulkActivate"]

    assert data["count"] == len(ids)
    events = GiftCardEvent.objects.all()
    assert events.count() == 2
    assert {event.gift_card_id for event in events} == {
        gift_card.id,
        gift_card_expiry_period.id,
    }
    assert {event.type for event in events} == {GiftCardEvents.ACTIVATED}


def test_gift_card_bulk_activate_by_app(
    app_api_client,
    gift_card,
    gift_card_expiry_period,
    gift_card_expiry_date,
    permission_manage_gift_card,
):
    # given
    gift_card.is_active = False
    gift_card_expiry_period.is_active = False
    gift_card_expiry_date.is_active = False
    gift_cards = [gift_card, gift_card_expiry_period, gift_card_expiry_date]
    GiftCard.objects.bulk_update(gift_cards, ["is_active"])

    ids = [graphene.Node.to_global_id("GiftCard", card.pk) for card in gift_cards]
    variables = {"ids": ids}

    # when
    response = app_api_client.post_graphql(
        MUTATION_GIFT_CARD_BULK_ACTIVATE,
        variables,
        permissions=(permission_manage_gift_card,),
    )

    # then
    content = get_graphql_content(response)
    data = content["data"]["giftCardBulkActivate"]

    assert data["count"] == len(ids)
    events = GiftCardEvent.objects.all()
    assert events.count() == len(ids)
    assert {event.gift_card_id for event in events} == {card.id for card in gift_cards}
    assert {event.type for event in events} == {GiftCardEvents.ACTIVATED}


def test_gift_card_bulk_activate_all_cards_already_active(
    staff_api_client,
    gift_card,
    gift_card_expiry_period,
    gift_card_expiry_date,
    permission_manage_gift_card,
):
    # given
    gift_cards = [gift_card, gift_card_expiry_period, gift_card_expiry_date]
    GiftCard.objects.bulk_update(gift_cards, ["is_active"])

    ids = [graphene.Node.to_global_id("GiftCard", card.pk) for card in gift_cards]
    variables = {"ids": ids}

    # when
    response = staff_api_client.post_graphql(
        MUTATION_GIFT_CARD_BULK_ACTIVATE,
        variables,
        permissions=(permission_manage_gift_card,),
    )

    # then
    content = get_graphql_content(response)
    data = content["data"]["giftCardBulkActivate"]

    assert data["count"] == len(ids)
    events = GiftCardEvent.objects.all()
    assert events.count() == 0


def test_gift_card_bulk_activate_by_customer(
    api_client, gift_card, gift_card_expiry_period
):
    # given
    gift_card.is_active = False
    gift_card_expiry_period.is_active = False
    gift_cards = [gift_card, gift_card_expiry_period]
    GiftCard.objects.bulk_update(gift_cards, ["is_active"])

    ids = [graphene.Node.to_global_id("GiftCard", card.pk) for card in gift_cards]
    variables = {"ids": ids}

    # when
    response = api_client.post_graphql(
        MUTATION_GIFT_CARD_BULK_ACTIVATE,
        variables,
    )

    # then
    assert_no_permission(response)
