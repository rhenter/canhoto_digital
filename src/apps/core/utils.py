import json
import os
import pickle
from base64 import b64encode
from collections import deque
from copy import deepcopy
from gzip import compress
from typing import Any, Dict, List, Tuple, Callable, Optional

from django.contrib.admin.models import LogEntry, ADDITION, CHANGE, DELETION
from django.contrib.contenttypes.models import ContentType
from django.core.cache import caches

Node = Dict[str, Any]
Path = str


def bfs_search(
    roots: List[Node],
    key: str,
    search: Any = None,
    *,
    predicate: Optional[Callable[[Any], bool]] = None,
    first_only: bool = True,
    return_paths: bool = False,
) -> Node | List[Tuple[Node, Path]]:
    """
    Breadth-first search through a list of tree nodes (each node may contain
    'children': List[Dict]) and return all nodes where node[key] matches
    `search` (or satisfies `predicate`).

    Parameters
    ----------
    roots : list of dict
        Root nodes of the tree.
    key : str
        Key to check in each node.
    search : Any, optional
        Value to compare against. Ignored if `predicate` is given.
    predicate : callable, optional
        Function bool(val) used for custom matching logic.
    first_only : bool, default False
        If True, stop at the first match.
    return_paths : bool, default True
        If True, return (node, path) tuples where a path is like
        '$[0].children[2].children[5]'.

    Returns
    -------
        List of nodes (or tuples (node, path) if return_paths=True).
    """
    def _match(val: Any) -> bool:
        if predicate is not None:
            return predicate(val)
        return val == search

    results: List[Node | Tuple[Node, Path]] = []
    queue: deque[Tuple[Node, Path]] = deque((n, f"$[{i}]") for i, n in enumerate(roots))

    while queue:
        node, path = queue.popleft()

        if key in node and _match(node[key]):
            results.append((node, path) if return_paths else node)
            if first_only:
                return results[0]

        children = node.get("children")
        if isinstance(children, list):
            for j, child in enumerate(children):
                if isinstance(child, dict):
                    queue.append((child, f"{path}.children[{j}]"))
    return results


def dbsafe_encode(value, compress_object=False, copy=True):
    # We use deepcopy() here to avoid a problem with cPickle, where dumps
    # can generate different character streams for same lookup value if
    # they are referenced differently.
    # The reason this is important is because we do all of our lookups as
    # simple string matches, thus the character streams must be the same
    # for the lookups to work properly. See tests.py for more information.
    if copy:
        # Copy can be very expensive if users aren't going to perform lookups
        # on the value anyway.
        value = deepcopy(value)
    value = pickle.dumps(value, protocol=2)
    if compress_object:
        value = compress(value)
    value = b64encode(value).decode()
    return value


def clear_custom_cache(patterns):
    cache = caches["default"]

    if isinstance(patterns, str):
        patterns = [patterns]

    for pattern in patterns:
        delete_pattern = getattr(cache, "delete_pattern", None)
        if callable(delete_pattern):
            delete_pattern(pattern)
            continue

        keys_fn = getattr(cache, "keys", None)
        if callable(keys_fn):
            keys = keys_fn(pattern)
            if keys:
                cache.delete_many(keys)


def add_logentry(user: Any, obj: Any, action: str, fields_changed: List[str] = None) -> LogEntry:
    if not fields_changed:
        fields_changed = []

    if action == 'creation':
        action_flag = ADDITION
        change_message = [{"added": {}, "origin": "API DRF"}]
    elif action == 'update':
        action_flag = CHANGE
        change_message = [{"changed": {"fields": [fields_changed]}, "origin": "API DRF"}]
    else:
        action_flag = DELETION
        change_message = [{"deleted": {}, "origin": "API DRF"}]

    return LogEntry.objects.log_action(
        user_id=user.pk,
        content_type_id=ContentType.objects.get_for_model(obj).pk,
        object_id=obj.pk,
        object_repr=str(obj),
        action_flag=action_flag,
        change_message=change_message
    )


def dump_json_to_folder(data, folder_path, filename):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    file_path = os.path.join(folder_path, filename)

    json_string = json.dumps(data, indent=2, default=str)

    with open(file_path, 'w') as file:
        file.write(json_string)
