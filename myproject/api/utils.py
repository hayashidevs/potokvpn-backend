import requests
from django.shortcuts import render

def custom_lockout_response(request, credentials, *args, **kwargs):
    return render(request, 'account_locked.html', status=403)