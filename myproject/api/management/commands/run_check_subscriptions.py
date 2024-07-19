from django.core.management.base import BaseCommand
from api.cron import CheckSubscriptionsCronJob

class Command(BaseCommand):
    help = 'Run CheckSubscriptionsCronJob manually'

    def handle(self, *args, **kwargs):
        job = CheckSubscriptionsCronJob()
        job.do()