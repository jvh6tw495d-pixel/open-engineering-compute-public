"""Ensures ``tests/`` is on sys.path so subpackages can `import _skill_helpers`.

Pytest's rootless import mode inserts each test file's own directory into
``sys.path`` — since this ``conftest.py`` lives directly in ``tests/``,
pytest also inserts ``tests/`` itself, making the sibling
``tests/_skill_helpers.py`` module importable from ``tests/unit/`` and
``tests/property/`` alike.
"""
