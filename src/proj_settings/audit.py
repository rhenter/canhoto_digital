import json, logging, time
from django.utils.deprecation import MiddlewareMixin
logger = logging.getLogger("audit")

class AuditLogMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request._start_time = time.time()

    def process_response(self, request, response):
        try:
            duration = None
            if hasattr(request, "_start_time"):
                duration = round((time.time() - request._start_time) * 1000, 1)
            user = getattr(request, "user", None)
            data = {
                "path": request.path,
                "method": request.method,
                "status": getattr(response, "status_code", None),
                "duration_ms": duration,
                "user": getattr(user, "username", None) if user and user.is_authenticated else None,
                "ip": request.META.get("REMOTE_ADDR"),
            }
            logger.info(json.dumps(data))
        except Exception:
            pass
        return response
