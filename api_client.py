import os
import requests
import config
import aiohttp
import datetime
from datetime import datetime, timedelta
import logging
import yaml
from utils import setup_logging, log

# Load additional config if needed
'''config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.yaml')
with open(config_path, 'r') as file:
    config = yaml.safe_load(file)

# Load paths from config.yaml
data_dir = config['data_storage']['data_directory']
logs_dir = config['data_storage']['logs_directory']
log_filename = config['data_storage']['log_filename']'''


def handle_response(response):
    if response.status_code in [200, 201]:
        return True, response.json()
    else:
        return False, response.text


async def check_user_registration(telegram_id):
    async with aiohttp.ClientSession() as session:
        url = f"{config.DJANGO_API_URL}/api/client_list/"
        params = {'telegramid': str(telegram_id)}
        async with session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                # Assuming data could be a list and checking the first item if it's not empty
                if isinstance(data, list) and data:
                    data = data[0]
                # Check if the list is not empty and the 'exists' key is True
                exists = data.get('exists', False) if isinstance(data, dict) else False
                return True, exists
            else:
                return False, False
            

async def get_uniqe_codes_and_update(unique_code):
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{config.DJANGO_API_URL}/api/codes/"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Debug log to check fetched codes
                    print(f"Fetched unique codes: {data}")
                    
                    # Iterate over codes to check for a match with the user-provided unique_code
                    for code_entry in data:
                        if code_entry['code'] == unique_code and not code_entry['used_code']:
                            # Mark the code as used by sending a PATCH request
                            id_unique_code = code_entry['id']
                            update_url = f"{config.DJANGO_API_URL}/api/codes/{id_unique_code}/"
                            update_data = {'used_code': True}
                            async with session.patch(update_url, json=update_data) as patch_response:
                                if patch_response.status == 200:
                                    print(f"Code '{unique_code}' marked as used.")
                                    return True
                                else:
                                    # Log the error if updating fails
                                    print(f"Failed to update code '{unique_code}' with ID {id_unique_code}: {patch_response.status}")
                                    return False
                    # Log if no matching unused code is found
                    print(f"No matching unused code found for '{unique_code}'")
                    return False
                else:
                    # Log if initial request to fetch codes fails
                    print(f"Failed to fetch codes: {response.status}")
                    return False
    except Exception as e:
        # General exception logging
        print(f"Exception in get_uniqe_codes_and_update: {e}")
        return False


async def get_referral_id_by_telegram_id(telegram_id):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{config.DJANGO_API_URL}/api/clients/",
                                   params={'telegramid': telegram_id}) as response:
                if response.status != 200:
                    print(f"Failed to get clients: {response.status}")
                    return None

                clients = await response.json()
                print(f"Clients response: {clients}")
                if not clients:
                    print("No clients found")
                    return None

                for client in clients:
                    if client['telegramid'] == telegram_id:
                        return client['referral_id']

                print("No matching client found for the given Telegram ID")
                log("No matching client found for the given Telegram ID: ", client)
                return None
    except Exception as e:
        print(f"API request error: {str(e)}")
        return None
    

async def get_subscription_count_by_telegram_id(telegram_id):
    """Получить количество подписок клиента по его telegram_id."""
    try:
        client_id = await get_client_id_from_telegram_id(telegram_id)
        if not client_id:
            log("No valid client ID found for the given Telegram ID.: ", client_id)
            return "No valid client ID found for the given Telegram ID."

        async with aiohttp.ClientSession() as session:
            url = f"{config.DJANGO_API_URL}/api/subscriptions/"
            params = {'clientid': client_id}
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    print(f"Failed to get subscriptions: {response.status}")
                    log(f"Failed to get subscriptions: {response.status}")
                    return f"Failed to get subscriptions with status {response.status}: {await response.text()}"

                subscriptions = await response.json()
                subscription_count = len(subscriptions)
                return subscription_count
    except Exception as e:
        print(f"API request error: {str(e)}")
        log(f"API request error: {str(e)}")
        return f"An unexpected error occurred: {str(e)}"




async def register_user(telegram_id, username, first_name, last_name):
    async with aiohttp.ClientSession() as session:
        url = f"{config.DJANGO_API_URL}/api/client_list/"
        # Provide a default value if username is None
        if username is None:
            username = f"user_{telegram_id}"
        data = {
            'telegramid': telegram_id,
            'username': username,
            'firstname': first_name,
            'lastname': last_name
        }
        logging.info(f"Registering user with data: {data}")  # Add logging
        try:
            async with session.post(url, json=data) as response:
                status = response.status
                if status in (200, 201):
                    json_response = await response.json()
                    logging.info(f"Registration Successful: {json_response}")
                    return True, json_response  # Success, return JSON data
                else:
                    text_response = await response.text()
                    logging.error(f"Registration Failed ({status}): {text_response}")
                    return False, text_response  # Error, return error message
        except Exception as e:
            logging.error(f"Exception during registration: {e}")
            log(f"Exception during registration: {e}")
            return False, str(e)


async def get_user_details(telegram_id):
    try:
        client_id = await get_client_id_from_telegram_id(telegram_id)
        if not client_id:
            return "No valid client ID found for the given Telegram ID."
        log(f"No valid client ID found for the given Telegram ID.: {client_id}")

        async with aiohttp.ClientSession() as session:
            async with session.get(f"{config.DJANGO_API_URL}/api/clients/{client_id}/") as response:
                if response.status != 200:
                    print(f"Failed to get client details: {response.status}")
                    log(f"Failed to get client details: {response.status}")
                    return f"Failed to get client details with status {response.status}: {await response.text()}"

                client_details = await response.json()
                print(f"Client details response: {client_details}")

                referred_by = client_details.get('referred_by', None)
                return referred_by
    except Exception as e:
        print(f"API request error: {str(e)}")
        log(f"API request error: {str(e)}")
        return f"An unexpected error occurred: {str(e)}"


async def get_client_id_from_telegram_id(telegram_id):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{config.DJANGO_API_URL}/api/clients/",
                                   params={'telegramid': telegram_id}) as response:
                if response.status != 200:
                    print(f"Failed to get clients: {response.status}")
                    log(f"Failed to get clients: {response.status}")
                    return None

                clients = await response.json()
                print(f"Clients response: {clients}")
                if not clients:
                    print("No clients found")
                    log("No clients found")
                    return None

                for client in clients:
                    if client['telegramid'] == telegram_id:
                        return client['id']

                print("No matching client found for the given Telegram ID")
                log("No matching client found for the given Telegram ID")
                return None
    except Exception as e:
        print(f"API request error: {str(e)}")
        log(f"API request error: {str(e)}")
        return None
    

async def get_rate_id_from_ratename(name):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{config.DJANGO_API_URL}/api/rates/",
                                   params={'name': name}) as response:
                if response.status != 200:
                    print(f"Failed to get rates: {response.status}")
                    log(f"Failed to get rates: {response.status}")
                    return None

                rates = await response.json()
                print(f"Clients response: {rates}")
                log(f"Clients response: {rates}")
                if not rates:
                    print("No clients found")
                    return None

                for rate in rates:
                    if rate['name'] == name:
                        return rate['id']

                print("No matching client found for the given Telegram ID")
                log("No matching client found for the given Telegram ID")
                return None
    except Exception as e:
        print(f"API request error: {str(e)}")
        log(f"API request error: {str(e)}")
        return None

async def get_bonus_days_from_ratename(rate_name):
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{config.DJANGO_API_URL}/api/rates/?name={rate_name}"
            async with session.get(url) as response:
                if response.status != 200:
                    raise ValueError(f"Failed to fetch rate details: {response.status}")
                log(f"Failed to fetch rate details: {response.status}")
                
                rate_details = await response.json()
                print(f"Raw rate details fetched for {rate_name}: {rate_details}")  # Detailed debug statement
                log(f"Raw rate details fetched for {rate_name}: {rate_details}") 

                # Ensure the response is a list and contains at least one item
                if not isinstance(rate_details, list) or not rate_details:
                    raise ValueError(f"Rate details are empty or not a list for rate: {rate_name}")
                log(f"Rate details are empty or not a list for rate: {rate_name}")

                # Access the first item in the list
                rate_info = rate_details[0]
                print(f"Parsed rate info for {rate_name}: {rate_info}")  # Detailed debug statement
                log(f"Parsed rate info for {rate_name}: {rate_info}")

                # Fetch the bonus_days from the rate info
                bonus_days = rate_info.get('bonus_days', None)
                print(f"Bonus days fetched for rate {rate_name}: {bonus_days}")  # Detailed debug statement
                log(f"Bonus days fetched for rate {rate_name}: {bonus_days}") 

                if bonus_days is None:
                    print(f"Bonus days is None for rate: {rate_name}")
                    log(f"Bonus days is None for rate: {rate_name}")
                    return None
                
                return bonus_days
    except Exception as e:
        print(f"Error fetching bonus days: {e}")
        log(f"Error fetching bonus days: {e}")
        return None

    
async def get_days_from_ratename(name):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{config.DJANGO_API_URL}/api/rates/", params={'name': name}) as response:
                if response.status != 200:
                    print(f"Failed to get rates: {response.status}")
                    log(f"Failed to get rates: {response.status}")
                    return None

                rates = await response.json()
                print(f"Rates response: {rates}")
                log(f"Rates response: {rates}")
                if not rates:
                    print("No rates found")
                    log("No rates found")
                    return None

                for rate in rates:
                    if rate['name'] == name:
                        return rate['dayamount']  # Ensure you are returning the correct field

                print("No matching rate found for the given name")
                log("No matching rate found for the given name")
                return None
    except Exception as e:
        print(f"API request error: {str(e)}")
        log(f"API request error: {str(e)}")
        return None



async def update_usedref(telegram_id):
    try:
        client_id = await get_client_id_from_telegram_id(telegram_id)
        if not client_id:
            return "No valid client ID found for the given Telegram ID."

        async with aiohttp.ClientSession() as session:
            async with session.patch(f"{config.DJANGO_API_URL}/api/clients/{client_id}/",
                                     json={'usedref': True}) as response:
                if response.status != 200:
                    print(f"Failed to update client usedref: {response.status}")
                    log(f"Failed to update client usedref: {response.status}")
                    return f"Failed to update client usedref with status {response.status}: {await response.text()}"
                return "Client usedref updated successfully!"
    except Exception as e:
        print(f"API request error: {str(e)}")
        log(f"API request error: {str(e)}")
        return f"An unexpected error occurred: {str(e)}"


async def add_device(telegram_id, subs_name, device_name, datestart):
    client_id = await get_client_id_from_telegram_id(telegram_id)
    if not client_id:
        return "No valid client ID found for the given Telegram ID."

    rateid = await get_rate_id_from_ratename(subs_name)
    if not rateid:
        return "Rate ID could not be found for the subscription name provided."

    dayamount = await get_days_from_ratename(subs_name)
    if not isinstance(dayamount, int):
        return "Invalid day amount for the given subscription name."

    date_format = "%Y-%m-%dT%H:%M:%S"
    date_start = datetime.strptime(datestart, date_format)
    date_end = date_start + timedelta(days=dayamount)
    date_end_str = date_end.strftime(date_format)

    async with aiohttp.ClientSession() as session:
        subscription_data = {
            'clientid': client_id,
            'rateid': rateid,
            'datestart': datestart,
            'dateend': date_end_str,
            'name': device_name
        }
        async with session.post(f"{config.DJANGO_API_URL}/api/subscriptions/", json=subscription_data) as subscription_response:
            if subscription_response.status == 201:
                subscription_json = await subscription_response.json()
                subscription_id = subscription_json.get('id')
                if not subscription_id:
                    return "Error: No subscription ID returned from the server."
                
                # Update the subscription with a config name derived from the subscription ID
                config_name = subscription_id[:8]
                update_data = {'config_name': config_name}
                async with session.patch(f"{config.DJANGO_API_URL}/api/subscriptions/{subscription_id}/", json=update_data) as patch_response:
                    if patch_response.status == 200:
                        return subscription_id
                    else:
                        return f"Failed to update subscription config_name with status {patch_response.status}: {await patch_response.text()}"
            else:
                return f"Failed to create subscription with status {subscription_response.status}: {await subscription_response.text()}"



async def get_subscriptions_by_client_id(client_id):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{config.DJANGO_API_URL}/api/subscriptions/",
                                   params={'clientid': client_id}) as response:
                if response.status != 200:
                    print(f"Failed to get subscriptions: {response.status}")
                    log(f"Failed to get subscriptions: {response.status}")
                    return f"Failed to get subscriptions with status {response.status}: {await response.text()}"

                subscriptions = await response.json()
                print(f"Subscriptions response: {subscriptions}")
                log(f"Subscriptions response: {subscriptions}")
                if not subscriptions:
                    return []

                return [subscription for subscription in subscriptions if subscription['clientid'] == client_id]
    except Exception as e:
        print(f"API request error: {str(e)}")
        log(f"API request error: {str(e)}")
        return f"An unexpected error occurred: {str(e)}"


async def get_telegram_id_for_client_id(client_id):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{config.DJANGO_API_URL}/api/clients/",
                                   params={'id': client_id}) as response:
                if response.status != 200:
                    print(f"Failed to get clients: {response.status}")
                    log(f"Failed to get clients: {response.status}")
                    return None

                clients = await response.json()
                print(f"Clients response: {clients}")
                log(f"Clients response: {clients}")
                if not clients:
                    print("No clients found")
                    log("No clients found")
                    return None

                for client in clients:
                    if client['id'] == client_id:
                        return client['telegramid']

                print("No matching client found for the given Telegram ID")
                log("No matching client found for the given Telegram ID")
                return None
    except Exception as e:
        print(f"API request error: {str(e)}")
        log(f"API request error: {str(e)}")
        return None



async def list_rates():
    """ List available rates where isreferral is false """
    response = requests.get(f"{config.DJANGO_API_URL}/api/rates")
    success, data = handle_response(response)
    if success:
        # Filter rates where isreferral is false
        filtered_rates = [rate for rate in data if not rate.get('isreferral', False)]
        print("Filtered normal rates:", filtered_rates)
        return filtered_rates
    return []

async def list_rates_isreferral():
    """ List available rates where isreferral is true """
    response = requests.get(f"{config.DJANGO_API_URL}/api/rates")
    success, data = handle_response(response)
    if success:
        # Filter rates where isreferral is true
        filtered_rates = [rate for rate in data if rate.get('isreferral', False)]
        print("Filtered referral rates:", filtered_rates)
        return filtered_rates
    return []


async def add_referred_by(telegram_id, referral_input):
    try:
        client_id = await get_client_id_from_telegram_id(telegram_id)
        if not client_id:
            print(f"No valid client ID found for the given Telegram ID: {telegram_id}")
            log(f"No valid client ID found for the given Telegram ID: {telegram_id}")
            return False

        # First, try to find the client by referral_id
        referred_by_client = await find_client_by_referral_id(referral_input)
        
        if not referred_by_client:
            # If no client is found by referral_id, assume referral_input is the client's id
            referred_by_client = await someone_used_referral(referral_input)
        
        if isinstance(referred_by_client, str) or not referred_by_client:
            print("Referral input is invalid")
            log("Referral input is invalid")
            return False

        referred_by_id = referred_by_client['id']
        
        if client_id == referred_by_id:
            print("Client ID and referred_by ID are the same, cannot self-refer")
            log("Client ID and referred_by ID are the same, cannot self-refer")
            return False

        async with aiohttp.ClientSession() as session:
            patch_url = f"{config.DJANGO_API_URL}/api/clients/{client_id}/update_referred_by/"
            payload = {'referred_by': referred_by_id}
            async with session.patch(patch_url, json=payload) as response:
                if response.status != 200:
                    print(f"Failed to update client referred_by: {response.status}")
                    log(f"Failed to update client referred_by: {response.status}")
                    return False
                return True
    except Exception as e:
        print(f"API request error: {str(e)}")
        return False


async def someone_used_referral(client_id):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{config.DJANGO_API_URL}/api/clients/{client_id}/") as response:
                if response.status != 200:
                    #error_message = f"Failed to find client by client_id with status {response.status}: {await response.text()}"
                    error_message = f"🚫 Указан неверный реферальный код Вашего друга"
                    print(error_message)
                    log(error_message)
                    return error_message

                client = await response.json()
                print(f"Client response: {client}")  # Log the retrieved client
                return client
    except Exception as e:
        error_message = f"API request error in someone_used_referral: {str(e)}"
        print(error_message)
        return error_message


async def update_dateend_referral(subscription_id, bonus_days):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{config.DJANGO_API_URL}/api/subscriptions/{subscription_id}/") as response:
                if response.status != 200:
                    error_message = f"Failed to get subscription: {response.status}, {await response.text()}"
                    print(error_message)
                    return error_message

                subscription = await response.json()
                print(f"Current subscription details: {subscription}")

                # Correct usage of datetime class
                current_dateend = datetime.strptime(subscription['dateend'], "%Y-%m-%dT%H:%M:%SZ")
                new_dateend = current_dateend + timedelta(days=bonus_days)
                print(f"New dateend: {new_dateend}")

                update_payload = {'dateend': new_dateend.strftime("%Y-%m-%dT%H:%M:%SZ")}
                print(f"Sending PATCH request to update dateend with payload: {update_payload}")

                patch_url = f"{config.DJANGO_API_URL}/api/subscriptions/{subscription_id}/"
                async with session.patch(patch_url, json=update_payload) as patch_response:
                    patch_response_text = await patch_response.text()
                    if patch_response.status != 200:
                        error_message = f"Failed to update subscription dateend: {patch_response.status}, {patch_response_text}"
                        print(error_message)
                        return error_message

                    print(f"PATCH response: {patch_response_text}")
                    return f"{bonus_days} days added successfully."
    except aiohttp.ClientError as e:
        error_message = f"Client error in update_dateend_referral: {str(e)}"
        print(error_message)
        return error_message
    except aiohttp.ServerTimeoutError as e:
        error_message = f"Server timeout error in update_dateend_referral: {str(e)}"
        print(error_message)
        return error_message
    except aiohttp.ServerConnectionError as e:
        error_message = f"Server connection error in update_dateend_referral: {str(e)}"
        print(error_message)
        return error_message
    except Exception as e:
        error_message = f"Unexpected error in update_dateend_referral: {str(e)}"
        print(error_message)
        return error_message


async def update_name_subs(subscription_id, name):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{config.DJANGO_API_URL}/api/subscriptions/{subscription_id}/") as response:
                if response.status != 200:
                    error_message = f"Failed to get subscription: {response.status}, {await response.text()}"
                    print(error_message)
                    return error_message

                subscription = await response.json()
                print(f"Current subscription details: {subscription}")

                update_payload = {'name': name}
                print(f"Sending PATCH request to update dateend with payload: {update_payload}")

                patch_url = f"{config.DJANGO_API_URL}/api/subscriptions/{subscription_id}/"
                async with session.patch(patch_url, json=update_payload) as patch_response:
                    patch_response_text = await patch_response.text()
                    if patch_response.status != 200:
                        error_message = f"Failed to update subscription dateend: {patch_response.status}, {patch_response_text}"
                        print(error_message)
                        return error_message

                    print(f"PATCH response: {patch_response_text}")
    except aiohttp.ClientError as e:
        error_message = f"Client error in update_dateend_referral: {str(e)}"
        print(error_message)
        return error_message
    except aiohttp.ServerTimeoutError as e:
        error_message = f"Server timeout error in update_dateend_referral: {str(e)}"
        print(error_message)
        return error_message
    except aiohttp.ServerConnectionError as e:
        error_message = f"Server connection error in update_dateend_referral: {str(e)}"
        print(error_message)
        return error_message
    except Exception as e:
        error_message = f"Unexpected error in update_dateend_referral: {str(e)}"
        print(error_message)
        return error_message


def create_subscription(client_id, rate_id):
    data = {'clientid': client_id, 'rateid': rate_id}
    response = requests.post(f"{config.DJANGO_API_URL}/api/subscriptions/", json=data)
    return handle_response(response)


def get_user_devices(client_id):
    response = requests.get(f"{config.DJANGO_API_URL}/api/subscription/by-client-id/{client_id}/")
    success, data = handle_response(response)
    return data if success else []


def send_peer_request_to_wgapi(public_key, config_name):
    url = f"{config.WGAPI_URL}/add_user/"
    data = {'public_key': public_key, 'config_name': config_name}
    response = requests.post(url, json=data)
    return handle_response(response)


def delete_peer_request_to_wgapi(public_key):
    url = f"{config.WGAPI_URL}/remove_user/"
    data = {'public_key': public_key}
    response = requests.post(url, json=data)
    return handle_response(response)


def handle_response(response):
    if response.status_code in [200, 201]:
        return True, response.json()
    else:
        return False, response.text


def apply_referral(client_id, referral_id):
    url = f"{config.DJANGO_API_URL}/api/apply_referral/"
    data = {
        'client_id': client_id,
        'referral_id': referral_id
    }
    response = requests.post(url, json=data)
    return handle_response(response)


def create_peer_and_update_subscription(subscription_id):
    # Step 1: Request to create a WireGuard peer via WGAPI
    wgapi_url = f"{config.WGAPI_URL}/add_user/"
    wgapi_data = {'subscription_id': subscription_id}
    wgapi_response = requests.post(wgapi_url, json=wgapi_data)
    if wgapi_response.status_code == 200:
        wgapi_content = wgapi_response.json()

        # Step 2: Update the Django API with the new WireGuard configuration
        update_url = f"{config.DJANGO_API_URL}/api/subscriptions/update/"
        update_data = {
            'subscription_id': subscription_id,
            'public_key': wgapi_content['public_key'],
            'config_name': wgapi_content['config_name']
        }
        update_response = requests.post(update_url, json=update_data)
        return handle_response(update_response)
    else:
        return False, "Failed to communicate with WireGuard API"

async def update_subscription_is_used(subscription_id, is_used):
    try:
        async with aiohttp.ClientSession() as session:
            update_payload = {'is_used': is_used}
            patch_url = f"{config.DJANGO_API_URL}/api/subscriptions/{subscription_id}/"
            async with session.patch(patch_url, json=update_payload) as response:
                if response.status != 200:
                    error_message = f"Failed to update subscription is_used: {response.status}, {await response.text()}"
                    print(error_message)
                    return False
                return True
    except Exception as e:
        print(f"API request error in update_subscription_is_used: {str(e)}")
        return False

async def is_referral_used(telegram_id):
    client_id = await get_client_id_from_telegram_id(telegram_id)
    if not client_id:
        return False, "Client ID not found."
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{config.DJANGO_API_URL}/api/clients/{client_id}/") as response:
            if response.status != 200:
                return False, f"Failed to get client details: {response.status}, {await response.text()}"
            
            client_details = await response.json()
            return client_details.get('usedref', False), client_details

async def is_test_subscription_used(telegram_id):
    client_id = await get_client_id_from_telegram_id(telegram_id)
    if not client_id:
        return False, "Client ID not found."
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{config.DJANGO_API_URL}/api/clients/{client_id}/") as response:
            if response.status != 200:
                return False, f"Failed to get client details: {response.status}, {await response.text()}"
            
            client_details = await response.json()
            return client_details.get('UsedTestSubscription', False), client_details

async def update_test_subscription_used(telegram_id):
    try:
        client_id = await get_client_id_from_telegram_id(telegram_id)
        if not client_id:
            return "No valid client ID found for the given Telegram ID."

        async with aiohttp.ClientSession() as session:
            async with session.patch(f"{config.DJANGO_API_URL}/api/clients/{client_id}/",
                                     json={'UsedTestSubscription': True}) as response:
                if response.status != 200:
                    print(f"Failed to update client UsedTestSubscription: {response.status}")
                    return f"Failed to update client UsedTestSubscription with status {response.status}: {await response.text()}"
                return "Client UsedTestSubscription updated successfully!"
    except Exception as e:
        print(f"API request error: {str(e)}")
        return f"An unexpected error occurred: {str(e)}"
    
async def find_client_by_referral_id(referral_id):
    """Find a client by their referral_id."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{config.DJANGO_API_URL}/api/clients/", params={'referral_id': referral_id}) as response:
                if response.status != 200:
                    print(f"Failed to find client by referral_id: {response.status}")
                    return None

                clients = await response.json()

                if not clients:
                    return None
                
                clients = list(filter(lambda x: x['referral_id'] == referral_id, clients))

                return clients[0]
                    
    except Exception as e:
        print(f"API request error: {str(e)}")
        return None
    
async def check_and_register_with_username(telegram_id, username, first_name, last_name):
    async with aiohttp.ClientSession() as session:
        if username is None:
            username = f"user_{telegram_id}"
        
        url = f"{config.DJANGO_API_URL}/api/clients/"
        params = {'username': str(username)}
        
        # Проверка, существует ли пользователь с данным username
        async with session.get(url, params=params) as response:
            if response.status == 200:
                print(1)
                json_response = await response.json()
                
                if json_response:
                    # Если пользователь найден, обновляем его запись
                    update_url = f"{config.DJANGO_API_URL}/api/clients/update_by_username/"
                    
                    data = {
                        'telegramid': telegram_id,
                        'username': username,
                        'firstname': first_name,
                        'lastname': last_name
                    }
                    
                    async with session.patch(update_url, json=data) as update_response:
                        update_status = update_response.status
                        if update_status in (200, 201):
                            updated_json_response = await update_response.json()
                            logging.info(f"Update Successful: {updated_json_response}")
                            return True, updated_json_response  # Успешное обновление, возвращаем JSON данные
                        else:
                            update_text_response = await update_response.text()
                            logging.error(f"Update Failed ({update_status}): {update_text_response}")
                            return False, update_text_response  # Ошибка обновления, возвращаем сообщение об ошибке
                else:
                    return False
            else:
                logging.error(f"Failed to check user existence ({response.status}): {await response.text()}")
                return False

async def save_config_from_url(subscription_id, download_url):
    """
    Fetches a configuration file from the provided URL and saves it to the 'basedir/configs' directory.
    
    Args:
        subscription_id (str): The subscription ID used to name the config file.
        download_url (str): The URL from which to download the configuration file.
        
    Returns:
        str: The file path where the config was saved, or an error message if the process fails.
    """
    try:
        # Fetch the config content from the URL
        response = requests.get(download_url)
        
        if response.status_code != 200:
            return f"Failed to download config: {response.status_code} - {response.text}"
        
        # Create the path for saving the config file
        config_filename = f"{subscription_id[:8]}.conf"
        config_dir = os.path.join(os.path.dirname(__file__), 'configs')
        os.makedirs(config_dir, exist_ok=True)
        
        config_path = os.path.join(config_dir, config_filename)
        
        # Save the content to a file
        with open(config_path, 'w') as config_file:
            config_file.write(response.text)
        
        return config_path
    
    except Exception as e:
        return f"Error occurred while saving config: {str(e)}"
    

async def get_bonus_days_from_rateid(rate_id):
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{config.DJANGO_API_URL}/api/rates/{rate_id}/"
            async with session.get(url) as response:
                if response.status != 200:
                    raise ValueError(f"Failed to fetch rate details: {response.status}")
                log(f"Failed to fetch rate details: {response.status}")
                
                rate_details = await response.json()
                print(f"Raw rate details fetched for rate ID {rate_id}: {rate_details}")  # Detailed debug statement
                log(f"Raw rate details fetched for rate ID {rate_id}: {rate_details}")

                # Ensure rate details is a dictionary
                if not isinstance(rate_details, dict):
                    raise ValueError(f"Rate details are not a valid dictionary for rate ID: {rate_id}")
                log(f"Rate details are not a valid dictionary for rate ID: {rate_id}")

                # Fetch the bonus_days from the rate details
                bonus_days = rate_details.get('bonus_days', None)
                print(f"Bonus days fetched for rate ID {rate_id}: {bonus_days}")  # Detailed debug statement
                log(f"Bonus days fetched for rate ID {rate_id}: {bonus_days}")

                if bonus_days is None:
                    print(f"Bonus days is None for rate ID: {rate_id}")
                    log(f"Bonus days is None for rate ID: {rate_id}")
                    return None

                return bonus_days
    except Exception as e:
        print(f"Error fetching bonus days: {e}")
        log(f"Error fetching bonus days: {e}")
        return None
