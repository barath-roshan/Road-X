"""Centralized notification templates for RoadX events."""

from __future__ import annotations

from typing import Dict, Tuple
from backend.models.notification import NotificationType


def render_notification_template(
    notification_type: NotificationType,
    context: Dict[str, str],
) -> Tuple[str, str]:
    """
    Render (title, message) tuple for a given notification type and context variables.
    Context variables may include: grievance_id, work_order_id, road_name, reason, progress_percentage, operation_title.
    """
    g_ref = context.get("grievance_id", "N/A")
    w_ref = context.get("work_order_id", "N/A")
    road_ref = context.get("road_name", "your area road")
    reason = context.get("reason", "")
    op_title = context.get("operation_title", "Road Operation")

    if notification_type == NotificationType.GRIEVANCE_ACCEPTED:
        title = "Grievance Accepted"
        msg = f"Your road complaint #{g_ref} for {road_ref} has been reviewed and accepted by government officers."
        return title, msg

    elif notification_type == NotificationType.GRIEVANCE_REJECTED:
        title = "Grievance Review Update"
        reason_str = f" Reason: {reason}" if reason else ""
        msg = f"Your road complaint #{g_ref} for {road_ref} was reviewed.{reason_str}"
        return title, msg

    elif notification_type == NotificationType.WORK_ORDER_ASSIGNED:
        title = "New Work Order Assigned"
        msg = f"Work Order #{w_ref} for grievance #{g_ref} on {road_ref} has been assigned to you."
        return title, msg

    elif notification_type == NotificationType.WORK_STARTED:
        title = "Maintenance Work Started"
        msg = f"Maintenance repair work has started on {road_ref} for complaint #{g_ref}."
        return title, msg

    elif notification_type == NotificationType.WORK_PROGRESS_UPDATED:
        progress = context.get("progress_percentage", "0")
        title = "Maintenance Work Progress"
        msg = f"Repair work progress for complaint #{g_ref} on {road_ref} is now at {progress}%."
        return title, msg

    elif notification_type == NotificationType.WORK_VERIFICATION_SUBMITTED:
        title = "Work Verification Needed"
        msg = f"Contractor submitted completion for Work Order #{w_ref} (Grievance #{g_ref}). Verification required."
        return title, msg

    elif notification_type == NotificationType.WORK_VERIFICATION_APPROVED:
        title = "Grievance Resolved"
        msg = f"Great news! Your road complaint #{g_ref} for {road_ref} has been verified and officially RESOLVED."
        return title, msg

    elif notification_type == NotificationType.WORK_VERIFICATION_REJECTED:
        title = "Work Rework Requested"
        reason_str = f" Reason: {reason}" if reason else ""
        msg = f"Government verification requested rework for Work Order #{w_ref} (Grievance #{g_ref}).{reason_str}"
        return title, msg

    elif notification_type == NotificationType.ROAD_OPERATION_ACTIVATED:
        title = f"Road Operation Active: {op_title}"
        reason_str = f" Reason: {reason}" if reason else ""
        msg = f"Notice: Active road operation/closure on {road_ref}.{reason_str}"
        return title, msg

    elif notification_type == NotificationType.ROAD_OPERATION_COMPLETED:
        title = f"Road Operation Completed: {op_title}"
        msg = f"Notice: Road operation on {road_ref} has completed. Normal traffic restored."
        return title, msg

    elif notification_type == NotificationType.ROAD_OPERATION_CANCELLED:
        title = f"Road Operation Cancelled: {op_title}"
        msg = f"Notice: Planned road operation on {road_ref} has been cancelled."
        return title, msg

    title = "RoadX System Update"
    msg = f"Update regarding road activity on {road_ref} (Ref: #{g_ref})."
    return title, msg
