"""Shared kernel — building blocks reused across every bounded context.

Nothing in this package depends on a concrete bounded context. It contains the
generic domain and application primitives (entities, value objects, domain
events, command/query handlers, unit of work) that modules build upon.
"""
