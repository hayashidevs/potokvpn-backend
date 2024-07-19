from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import clientViewSet, rateViewSet, subscriptionViewSet, get_expiring_subscriptions, update_subscription, delete_subscription, apply_referral, client_list, SubscriptionDetail, update_subscription_dateend
router = DefaultRouter()
router.register(r'clients', clientViewSet)
router.register(r'rates', rateViewSet)
router.register(r'subscriptions', subscriptionViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('expiring_subscriptions/', get_expiring_subscriptions, name='expiring_subscriptions'),
    path('update_subscription/', update_subscription, name='update_subscription'),
    path('delete_subscription/<int:subscription_id>/', delete_subscription, name='delete_subscription'),
    path('apply_referral/', apply_referral, name='apply_referral'),
    path('client_list/', client_list, name='client_list'),
    path('api/subscription/by-client-id/<str:client_id>/', SubscriptionDetail.as_view(), name='subscription-by-client-id'),
    path('update_subscription_dateend/', update_subscription_dateend, name='update_subscription_dateend'),
]
