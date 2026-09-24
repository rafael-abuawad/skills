"""Add Hypothesis strategies using compiler ABI and source-level Vyper bounds.

Use integers for exact contract arithmetic. Bound Bytes[N], String[N], DynArray
and nested arrays from source/compiler metadata; fail on unknown bounds/types.
Select actors and existing entity IDs from current example state. Include zero,
limits, permission boundaries, and meaningful valid inputs; avoid broad assume().
"""
