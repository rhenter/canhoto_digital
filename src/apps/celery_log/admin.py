import json

from django.contrib import admin
from django.contrib import messages
from django.db.models import JSONField
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from apps.core.widgets import PrettyJSONWidget
from proj_settings.celery import celery_app
from .models import TaskLog, TaskLogStatistics
from .utils import sort_dict_recursively


@admin.register(TaskLog)
class TaskLogAdmin(admin.ModelAdmin):
    model = TaskLog
    date_hierarchy = 'timestamp'
    list_display = (
        'id',
        'task_name',
        '_timestamp',
        'status',
        'result_snippet'
    )
    list_filter = ('status', 'timestamp', 'task_name', 'queue_name')
    readonly_fields = (
        'timestamp',
        'worker',
        'status',
        'task_id',
        'task_name',
        'periodic_task_name',
        'queue_name',
        'exc_type',
        'exc_msg',
        'result_pretty',
        'traceback_pretty',
    )
    search_fields = ('task_name', 'result')
    fieldsets = (
        (None, {
            'fields': (
                'task_id',
                'task_name',
                'periodic_task_name',
                'queue_name',
                'status',
                'worker',
            ),
            'classes': ('extrapretty', 'wide')
        }),
        (_('Parameters'), {
            'fields': (
                'task_args',
                'task_kwargs',
            ),
            'classes': ('extrapretty', 'wide')
        }),
        (_('Result'), {
            'fields': (
                'result_pretty',
                'timestamp',
                'exc_type',
                'exc_msg',
                'traceback_pretty',
            ),
            'classes': ('extrapretty', 'wide')
        }),
    )
    formfield_overrides = {
        JSONField: {'widget': PrettyJSONWidget}
    }
    list_per_page = 25

    def get_changelist_instance(self, request):
        """Override to set list_per_page before changelist creation"""
        # Handle list_per_page parameter from request
        list_per_page_options = [25, 50, 75, 100]
        selected_per_page = request.GET.get('list_per_page', '25')

        try:
            selected_per_page = int(selected_per_page)
            if selected_per_page in list_per_page_options:
                self.list_per_page = selected_per_page
        except (ValueError, TypeError):
            self.list_per_page = 25  # Default fallback

        # Create a modified request without the list_per_page parameter
        # to prevent Django from treating it as a filter
        if 'list_per_page' in request.GET:
            # Create a mutable copy of GET parameters
            get_params = request.GET.copy()
            del get_params['list_per_page']
            # Create a new request object with modified GET parameters
            request.GET = get_params

        return super().get_changelist_instance(request)

    def changelist_view(self, request, extra_context=None):
        """Custom changelist view to provide context for list_per_page selection"""
        list_per_page_options = [25, 50, 75, 100]

        # Get the original list_per_page parameter from request to maintain selection
        # when other filters change (like date filters)
        original_list_per_page = request.GET.get('list_per_page', '25')
        try:
            selected_per_page = int(original_list_per_page)
            if selected_per_page not in list_per_page_options:
                selected_per_page = 25  # Default fallback
        except (ValueError, TypeError):
            selected_per_page = 25  # Default fallback

        if extra_context is None:
            extra_context = {}

        extra_context.update({
            'list_per_page_options': list_per_page_options,
            'selected_per_page': selected_per_page,
        })

        return super().changelist_view(request, extra_context=extra_context)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def get_urls(self):
        """Add custom URLs for re-run functionality"""
        urls = super().get_urls()
        custom_urls = [
            path(
                '<path:object_id>/rerun/',
                self.admin_site.admin_view(self.rerun_task_view),
                name='celery_log_tasklog_rerun',
            ),
        ]
        return custom_urls + urls

    def rerun_task_view(self, request, object_id):
        """Re-run a task from the TaskLog"""
        try:
            task_log = self.get_object(request, object_id)
            if not task_log:
                messages.error(request, "Task log not found.")
                return HttpResponseRedirect(reverse('admin:celery_log_tasklog_changelist'))

            # Get task arguments
            task_args = task_log.task_args or []
            task_kwargs = task_log.task_kwargs or {}

            # Re-run the task using celery
            try:
                result = celery_app.send_task(
                    task_log.task_name,
                    args=task_args,
                    kwargs=task_kwargs,
                    queue=task_log.queue_name
                )
                messages.success(
                    request,
                    f"Task '{task_log.task_name}' has been re-queued with ID: {result.id}"
                )
            except Exception as e:
                messages.error(
                    request,
                    f"Failed to re-run task '{task_log.task_name}': {str(e)}"
                )

        except Exception as e:
            messages.error(request, f"Error processing re-run request: {str(e)}")

        return HttpResponseRedirect(
            reverse('admin:celery_log_tasklog_change', args=[object_id])
        )

    def exc_type(self, obj: TaskLog) -> str:
        """Show the exception type from the traceback JSON."""
        return (obj.traceback or {}).get('exc_type', '')

    exc_type.short_description = "Exception Type"

    def exc_msg(self, obj: TaskLog) -> str:
        """Show the exception message from the traceback JSON."""
        return (obj.traceback or {}).get('exc_msg', '')

    exc_msg.short_description = "Exception Message"

    def result_pretty(self, obj: TaskLog) -> str:
        """
        Render the TaskLog.result (JSON) as a wrapped <pre> block.
        """
        data = obj.result or {}
        raw = json.dumps(data, indent=2)
        safe = escape(raw)
        return mark_safe(
            f"""
    <pre style="
        background: #f7f7f7;
        padding: 8px;
        border: 1px solid #ddd;
        white-space: pre-wrap;
        word-wrap: break-word;
        word-break: break-all;
        max-height: 500px;
        overflow: auto;
    ">{safe}</pre>
    """)

    result_pretty.short_description = "Result"

    def result_snippet(self, obj: TaskLog) -> str:
        data = obj.result or {}
        if not data and obj.status == TaskLog.Status.FAILURE:
            data = {"error": obj.error_message}

        data = sort_dict_recursively(data)
        # 1) one-liner JSON for the summary
        raw_compact = json.dumps(data, separators=(',', ':'))
        safe_compact = escape(raw_compact)

        # 2) pretty JSON for the expanded <pre>
        raw_pretty = json.dumps(data, indent=2)
        safe_pretty = escape(raw_pretty)

        html = f'''
    <details style="
        display:inline-block;
        max-width:500px;
        vertical-align:top;
    ">
      <summary style="
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          cursor: pointer;
      ">{safe_compact}</summary>
      <pre style="
          background:#f7f7f7;
          padding:4px;
          border:1px solid #ddd;
          margin:4px 0;
          white-space: pre-wrap;
          word-wrap: break-word;
          max-height:500px;
          overflow:auto;
      ">{safe_pretty}</pre>
    </details>
    '''
        return mark_safe(html)

    result_snippet.short_description = "Result"

    def traceback_pretty(self, obj: TaskLog) -> str:
        tb = obj.traceback or {}
        frames = tb.get('exc_tb', {}).get('frames', [])
        html_chunks = []
        total = len(frames)

        for i, frame in enumerate(frames):
            is_last = (i == total - 1)
            # if it's the last frame, open it by default
            details_attr = ' open' if is_last else ''
            header = (
                f"Frame {i}: "
                f"{frame.get('func_name')} @ "
                f"{frame.get('module_name')}:{frame.get('lineno')}"
            )

            raw = json.dumps(frame, indent=2)
            safe_payload = escape(raw)

            html_chunks.append(f"""
    <details{details_attr} style="margin-bottom:8px;">
      <summary style="font-weight:bold;">{header}</summary>
      <pre style="
          background:#f7f7f7;
          padding:8px;
          border:1px solid #ddd;
          /* wrap long lines instead of horizontal scroll */
          white-space: pre-wrap;
          word-wrap: break-word;
          word-break: break-all;
          /* optional: limit height and allow scrolling */
          max-height: 300px;
          overflow: auto;
        ">
    {safe_payload}
      </pre>
    </details>
    """)

        if not html_chunks:
            return "No traceback available."

        return mark_safe("".join(html_chunks))

    traceback_pretty.short_description = "Traceback details"

    def _timestamp(self, obj):
        return obj.timestamp.strftime('%Y-%m-%d %H:%M')

    _timestamp.short_description = _('Timestamp')
    _timestamp.admin_order_field = 'timestamp'


@admin.register(TaskLogStatistics)
class TaskLogStatisticsAdmin(admin.ModelAdmin):
    """
    Admin for TaskLogStatistics with charts and statistics
    """
    model = TaskLogStatistics

    # Hide add/change functionality since this is for statistics only
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        from django.db.models import Count, Q
        from datetime import datetime, timedelta
        from django.conf import settings
        import json

        # Get data for the last N days based on CELERY_TASK_LOGS_EXPIRES setting
        days_to_show = settings.CELERY_TASK_LOGS_EXPIRES
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days_to_show)

        # Total messages per day
        messages_per_day = TaskLog.objects.filter(
            timestamp__date__gte=start_date,
            timestamp__date__lte=end_date
        ).extra(
            select={'day': 'date(timestamp)'}
        ).values('day').annotate(
            total=Count('id')
        ).order_by('day')

        # Failures per day
        failures_per_day = TaskLog.objects.filter(
            timestamp__date__gte=start_date,
            timestamp__date__lte=end_date,
            status=TaskLog.Status.FAILURE
        ).extra(
            select={'day': 'date(timestamp)'}
        ).values('day').annotate(
            failures=Count('id')
        ).order_by('day')

        # Success vs Failure totals
        success_failure_stats = TaskLog.objects.filter(
            timestamp__date__gte=start_date,
            timestamp__date__lte=end_date
        ).aggregate(
            total_success=Count('id', filter=Q(status=TaskLog.Status.SUCCESS)),
            total_failure=Count('id', filter=Q(status=TaskLog.Status.FAILURE))
        )

        # Top 10 queues with most messages
        top_queues = TaskLog.objects.filter(
            timestamp__date__gte=start_date,
            timestamp__date__lte=end_date
        ).values('queue_name').annotate(
            message_count=Count('id'),
            success_count=Count('id', filter=Q(status=TaskLog.Status.SUCCESS)),
            failure_count=Count('id', filter=Q(status=TaskLog.Status.FAILURE))
        ).order_by('-message_count')[:10]

        # Top 10 tasks with most executions
        top_tasks = TaskLog.objects.filter(
            timestamp__date__gte=start_date,
            timestamp__date__lte=end_date
        ).values('task_name').annotate(
            execution_count=Count('id'),
            success_count=Count('id', filter=Q(status=TaskLog.Status.SUCCESS)),
            failure_count=Count('id', filter=Q(status=TaskLog.Status.FAILURE)),
            success_rate=Count('id', filter=Q(status=TaskLog.Status.SUCCESS)) * 100.0 / Count('id')
        ).order_by('-execution_count')[:10]

        # Worker distribution
        worker_distribution = TaskLog.objects.filter(
            timestamp__date__gte=start_date,
            timestamp__date__lte=end_date
        ).values('worker').annotate(
            task_count=Count('id'),
            success_count=Count('id', filter=Q(status=TaskLog.Status.SUCCESS)),
            failure_count=Count('id', filter=Q(status=TaskLog.Status.FAILURE)),
            failure_rate=Count('id', filter=Q(status=TaskLog.Status.FAILURE)) * 100.0 / Count('id')
        ).order_by('-task_count')[:10]

        # Periodic task distribution
        periodic_task_distribution = TaskLog.objects.filter(
            timestamp__date__gte=start_date,
            timestamp__date__lte=end_date,
            periodic_task_name__isnull=False
        ).values('periodic_task_name').annotate(
            execution_count=Count('id'),
            success_count=Count('id', filter=Q(status=TaskLog.Status.SUCCESS)),
            failure_count=Count('id', filter=Q(status=TaskLog.Status.FAILURE))
        ).order_by('-execution_count')[:10]

        # Task error analysis - most common error messages
        error_analysis = TaskLog.objects.filter(
            timestamp__date__gte=start_date,
            timestamp__date__lte=end_date,
            status=TaskLog.Status.FAILURE,
            error_message__isnull=False
        ).exclude(error_message='').values('error_message').annotate(
            error_count=Count('id')
        ).order_by('-error_count')[:10]

        # Prepare chart data
        chart_data = {
            'messages_per_day': list(messages_per_day),
            'failures_per_day': list(failures_per_day),
            'success_failure_stats': success_failure_stats,
            'top_queues': list(top_queues),
            'top_tasks': list(top_tasks),
            'worker_distribution': list(worker_distribution),
            'periodic_task_distribution': list(periodic_task_distribution),
            'error_analysis': list(error_analysis),
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            }
        }

        extra_context = extra_context or {}
        extra_context['chart_data'] = json.dumps(chart_data, default=str)
        extra_context['days_to_show'] = days_to_show
        extra_context['statistics'] = {
            'total_messages': success_failure_stats['total_success'] + success_failure_stats['total_failure'],
            'total_success': success_failure_stats['total_success'],
            'total_failure': success_failure_stats['total_failure'],
            'success_rate': round(
                (success_failure_stats['total_success'] /
                 max(success_failure_stats['total_success'] + success_failure_stats['total_failure'], 1)) * 100, 2
            )
        }

        return super().changelist_view(request, extra_context=extra_context)
