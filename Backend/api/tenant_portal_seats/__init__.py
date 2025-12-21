"""
Tenant Portal Seats API

Handles seat-based licensing for the tenant portal using GitHub-style architecture:
- Real-time seat counting (no drift-prone counters)
- Single source of truth (tenant.user_id IS NOT NULL)
- Enforcement at invitation acceptance, not creation
"""
