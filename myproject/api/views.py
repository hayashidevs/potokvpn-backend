from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse, FileResponse, Http404
from django.conf import settings
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from rest_framework import viewsets
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics
from rest_framework.exceptions import NotFound

from .models import client, rate, subscription, codes
from .serializers import clientSerializer, rateSerializer, subscriptionSerializer, codesSerializer

import json
from datetime import timedelta

import logging
import os
import requests


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CodesViewSet(viewsets.ModelViewSet):
    queryset = codes.objects.all()
    serializer_class = codesSerializer

class clientViewSet(viewsets.ModelViewSet):
    queryset = client.objects.all()
    serializer_class = clientSerializer

    @action(detail=True, methods=['patch'])
    def update_referred_by(self, request, pk=None):
        try:
            client_instance = self.get_object()
        except client.DoesNotExist:
            return Response({'status': 'client not found'}, status=status.HTTP_404_NOT_FOUND)

        referred_by_id = request.data.get('referred_by')
        if not referred_by_id:
            return Response({'status': 'no referred_by provided'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            referred_by_client = client.objects.get(pk=referred_by_id)
        except client.DoesNotExist:
            return Response({'status': 'referred_by client not found'}, status=status.HTTP_404_NOT_FOUND)

        client_instance.referred_by = referred_by_client
        client_instance.save()
        return Response({'status': 'referred_by updated'}, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['patch'], url_path='update_by_username')
    def update_client_by_username(self, request):
        username = request.data.get('username')
        if not username:
            return Response({'status': 'username not provided'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            client_instance = client.objects.get(username=username)
        except client.DoesNotExist:
            return Response({'status': 'client not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(client_instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class rateViewSet(viewsets.ModelViewSet):
    queryset = rate.objects.all()
    serializer_class = rateSerializer

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        print(response.data)  # Add logging to check response data
        return response
    def get_queryset(self):
        name = self.request.query_params.get('name', None)
        if name:
            rates = self.queryset.filter(name=name)
            logger.debug(f"Rates fetched for name {name}: {rates}")
            return rates
        rates = self.queryset
        logger.debug(f"All rates fetched: {rates}")
        return rates


class subscriptionViewSet(viewsets.ModelViewSet):
    queryset = subscription.objects.all()
    serializer_class = subscriptionSerializer


@csrf_exempt
def register_client(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        client, created = client.objects.get_or_create(
            telegramid=data['telegramid'],
            defaults={'username': data['username'], 'referral_id': data['referral_id']}
        )
        return JsonResponse({'success': True, 'created': created})
    return JsonResponse({'success': False}, status=400)


def get_expiring_subscriptions(request):
    # Чекаем текущее время
    current_time = timezone.now()
    # Определяет временное окно для проверки истекающих подписок
    time_threshold = current_time + timedelta(days=4)  # Заблаговременно, чтобы справиться с любыми задержками или проблемами сети.
    expiring_subs = subscription.objects.filter(dateend__lte=time_threshold)
    data = [{'subscription_id': sub.id, 'dateend': sub.dateend} for sub in expiring_subs]
    return JsonResponse(data, safe=False)


@api_view(['POST'])
def update_subscription(request):
    subscription_id = request.data.get('subscription_id')
    config_name = request.data.get('config_name')

    try:
        subscription_instance = subscription.objects.get(id=subscription_id)
        subscription_instance.config_name = config_name
        subscription_instance.save()
        return Response({'status': 'success', 'message': 'Subscription updated successfully'})
    except subscription.DoesNotExist:
        return Response({'status': 'error', 'message': 'Subscription not found'}, status=404)

@api_view(['POST'])
def update_subscription_dateend(request):
    subscription_id = request.data.get('subscription_id')
    dateend_update = request.data.get('dateend')

    try:
        subscription_instance = subscription.objects.get(id=subscription_id)
        subscription_instance.dateend= dateend_update
        subscription_instance.save()
        return Response({'status': 'success', 'message': 'Subscription updated successfully'})
    except subscription.DoesNotExist:
        return Response({'status': 'error', 'message': 'Subscription not found'}, status=404)

@api_view(['DELETE'])
def delete_subscription(request, subscription_id):
    try:
        subscription = subscription.objects.get(id=subscription_id)
        subscription.delete()
        return Response({'status': 'success', 'message': 'Subscription deleted successfully'})
    except subscription.DoesNotExist:
        return Response({'status': 'error', 'message': 'Subscription not found'}, status=status.HTTP_404_NOT_FOUND)
    
@csrf_exempt
def apply_referral(request):
    if request.method == 'POST':
        data = request.JSON()
        client_id = data.get('client_id')
        referral_id = data.get('referral_id')
        try:
            referring_client = client.objects.get(referral_id=referral_id)
            current_client = client.objects.get(id=client_id)
            current_client.referred_by = referring_client
            current_client.save()
            return JsonResponse({'success': True, 'message': 'Referral code applied successfully.'})
        except client.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Client or referral not found.'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

@csrf_exempt
def client_list(request):
    if request.method == 'GET':
        telegram_id = request.GET.get('telegramid')
        if telegram_id:
            client_obj = client.objects.filter(telegramid=telegram_id).first()
            if client_obj:
                return JsonResponse({'success': True, 'exists': True, 'client': client_obj.to_dict()}, safe=False)
            else:
                return JsonResponse({'success': True, 'exists': False}, status=200)
        else:
            return JsonResponse({'success': False, 'message': 'Telegram ID not provided'}, status=400)

    elif request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        telegram_id = data.get('telegramid')
        username = data.get('username')
        first_name = data.get('firstname', '')
        last_name = data.get('lastname', '')
        client_obj, created = client.objects.get_or_create(
            telegramid=telegram_id,
            defaults={
                'username': username,
                'firstname': first_name,
                'lastname': last_name
            }
        )
        if created:
            return JsonResponse({'success': True, 'message': 'Client created successfully', 'client_id': client_obj.id}, status=201)
        else:
            return JsonResponse({'success': True, 'message': 'Client already exists', 'client_id': client_obj.id}, status=200)

    return JsonResponse({'success': False, 'message': 'Invalid HTTP method'}, status=405)


class SubscriptionDetail(generics.RetrieveAPIView):
    serializer_class = subscriptionSerializer

    def get_queryset(self):
        """
        Optionally restricts the returned purchases to a given user,
        by filtering against a `clientid` query parameter in the URL.
        """
        queryset = subscription.objects.all()
        clientid = self.kwargs.get('clientid')
        if clientid is not None:
            queryset = queryset.filter(clientid=clientid)
        return queryset

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        obj = queryset.first()
        if obj is None:
            raise NotFound('A subscription with this client ID does not exist.')
        return obj

