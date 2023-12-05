from collections import defaultdict
from typing import Union

from ..page.models import Page
from ..product.models import Product, ProductVariant
from .models import (
    AssignedPageAttribute,
    AssignedPageAttributeValue,
    AssignedProductAttribute,
    AssignedProductAttributeValue,
    AssignedVariantAttribute,
    AssignedVariantAttributeValue,
    AttributeValue,
)

AttributeAssignmentType = Union[
    AssignedProductAttribute, AssignedVariantAttribute, AssignedPageAttribute
]
T_INSTANCE = Union[Product, ProductVariant, Page]


def associate_attribute_values_to_instance(
    instance: T_INSTANCE, attr_val_map: dict[int, list]
):
    # Ensure the values are actually form the given attribute
    validate_attribute_owns_values(attr_val_map)

    # Associate the attribute and the passed values
    _associate_attribute_to_instance(instance, attr_val_map)


def _associate_attribute_to_instance(
    instance: T_INSTANCE, attr_val_map: dict[int, list]
):
    if isinstance(instance, Product):
        instance_attrs_ids = instance.product_type.attributeproduct.filter(
            attribute_id__in=attr_val_map.keys()
        ).values_list("pk", flat=True)

        assignments = _get_or_create_assignments(
            instance, instance_attrs_ids, AssignedProductAttribute, "product"
        )

        values_order_map = _assign_values(
            instance,
            assignments,
            attr_val_map,
            AssignedProductAttributeValue,
            "product",
        )
        _order_assigned_attr_values(
            values_order_map, assignments, attr_val_map, AssignedProductAttributeValue
        )
    elif isinstance(instance, ProductVariant):
        instance_attrs_ids = instance.product.product_type.attributevariant.filter(
            attribute_id__in=attr_val_map.keys()
        ).values_list(
            "pk", flat=True
        )  # type: ignore

        assignments = _get_or_create_assignments(
            instance, instance_attrs_ids, AssignedVariantAttribute, "variant"
        )
        values_order_map = _assign_values(
            instance, assignments, attr_val_map, AssignedVariantAttributeValue, None
        )
        _order_assigned_attr_values(
            values_order_map, assignments, attr_val_map, AssignedVariantAttributeValue
        )
    elif isinstance(instance, Page):
        instance_attrs_ids = instance.page_type.attributepage.filter(  # type: ignore
            attribute_id__in=attr_val_map.keys()
        ).values_list("pk", flat=True)

        assignments = _get_or_create_assignments(
            instance, instance_attrs_ids, AssignedPageAttribute, "page"
        )
        values_order_map = _assign_values(
            instance, assignments, attr_val_map, AssignedPageAttributeValue, "page"
        )
        _order_assigned_attr_values(
            values_order_map, assignments, attr_val_map, AssignedPageAttributeValue
        )
    else:
        raise AssertionError(f"{instance.__class__.__name__} is unsupported")


def _get_or_create_assignments(
    instance, instance_attrs_ids, assigment_model, instance_field_name
):
    instance_field_kwarg = {instance_field_name: instance}
    assignments = list(
        assigment_model.objects.filter(
            assignment_id__in=instance_attrs_ids, **instance_field_kwarg
        )
    )

    assignments_to_create = []
    for id in instance_attrs_ids:
        if id not in [a.assignment_id for a in assignments]:
            assignments_to_create.append(id)

    if assignments_to_create:
        assignments += list(
            assigment_model.objects.bulk_create(
                [
                    assigment_model(assignment_id=assignment_id, **instance_field_kwarg)
                    for assignment_id in assignments_to_create
                ]
            )
        )
    return assignments


def _assign_values(
    instance, assignments, attr_val_map, assigment_model, instance_field_name
) -> dict[int, list]:
    instance_field_kwarg = (
        {instance_field_name: instance} if instance_field_name else {}
    )

    assigment_attr_map = {a.assignment.attribute_id: a for a in assignments}

    assigment_model.objects.filter(
        assignment_id__in=[a.pk for a in assignments],
    ).exclude(
        value_id__in=[v.pk for values in attr_val_map.values() for v in values]
    ).delete()

    values_order_map = defaultdict(list)
    assigned_attr_values_instances = []
    for attr_id, values in attr_val_map.items():
        assignment = assigment_attr_map[attr_id]

        for value in values:
            assigned_attr_values_instances.append(
                assigment_model(
                    value=value, assignment_id=assignment.id, **instance_field_kwarg
                )
            )
            values_order_map[assignment.id].append(value.id)

    assigment_model.objects.bulk_create(
        assigned_attr_values_instances, ignore_conflicts=True
    )
    return values_order_map


def _order_assigned_attr_values(
    values_order_map, assignments, attr_val_map, assigment_model
) -> None:
    assigned_attrs_values = assigment_model.objects.filter(
        assignment_id__in=(a.pk for a in assignments),
        value_id__in=(v.pk for values in attr_val_map.values() for v in values),
    )
    for value in assigned_attrs_values:
        value.sort_order = values_order_map[value.assignment_id].index(value.value_id)

    assigment_model.objects.bulk_update(assigned_attrs_values, ["sort_order"])


def validate_attribute_owns_values(attr_val_map: dict[int, list]) -> None:
    values = defaultdict(set)
    for value in AttributeValue.objects.filter(
        attribute_id__in=attr_val_map.keys(),
        pk__in=[v.pk for values in attr_val_map.values() for v in values],
    ).iterator():
        values[value.attribute_id].add(value.id)

    for attribute_id, value_ids in attr_val_map.items():
        if values[attribute_id] != {v.pk for v in value_ids}:
            raise AssertionError("Some values are not from the provided attribute.")
