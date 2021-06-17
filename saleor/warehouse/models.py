import itertools
import uuid
from typing import Set

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Count, Exists, F, OuterRef, Q, Prefetch, Sum
from django.db.models.expressions import Subquery
from django.db.models.functions import Coalesce
from django.db.models.query import QuerySet

from ..account.models import Address
from ..channel.models import Channel
from ..checkout.models import CheckoutLine
from ..core.models import ModelWithMetadata
from ..order.models import OrderLine
from ..product.models import Product, ProductVariant
from ..shipping.models import ShippingZone
from . import WarehouseClickAndCollectOption


class WarehouseQueryset(models.QuerySet):
    def prefetch_data(self):
        return self.select_related("address").prefetch_related("shipping_zones")

    def for_country(self, country: str):
        return (
            self.prefetch_data()
            .filter(shipping_zones__countries__contains=country)
            .order_by("pk")
        )

    def applicable_for_click_and_collect(self, lines: QuerySet[CheckoutLine]):
        lines_quantity = (
            lines.filter(variant_id=OuterRef("product_variant_id"))
            .annotate(prod_sum=Sum("quantity"))
            .values("prod_sum")
        )

        stock_qs = (
            Stock.objects.annotate_available_quantity()
            .annotate(line_quantity=F("available_quantity") - Subquery(lines_quantity))
            .filter(
                product_variant__id__in=lines.values("variant_id"),
                line_quantity__gt=0,
            )
            .select_related("product_variant")
        )

        local_warehouses_qs = (
            self.prefetch_related(Prefetch("stock_set", queryset=stock_qs))
            .filter(stock__in=stock_qs)
            .annotate(stock_num=Count("stock__id"))
            .filter(
                stock_num=lines.count(),
                click_and_collect_option=WarehouseClickAndCollectOption.LOCAL_STOCK,
            )
        )

        all_warehouses_qs = self.filter(
            click_and_collect_option=WarehouseClickAndCollectOption.ALL_WAREHOUSES
        )
        ids = [
            warehouse.id
            for warehouse in itertools.chain(local_warehouses_qs, all_warehouses_qs)
        ]

        return self.filter(pk__in=ids)


class Warehouse(ModelWithMetadata):

    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=250)
    slug = models.SlugField(max_length=255, unique=True, allow_unicode=True)
    shipping_zones = models.ManyToManyField(
        ShippingZone, blank=True, related_name="warehouses"
    )
    address = models.ForeignKey(Address, on_delete=models.PROTECT)
    email = models.EmailField(blank=True, default="")
    click_and_collect_option = models.CharField(
        max_length=30,
        choices=WarehouseClickAndCollectOption.CHOICES,
        default=WarehouseClickAndCollectOption.DISABLED,
    )
    is_private = models.BooleanField(default=True)

    objects = models.Manager.from_queryset(WarehouseQueryset)()

    class Meta(ModelWithMetadata.Meta):
        ordering = ("-slug",)

    def __str__(self):
        return self.name

    @property
    def countries(self) -> Set[str]:
        shipping_zones = self.shipping_zones.all()
        return set(itertools.chain(*[zone.countries for zone in shipping_zones]))

    def delete(self, *args, **kwargs):
        address = self.address
        super().delete(*args, **kwargs)
        address.delete()

    def clean(self) -> None:
        if (
            self.click_and_collect_option == WarehouseClickAndCollectOption.LOCAL_STOCK
            and self.is_private
        ):
            raise ValidationError(
                {
                    "click_and_collect_option": (
                        "Cannot set click&collect to 'LOCAL STOCK'"
                        "when warehouse is private"
                    )
                }
            )
        super().clean()


class StockQuerySet(models.QuerySet):
    def annotate_available_quantity(self):
        return self.annotate(
            available_quantity=F("quantity")
            - Coalesce(
                Sum(
                    "allocations__quantity_allocated",
                    filter=Q(allocations__quantity_allocated__gt=0),
                ),
                0,
            )
        )

    def for_channel(self, channel_slug: str):
        ShippingZoneChannel = Channel.shipping_zones.through  # type: ignore
        WarehouseShippingZone = ShippingZone.warehouses.through  # type: ignore
        channels = Channel.objects.filter(slug=channel_slug).values("pk")
        shipping_zone_channels = ShippingZoneChannel.objects.filter(
            Exists(channels.filter(pk=OuterRef("channel_id")))
        ).values("shippingzone_id")
        warehouse_shipping_zones = WarehouseShippingZone.objects.filter(
            Exists(
                shipping_zone_channels.filter(
                    shippingzone_id=OuterRef("shippingzone_id")
                )
            )
        ).values("warehouse_id")
        return self.select_related("product_variant").filter(
            Exists(
                warehouse_shipping_zones.filter(warehouse_id=OuterRef("warehouse_id"))
            )
        )

    def for_country_and_channel(self, country_code: str, channel_slug):
        filter_lookup = {"shipping_zones__countries__contains": country_code}
        if channel_slug is not None:
            filter_lookup["shipping_zones__channels__slug"] = channel_slug
        query_warehouse = models.Subquery(
            Warehouse.objects.filter(**filter_lookup).values("pk")
        )
        return self.select_related("product_variant", "warehouse").filter(
            warehouse__in=query_warehouse
        )

    def get_variant_stocks_for_country(
        self, country_code: str, channel_slug: str, product_variant: ProductVariant
    ):
        """Return the stock information about the a stock for a given country.

        Note it will raise a 'Stock.DoesNotExist' exception if no such stock is found.
        """
        return self.for_country_and_channel(country_code, channel_slug).filter(
            product_variant=product_variant
        )

    def get_product_stocks_for_country_and_channel(
        self, country_code: str, channel_slug: str, product: Product
    ):
        return self.for_country_and_channel(country_code, channel_slug).filter(
            product_variant__product_id=product.pk
        )


class Stock(models.Model):
    warehouse = models.ForeignKey(Warehouse, null=False, on_delete=models.CASCADE)
    product_variant = models.ForeignKey(
        ProductVariant, null=False, on_delete=models.CASCADE, related_name="stocks"
    )
    quantity = models.PositiveIntegerField(default=0)

    objects = models.Manager.from_queryset(StockQuerySet)()

    class Meta:
        unique_together = [["warehouse", "product_variant"]]
        ordering = ("pk",)

    def increase_stock(self, quantity: int, commit: bool = True):
        """Return given quantity of product to a stock."""
        self.quantity = F("quantity") + quantity
        if commit:
            self.save(update_fields=["quantity"])

    def decrease_stock(self, quantity: int, commit: bool = True):
        self.quantity = F("quantity") - quantity
        if commit:
            self.save(update_fields=["quantity"])


class AllocationQueryset(models.QuerySet):
    def annotate_stock_available_quantity(self):
        return self.annotate(
            stock_available_quantity=F("stock__quantity")
            - Coalesce(Sum("stock__allocations__quantity_allocated"), 0)
        )

    def available_quantity_for_stock(self, stock: "Stock"):
        allocated_quantity = (
            self.filter(stock=stock).aggregate(Sum("quantity_allocated"))[
                "quantity_allocated__sum"
            ]
            or 0
        )
        return max(stock.quantity - allocated_quantity, 0)


class Allocation(models.Model):
    order_line = models.ForeignKey(
        OrderLine,
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name="allocations",
    )
    stock = models.ForeignKey(
        Stock,
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name="allocations",
    )
    quantity_allocated = models.PositiveIntegerField(default=0)

    objects = models.Manager.from_queryset(AllocationQueryset)()

    class Meta:
        unique_together = [["order_line", "stock"]]
        ordering = ("pk",)
