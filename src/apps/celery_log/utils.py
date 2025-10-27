import json
from boltons.tbutils import ContextualExceptionInfo


def clean_locals(locals_dict, safe_types=(str, int, float, bool, type(None))):
    return {
        k: (v if isinstance(v, safe_types) else repr(v))
        for k, v in locals_dict.items()
        if not k.startswith("_") or k in ['In', 'Out']
    }


def get_contextual_traceback():
    exception_data = ContextualExceptionInfo.from_current().to_dict()
    frames = exception_data.get("exc_tb", {}).get("frames") or []
    for idx, frame in enumerate(frames):
        # remove duplicated context keys
        frame.pop("pre_lines", None)
        frame.pop("post_lines", None)

        # first frame usually tem só imports/module-level, clear the locals
        if idx == 0:
            frame["locals"] = {}
        else:
            locs = frame.get("locals")
            if isinstance(locs, dict):
                frame["locals"] = clean_locals(locs)
            else:
                frame["locals"] = {}

    return exception_data


def get_periodic_task_name(request):
    """
    Extract periodic task name from request headers.

    Args:
        request: Celery request object

    Returns:
        str or None: Periodic task name if found, None otherwise
    """
    periodic_task_name = None
    if hasattr(request, 'headers') and request.headers:
        # Check common header names for periodic task identification
        periodic_task_name = (
            request.headers.get('periodic_task_name') or
            request.headers.get('task') or
            request.headers.get('origin')
        )
    return periodic_task_name


def sort_dict_recursively(obj):
    """
    Recursively sort dictionaries by keys.
    """
    if isinstance(obj, dict):
        return {key: sort_dict_recursively(value) for key, value in sorted(obj.items())}
    elif isinstance(obj, list):
        return [sort_dict_recursively(item) for item in obj]
    else:
        return obj


def create_task_log(sender=None, exception=None, result=None, **kwargs):
    """
    Create a TaskLog entry for both success and failure cases.

    Args:
        sender: Celery task sender object
        exception: Exception object (for failure cases)
        result: Task result (for success cases)
        **kwargs: Additional parameters

    Returns:
        TaskLog: Created TaskLog instance
    """
    from .models import TaskLog

    # Get queue name from routing_key
    queue_name = sender.request.delivery_info.get('routing_key')

    # Get periodic task name from headers
    periodic_task_name = get_periodic_task_name(sender.request)

    # Common parameters for both success and failure
    task_log_data = {
        'task_id': sender.request.id,
        'task_name': sender.name,
        'periodic_task_name': periodic_task_name,
        'queue_name': queue_name,
        'worker': sender.request.hostname,
        'task_args': sender.request.args,
        'task_kwargs': sender.request.kwargs,
    }

    # Handle success case
    if exception is None:
        # Serialize result
        try:
            result_serialized = json.loads(json.dumps(result, default=str))
        except Exception:
            result_serialized = None

        task_log_data.update({
            'status': TaskLog.Status.SUCCESS,
            'result': result_serialized if isinstance(result_serialized, (str, dict, list, int, float)) else None,
        })
    else:
        # Handle failure case
        exception_data = get_contextual_traceback()
        task_log_data.update({
            'status': TaskLog.Status.FAILURE,
            'result': None,
            'error_message': f"{type(exception).__name__}: {exception}",
            'traceback': exception_data,
        })

    return TaskLog.objects.create(**task_log_data)
