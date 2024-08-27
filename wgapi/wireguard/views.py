from django.shortcuts import render
import json
import uuid
import os
from django.http import JsonResponse
from .management import add_peer, remove_peer, CommandStatus
from django.views.decorators.csrf import csrf_exempt
import requests
from rest_framework.decorators import api_view

@api_view(['POST'])
@csrf_exempt
def add_user(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
        subscription_id = uuid.UUID(data['subscription_id'])
        
        # Convert UUID to string for any subsequent operations that require slicing
        subscription_id_str = str(subscription_id)
        
        add_status, add_message = add_peer(subscription_id_str)
        if add_status == CommandStatus.OK:
            client_name = subscription_id_str[:8]
            config_file_path = f"/root/configs/awg0-client-{client_name}.conf"
            
            if os.path.exists(config_file_path):
                with open(config_file_path, 'r') as config_file:
                    config_content = config_file.read()

                # Return the configuration content without updating the subscription table entry
                return JsonResponse({'status': 'success', 'config_content': config_content})
            else:
                return JsonResponse({'status': 'error', 'message': 'Config file not found'}, status=400)
        else:
            return JsonResponse({'status': 'error', 'message': add_message}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@api_view(['POST'])
@csrf_exempt
def remove_user(request):
    """ Endpoint to remove an existing WireGuard user. """
    try:
        data = json.loads(request.body.decode('utf-8'))
        subscription_id = uuid.UUID(data['subscription_id'])

        subscription_id_str = str(subscription_id)
        client_name = subscription_id_str[:8]
        
        remove_status, error_msg = remove_peer(client_name)
        if remove_status == CommandStatus.OK:
            return JsonResponse({'status': 'success', 'message': 'User deleted successfully'})
        return JsonResponse({'status': 'error', 'message': f'Failed to delete user: {error_msg}'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@api_view(['POST'])
@csrf_exempt
def get_config(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
        subscription_id = uuid.UUID(data['subscription_id'])
        
        # Convert UUID to string and get the first 8 characters
        subscription_id_str = str(subscription_id)
        client_name = subscription_id_str[:8]
        
        # Construct the file path
        config_file_path = f"/root/configs/awg0-client-{client_name}.conf"
        
        # Check if the file exists and read its content
        if os.path.exists(config_file_path):
            with open(config_file_path, 'r') as config_file:
                config_content = config_file.read()
            return JsonResponse({'status': 'success', 'config_content': config_content})
        else:
            return JsonResponse({'status': 'error', 'message': 'Config file not found'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
