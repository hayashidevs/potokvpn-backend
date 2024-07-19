from django.contrib import admin
import json
import uuid
import requests
import logging
from django.urls import path, re_path, reverse
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.html import format_html
from .models import client, rate, subscription

logger = logging.getLogger(__name__)

class subscriptionInline(admin.TabularInline):
    model = subscription
    extra = 0
    fields = ('id', 'rateid', 'rate_name_display', 'name', 'datestart', 'dateend', 'add_user_button', 'view_subscription_link')
    readonly_fields = ('id', 'rate_name_display', 'add_user_button', 'view_subscription_link')

    def add_user_button(self, obj):
        return format_html(
            '<button type="button" class="button" onclick="addUser(\'{}\')">Выдать конфиг</button>',
            obj.id
        )
    add_user_button.short_description = 'Выдать конфиг'
    add_user_button.allow_tags = True

    def rate_name_display(self, instance):
        return instance.rateid.name
    rate_name_display.short_description = 'Название тарифа'

    def view_subscription_link(self, obj):
        url = reverse('admin:api_subscription_change', args=[obj.id])
        return format_html('<a href="{}">Перейти к подписке</a>', url)
    view_subscription_link.short_description = 'Перейти к подписке'

class clientAdmin(admin.ModelAdmin):
    list_display = ('username', 'firstname', 'telegramid', 'get_first_subscription', 'get_subscription_count', 'id', 'get_referred_by_username')
    search_fields = ('username', 'firstname', 'telegramid', 'id')
    readonly_fields = ('id',)
    list_filter = ('username', 'id', 'referred_by__username', 'UsedTestSubscription')
    inlines = [subscriptionInline]
    change_form_template = 'admin/client_change_form.html'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            re_path(r'^add-user/(?P<subscription_id>[0-9a-f-]+)/$', self.admin_site.admin_view(self.add_user_view), name='add-user'),
        ]
        return custom_urls + urls

    def add_user_view(self, request, subscription_id):
        subscription_obj = get_object_or_404(subscription, pk=subscription_id)
        if not subscription_obj:
            self.message_user(request, "Subscription not found.", level='error')
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

        logger.info(f"Processing Add User for Subscription ID: {subscription_id}")

        try:
            response = requests.post(
                'http://v1632382.hosted-by-vdsina.ru:8000/wireguard/add_user/',
                json={'subscription_id': str(subscription_obj.id)},
                headers={'Content-Type': 'application/json'}
            )
            logger.info(f"Response Status Code: {response.status_code}")
            logger.info(f"Response Content: {response.content}")
            response_data = response.json()
            if response_data.get('status') == 'success':
                self.message_user(request, "User added successfully. Config: " + response_data.get('config_content'), level='success')
            else:
                self.message_user(request, "Error: " + response_data.get('message'), level='error')
        except Exception as e:
            logger.error(f"Exception occurred: {str(e)}")
            self.message_user(request, "Exception: " + str(e), level='error')

        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

    def get_first_subscription(self, obj):
        first_subscription = obj.subscriptions.first()
        if first_subscription and first_subscription.rateid:
            return f'{first_subscription.id} - {first_subscription.rateid.name}'
        return 'Нет подписок'
    get_first_subscription.short_description = 'Первая подписка'

    def get_subscription_count(self, obj):
        return obj.subscriptions.count()
    get_subscription_count.short_description = 'Количество подписок'

    def get_referred_by_username(self, obj):
        return obj.referred_by.username if obj.referred_by else None
    get_referred_by_username.short_description = 'Относящийся к'
    get_referred_by_username.admin_order_field = 'referred_by__username'

class rateAdmin(admin.ModelAdmin):
    list_display = ('name', 'id', 'dayamount')
    search_fields = ('name', 'dayamount')
    list_filter = ('dayamount', 'price')
    readonly_fields = ('id',)

class subscriptionAdmin(admin.ModelAdmin):
    list_display = ('get_client_username', 'get_client_firstname', 'get_rate_name', 'name', 'datestart', 'dateend', 'add_user_button')
    search_fields = ('client__username', 'rate__name')
    list_filter = ('clientid__username', 'rateid__name', 'datestart', 'dateend')
    change_list_template = 'admin/subscription_change_list.html'
    change_form_template = 'admin/subscription_change_form.html'
    readonly_fields = ('id',)

    def add_user_button(self, obj):
        return format_html(
            '<button type="button" class="button" onclick="addUser(\'{}\')">Выдать конфиг</button>',
            obj.id
        )
    add_user_button.short_description = 'Выдать конфиг'
    add_user_button.allow_tags = True

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            re_path(r'add-user/(?P<subscription_id>[0-9a-f-]+)/$', self.admin_site.admin_view(self.add_user_view), name='add-user'),
        ]
        return custom_urls + urls

    def add_user_view(self, request, subscription_id):
        subscription_obj = get_object_or_404(subscription, pk=subscription_id)
        if not subscription_obj:
            self.message_user(request, "Subscription not found.", level='error')
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

        logger.info(f"Processing Add User for Subscription ID: {subscription_id}")

        try:
            response = requests.post(
                'http://v1632382.hosted-by-vdsina.ru:8000/wireguard/add_user/',
                json={'subscription_id': str(subscription_obj.id)},
                headers={'Content-Type': 'application/json'}
            )
            logger.info(f"Response Status Code: {response.status_code}")
            logger.info(f"Response Content: {response.content}")
            response_data = response.json()
            if response_data.get('status') == 'success':
                self.message_user(request, "User added successfully. Config: " + response_data.get('config_content'), level='success')
            else:
                self.message_user(request, "Error: " + response_data.get('message'), level='error')
        except Exception as e:
            logger.error(f"Exception occurred: {str(e)}")
            self.message_user(request, "Exception: " + str(e), level='error')

        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

    def get_client_username(self, obj):
        return obj.clientid.username
    get_client_username.short_description = 'Юзернейм'
    get_client_username.admin_order_field = 'client__username'

    def get_client_firstname(self, obj):
        return obj.clientid.firstname
    get_client_firstname.short_description = 'Имя'
    get_client_firstname.admin_order_field = 'client__firstname'

    def get_rate_name(self, obj):
        return obj.rateid.name
    get_rate_name.short_description = 'Название тарифа'
    get_rate_name.admin_order_field = 'rate__name'

admin.site.register(client, clientAdmin)
admin.site.register(rate, rateAdmin)
admin.site.register(subscription, subscriptionAdmin)
