"""
Context processors for matching_app.
Makes unread message count available globally across all templates for navbar badge notifications.
"""
from .models import Message


def unread_messages_processor(request):
    """Context processor that computes the number of unread messages for the logged-in user."""
    if request.user.is_authenticated:
        unread_count = Message.objects.filter(recipient=request.user, is_read=False, deleted_by_recipient=False).count()
        return {'unread_messages_count': unread_count}
    return {'unread_messages_count': 0}
