from celery import shared_task
from django.utils.timezone import now
from datetime import timedelta
from .models import subscription
from .utils import send_remove_peer_request, send_delete_config_request

@shared_task
def check_subscriptions():
    current_time = now()
    three_days_ago = current_time - timedelta(days=3)

    expired_subscriptions = subscription.objects.filter(dateend__lt=current_time)
    for sub in expired_subscriptions:
        send_remove_peer_request(sub.public_key)

    expired_configs = subscription.objects.filter(dateend__lt=three_days_ago)
    for sub in expired_configs:
        send_delete_config_request(sub.config_name)
        sub.delete()
