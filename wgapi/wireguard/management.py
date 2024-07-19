import subprocess
import hashlib
import os
import uuid
from django.conf import settings
from datetime import datetime, timedelta
from django.utils import timezone
from enum import Enum

class CommandStatus(Enum):
    OK = "OK"
    ERROR = "ERROR"

def generate_ip_from_key(subscription_id):
    """ Generate a unique IP address based on the public key using SHA-256 hash. """
    hash_object = hashlib.sha256(subscription_id.encode())
    hex_dig = hash_object.hexdigest()
    # Create an IP address by using parts of the hash
    return f"10.{int(hex_dig[0:2], 16) % 255}.{int(hex_dig[2:4], 16) % 255}.{int(hex_dig[4:6], 16) % 255}"

def run_script(command):
    """ Execute the given shell command. """
    try:
        subprocess.run(command, shell=True, check=True)
        return "OK"
    except subprocess.CalledProcessError as error:
        return f"ERROR: {error.stderr.decode('utf-8') if error.stderr else 'Unknown error'}"

def add_peer(subscription_id):
    """ Add a peer to WireGuard configuration via script. """
    client_name = subscription_id[:8]
    ip_address = generate_ip_from_key(subscription_id)
    command = f"sudo bash /root/wireguard-install8.sh non-interactive 1 {client_name} {ip_address}"
    result = run_script(command)
    if result == "OK":
        return CommandStatus.OK, "Peer added successfully"
    else:
        return CommandStatus.ERROR, result

def remove_peer(client_name):
    """ Remove a peer from the WireGuard configuration via script. """
    command = f"sudo bash /root/wireguard-install8.sh non-interactive 3 {client_name}"
    result = run_script(command)
    if result == "OK":
        return CommandStatus.OK, ""
    else:
        return CommandStatus.ERROR, result