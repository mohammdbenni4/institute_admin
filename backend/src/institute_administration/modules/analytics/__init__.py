"""Analytics bounded context.

Read-only reporting over the existing tables (no schema of its own): institute
overview KPIs, per-halaqah student leaderboards, and an at-risk watch-list. All
aggregation runs over a single indexed ``record_date`` window per request.
"""
