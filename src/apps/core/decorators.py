import functools
import inspect
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


def timer(func: Any) -> Any:
    """Print the runtime of the decorated function"""

    @functools.wraps(func)
    def wrapper_timer(*args, **kwargs):
        try:
            is_method = inspect.getfullargspec(func)[0][0] == 'self'
        except IndexError:
            is_method = False

        if is_method:
            name = f'{repr(args[0])}.{func.__name__}'
        else:
            name = func.__name__

        logger.debug(f"Task: {name} - Started")
        start_time = time.perf_counter()
        value = func(*args, **kwargs)
        end_time = time.perf_counter()
        run_time = end_time - start_time
        minutes = 0
        seconds = run_time
        if run_time > 60:
            minutes = int(seconds / 60)
            seconds = int(seconds % 60)

        msg = f"Task: {name} - Finished in "
        if minutes:
            msg += f"{round(minutes)} min and "
        logger.debug(msg + f"{seconds:.2f} secs")
        return value

    return wrapper_timer
