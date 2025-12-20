ui_data_contract.md
1. Feature Summary

The Notifications System provides a centralized, asynchronous mechanism to inform users about onboarding and workflow events through email-first delivery and limited in-app notifications. It ensures users remain informed without blocking core business processes, while maintaining strict company scoping and predictable notification behavior.

2. Screens Covered
- SCR_NOTIFICATION_INBOX

3. Data Requirements Per Screen
3.1 Screen ID
SCR_NOTIFICATION_INBOX
Route: /notifications

3.2 Reads (Server Data Required)
Reads:
- Notification:
    fields:
      - id
      - type
      - title
      - message
      - channel
      - is_read
      - read_at
      - related_record_id
      - related_table
      - created_at


Only in-app notifications (task and leave types) are returned to this screen.
Invitation notifications are email-only and excluded.

3.3 Writes (Actions / Mutations)
Writes:
- mark_notification_read

3.4 Query Parameters
Query Parameters:
- is_read
- type
- page
- page_size
- sort_by
- sort_order

3.5 Derived or Aggregated Fields
Derived Fields:
- is_unread (boolean)          // inverse of is_read
- notification_age_label      // e.g. "2h ago", "Yesterday"


Derived purely for UI rendering convenience.

3.6 UI Data Constraints

Server-side pagination required

Notifications are strictly company-scoped

Users may receive notifications they cannot act on due to RBAC

UI must rely on RBAC checks when navigating to related records

In-app notifications are read-only (no edit/delete)

4. Proposed API Hints (Not Final API Spec)
Proposed API Hints:
- GET   /api/v1/notifications
- PATCH /api/v1/notifications/{id}/read

5. Cross-Screen Data Dependencies
SCR_NOTIFICATION_INBOX depends on:
- RBAC permission evaluation (F-002) for navigation to related records

F-000 (Auth) provides:
- Authenticated user context

F-008 (Task Management) and F-009 (Leave Management) provide:
- Target screens for related_record navigation

6. Data Edge Cases

Empty notification inbox

Notifications referencing deleted or inaccessible records

User receives notification but lacks permission to view related entity

Deactivated users may still have unread notifications

In-app notification creation failure (screen remains unaffected)

Mixed channel notifications (email + in-app vs email-only)