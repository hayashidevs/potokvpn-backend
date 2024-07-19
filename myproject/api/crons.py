import datetime
import requests
from django_cron import CronJobBase, Schedule
from django.conf import settings
from .models import subscription
import logging
from django.utils import timezone 

logger = logging.getLogger(__name__)

class CheckSubscriptionsCronJob(CronJobBase):
    RUN_AT_TIMES = ['23:50']  # Runs daily at 23:50

    schedule = Schedule(run_at_times=RUN_AT_TIMES)
    code = 'api.check_subscriptions_cron_job'  # Unique code for the job

    def do(self):
        today = timezone.localtime(timezone.now()).date()  # Use timezone-aware date
        # Retrieve subscriptions that end today or have already ended
        subscriptions = subscription.objects.filter(dateend__date__lte=today)

        for sub in subscriptions:
            logger.info(f"Processing subscription {sub.id}")
            response = requests.post(
                'http://v1632382.hosted-by-vdsina.ru:8000/wireguard/remove_user/',  # Replace with actual endpoint
                json={'subscription_id': str(sub.id)}
            )
            logger.info(f"Response status: {response.status_code}, Response data: {response.json()}")

            if response.status_code == 200 and response.json().get('status') == 'success':
                sub.delete()
                logger.info(f"Subscription {sub.id} deleted")
            else:
                logger.error(f"Failed to delete subscription {sub.id}")

        # Additional check to ensure expired subscriptions are deleted from the database
        remaining_subscriptions = subscription.objects.filter(dateend__date__lte=today)
        for sub in remaining_subscriptions:
            logger.warning(f"Subscription {sub.id} was not deleted remotely. Attempting to delete from database.")
            sub.delete()
            logger.info(f"Subscription {sub.id} deleted from database")

class ResetSubscriptionUsageCronJob(CronJobBase):
    RUN_AT_TIMES = ['22:00']

    schedule = Schedule(run_at_times=RUN_AT_TIMES)
    code = 'api.reset_subscription_usage_cron_job'  # a unique code

    def do(self):
        try:
            subscriptions = subscription.objects.filter(is_used=True)
            subscriptions.update(is_used=False)
            print(f"Reset is_used field for {subscriptions.count()} subscriptions.")
        except Exception as e:
            print(f"Error in ResetSubscriptionUsageCronJob: {e}")