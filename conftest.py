"""Pytest bootstrap.

Ensures the project root is importable and that the project's ``sitecustomize``
(which carries runtime hotfixes) is the module returned by ``import
sitecustomize`` — on some hosts (e.g. Debian/Ubuntu) an empty system
``sitecustomize`` stub is auto-imported at interpreter startup and would
otherwise shadow ours, breaking the hotfix tests and the live grant delivery
they cover.
"""
import importlib
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

_existing = sys.modules.get("sitecustomize")
_existing_file = getattr(_existing, "__file__", "") or ""
if os.path.dirname(os.path.abspath(_existing_file)) != PROJECT_ROOT:
    sys.modules.pop("sitecustomize", None)
    importlib.import_module("sitecustomize")
