from typing import Dict, Union

from celery.utils.log import get_task_logger
from django.conf import settings
from django.core.files.storage import default_storage
from django.db.models import Q
from django.db.models.expressions import Exists, OuterRef
from django.utils import timezone

from ..celeryconf import app
from ..core import JobStatus
from . import ExportEvents, events
from .models import ExportEvent, ExportFile
from .notifications import send_export_failed_info
from .utils.export import export_gift_cards, export_products

task_logger = get_task_logger(__name__)


def on_task_failure(self, exc, task_id, args, kwargs, einfo):
    export_file_id = args[0]
    export_file = ExportFile.objects.get(pk=export_file_id)

    export_file.content_file = None
    export_file.status = JobStatus.FAILED
    export_file.save(update_fields=["status", "updated_at", "content_file"])

    events.export_failed_event(
        export_file=export_file,
        user=export_file.user,
        app=export_file.app,
        message=str(exc),
        error_type=str(einfo.type),
    )

    send_export_failed_info(export_file)


def on_task_success(self, retval, task_id, args, kwargs):
    export_file_id = args[0]

    export_file = ExportFile.objects.get(pk=export_file_id)
    export_file.status = JobStatus.SUCCESS
    export_file.save(update_fields=["status", "updated_at"])
    events.export_success_event(
        export_file=export_file, user=export_file.user, app=export_file.app
    )


@app.task(on_success=on_task_success, on_failure=on_task_failure)
def export_products_task(
    export_file_id: int,
    scope: Dict[str, Union[str, dict]],
    export_info: Dict[str, list],
    file_type: str,
    delimiter: str = ",",
):
    export_file = ExportFile.objects.get(pk=export_file_id)
    export_products(export_file, scope, export_info, file_type, delimiter)


@app.task(on_success=on_task_success, on_failure=on_task_failure)
def export_gift_cards_task(
    export_file_id: int,
    scope: Dict[str, Union[str, dict]],
    file_type: str,
    delimiter: str = ",",
):
    export_file = ExportFile.objects.get(pk=export_file_id)
    export_gift_cards(export_file, scope, file_type, delimiter)


@app.task
def delete_old_export_files():
    now = timezone.now()

    events = ExportEvent.objects.filter(
        type=ExportEvents.EXPORT_PENDING,
        date__lte=now - settings.EXPORT_FILES_TIMEDELTA,
    ).values("export_file_id")
    export_files = ExportFile.objects.filter(
        Q(events__isnull=True) | Exists(events.filter(export_file_id=OuterRef("id")))
    )

    if not export_files:
        return

    paths_to_delete = list(export_files.values_list("content_file", flat=True))

    for path in paths_to_delete:
        if path:
            default_storage.delete(path)

    count = export_files.count()
    export_files.delete()

    task_logger.debug("Delete %s export files.", count)
