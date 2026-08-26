#!/usr/bin/env python3
"""Fail before any pack rebuild unless the local neural-training environment works."""
import importlib, sys

if sys.prefix == sys.base_prefix:
    raise SystemExit("Use clink-index/clink-language-packs/.venv/bin/python3; system Python is not permitted for neural training.")
for name in ("torch", "coremltools"):
    try:
        module = importlib.import_module(name)
    except ImportError as error:
        raise SystemExit(f"Missing {name}. Run: .venv/bin/python3 -m pip install -r requirements-train.txt") from error
    print(f"{name} {module.__version__}")
print(f"training interpreter: {sys.executable}")
