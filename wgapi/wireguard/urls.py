from django.urls import path, include
from .views import add_user, remove_user, get_config

urlpatterns = [
    path('add_user/', add_user, name='add_user'),
    path('remove_user/', remove_user, name='remove_user'),
    path('get_config/', get_config, name='get_config'),
]
    