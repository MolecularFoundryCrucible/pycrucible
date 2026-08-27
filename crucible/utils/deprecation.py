#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API lifecycle decorators — mark methods as deprecated or removed.
"""

import warnings
import functools


def _deprecated(new_api: str):
    """Decorator that emits a DeprecationWarning pointing to the new API."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            warnings.warn(
                f"{func.__name__}() is deprecated; use {new_api} instead.",
                DeprecationWarning,
                stacklevel=2,
            )
            return func(*args, **kwargs)
        return wrapper
    return decorator


def _deprecated_parameter(old_name: str, new_name: str):
    """Map a deprecated keyword to its replacement while preserving positional calls."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if old_name in kwargs:
                if new_name in kwargs:
                    raise TypeError(
                        f"Pass either '{new_name}' or deprecated '{old_name}', not both."
                    )
                warnings.warn(
                    f"The '{old_name}' keyword is deprecated; use '{new_name}' instead.",
                    DeprecationWarning,
                    stacklevel=2,
                )
                kwargs[new_name] = kwargs.pop(old_name)
            return func(*args, **kwargs)
        return wrapper
    return decorator


def _removed(reason: str):
    """Decorator that raises NotImplementedError for methods removed from the API."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            raise NotImplementedError(
                f"{func.__name__}() has been removed and is no longer available. {reason}"
            )
        return wrapper
    return decorator
