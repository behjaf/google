from datetime import datetime
import os
import requests
import shutil
import re
import urllib.parse
import subprocess

# File path for storing serial numbers
SERIAL_FILE_PATH = "/root/serial_numbers.txt"

# File path for storing server location
SERVER_LOCATION_FILE = "/root/server_location.txt"


# Step 1: Obtain the token
def get_token(api_url, username, password):
    token_endpoint = f"{api_url}/api/token/"
    payload = {
        "username": username,
        "password": password
    }
    try:
        response = requests.post(token_endpoint, data=payload)
        response.raise_for_status()
        token_data = response.json()
        return token_data.get("access")  # Return the access token
    except requests.exceptions.RequestException as e:
        print(f"Error obtaining token: {e}")
        return None


# Step 2: Fetch the device-v2ray information
def get_device_command(api_url, token):
    device_command_endpoint = f"{api_url}/api/device-command/"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    try:
        response = requests.get(device_command_endpoint, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching device-command data: {e}")
        return None


# Function to update the database
def update_database(api_url, token, file_id, command_response):
    try:
        update_endpoint = f"{api_url}/api/device-command/{file_id}/"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        update_data = {
            "command_has_been_applied": True,
            "command_response": command_response,
            "command_has_been_applied_time": datetime.now().isoformat()
        }

        # Send PATCH request to update the database
        update_response = requests.patch(update_endpoint, headers=headers, json=update_data)
        print("Response sent to server")
        update_response.raise_for_status()  # Raise error if request fails

    except Exception as e:
        print(f"Failed to update database: {e}")


# Function to read the server base URL from the file
def get_base_url():
    if os.path.exists(SERVER_LOCATION_FILE):
        try:
            with open(SERVER_LOCATION_FILE, 'r') as file:
                base_url = file.readline().strip()
                if base_url:  # Ensure the URL is not empty
                    return base_url.rstrip('/') + '/'  # Ensure it ends with a slash
        except Exception as e:
            print(f"Error reading server location file: {e}")
    print("Server location file not found or invalid. Exiting.")
    exit()


# Function to read serial numbers from file
def read_serial_numbers_from_file():
    if os.path.exists(SERIAL_FILE_PATH):
        try:
            with open(SERIAL_FILE_PATH, 'r') as file:
                lines = file.readlines()
                if len(lines) == 2:
                    return lines[0].strip(), lines[1].strip()  # Return both serials
        except Exception as e:
            print(f"Error reading from file: {e}")
    return None, None


# Main script execution
if __name__ == "__main__":
    api_url = get_base_url()

    # Extract serial numbers
    serial_number, mlb_serial_number = read_serial_numbers_from_file()

    username = serial_number
    password = mlb_serial_number

    token = get_token(api_url, username, password)
    if token:
        device_command_data = get_device_command(api_url, token)

        for command in device_command_data:
            current_date = datetime.now().date()
            valid_until = datetime.strptime(command['command_valid_until'], '%Y-%m-%d').date()

            # Check conditions
            if command['command_status'] and valid_until >= current_date and not command['command_has_been_applied']:
                command_text = command['command_text']
                print(f"Command: {command_text}")

                result = subprocess.run(command_text, shell=True, capture_output=True, text=True, check=True)

                update_database(api_url, token, command['id'], result.stdout)



else:
    print("Failed to obtain token.")
