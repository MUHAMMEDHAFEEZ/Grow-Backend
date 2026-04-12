"""
grow/schema_hooks.py — drf-spectacular preprocessing hooks.
"""

# Path prefixes that belong to legacy apps and should be excluded from the API schema
_EXCLUDED_PREFIXES = ("/accounts/", "/students/", "/schools/")


def exclude_legacy_paths(endpoints, **kwargs):
    """
    Remove legacy URL paths (not under /api/v1/) from the generated schema.
    This keeps the Swagger docs focused on the v1 API surface only.
    """
    return [
        (path, path_regex, method, callback)
        for path, path_regex, method, callback in endpoints
        if not any(path.startswith(prefix) for prefix in _EXCLUDED_PREFIXES)
    ]
