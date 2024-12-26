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
def get_device_file(api_url, token):
    device_file_endpoint = f"{api_url}/api/device-file/"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    try:
        response = requests.get(device_file_endpoint, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching device-v2ray data: {e}")
        return None


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

    source_file = ''
    destination_file = ''

    token = get_token(api_url, username, password)
    if token:
        device_file_data = get_device_file(api_url, token)

        for file in device_file_data:
            current_date = datetime.now().date()
            valid_until = datetime.strptime(file['file_valid_until'], '%Y-%m-%d').date()

            # Check conditions
            if file['file_status'] and valid_until >= current_date and not file['file_has_been_updated']:
                destination_file = file['file_local_location']
                source_file = file['file_remote_location']

                try:
                    # Handle empty source_file case
                    if not source_file:
                        if os.path.exists(destination_file):
                            os.remove(destination_file)  # Remove destination file
                            print(f"Destination file removed: {destination_file}")
                        continue

                    # Download the file content directly
                    response = requests.get(source_file)
                    response.raise_for_status()  # Raise an error for bad status codes

                    # Ensure destination directory exists
                    os.makedirs(os.path.dirname(destination_file), exist_ok=True)

                    # Write the content to the destination file
                    with open(destination_file, 'wb') as output_file:  # Renamed 'file' to 'output_file'
                        output_file.write(response.content)

                    print(f"File downloaded and saved to: {destination_file}")

                    # Update the database with status and time
                    try:
                        update_endpoint = f"{api_url}/api/device-file/{file['id']}/"  # Use original 'file' from API response
                        headers = {
                            "Authorization": f"Bearer {token}",
                            "Content-Type": "application/json"
                        }
                        update_data = {
                            "file_has_been_updated": True,
                            "file_has_been_updated_time": datetime.now().isoformat()
                        }

                        # Send PATCH request to update the database
                        update_response = requests.patch(update_endpoint, headers=headers, json=update_data)
                        update_response.raise_for_status()  # Raise error if request fails

                        print(f"Database updated for file: {destination_file}")

                    except Exception as e:
                        print(f"Failed to update database: {e}")

                except Exception as e:
                    print(f"An error occurred: {e}")


    else:
        print("Failed to obtain token.")