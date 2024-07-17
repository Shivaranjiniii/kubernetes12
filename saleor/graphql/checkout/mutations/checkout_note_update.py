import graphene

from ....webhook.event_types import WebhookEventAsyncType
from ...core import ResolveInfo
from ...core.descriptions import ADDED_IN_321
from ...core.doc_category import DOC_CATEGORY_CHECKOUT
from ...core.mutations import BaseMutation
from ...core.types import CheckoutError
from ...core.utils import WebhookEventInfo
from ...plugins.dataloaders import get_plugin_manager_promise
from ..types import Checkout


class CheckoutNoteUpdate(BaseMutation):
    checkout = graphene.Field(Checkout, description="An updated checkout.")

    class Arguments:
        id = graphene.ID(
            description="The checkout's ID." + ADDED_IN_321,
            required=False,
        )
        note = graphene.String(required=True, description="New note content.")

    class Meta:
        description = "Updates note in the existing checkout object." + ADDED_IN_321
        doc_category = DOC_CATEGORY_CHECKOUT
        error_type_class = CheckoutError
        error_type_field = "checkout_errors"
        webhook_events_info = [
            WebhookEventInfo(
                type=WebhookEventAsyncType.CHECKOUT_UPDATED,
                description="A checkout was updated.",
            )
        ]

    @classmethod
    def perform_mutation(  # type: ignore[override]
        cls,
        _root,
        info: ResolveInfo,
        /,
        *,
        note,
        id=None,
    ):
        checkout = cls.get_node_or_error(info, id, only_type=Checkout)

        checkout.note = note
        cls.clean_instance(info, checkout)
        checkout.save(update_fields=["note", "last_change"])
        manager = get_plugin_manager_promise(info.context).get()
        cls.call_event(manager.checkout_updated, checkout)
        return CheckoutNoteUpdate(checkout=checkout)
