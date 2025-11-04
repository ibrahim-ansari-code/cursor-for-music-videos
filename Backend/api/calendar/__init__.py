"""
Calendar API Module

Provides unified calendar view of events from multiple sources:
- Invoices (due dates)
- Leases (start/end dates)
- Maintenance (scheduled dates)
- Properties (insurance/mortgage expiries)
- Custom Reminders (user-created)

Uses virtual calendar approach - events computed on-demand from source tables.
"""

