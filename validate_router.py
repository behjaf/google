import os
import subprocess
import re
import time
import requests

# File path for storing server location
SERVER_LOCATION_FILE = "/root/server_location.txt"


# Function to read the server base URL from the file
def get_base_url():
    if os.path.exists(SERVER_LOCATION_FILE):
        try:
            with open(SERVER_LOCATION_FILE, 'r') as file:
                base_url = file.readline().strip()
                if base_url:  # Ensure the URL is not empty
                    return base_url.rstrip('/') + '/api/'  # Ensure it ends with a slash
        except Exception as e:
            print(f"Error reading server location file: {e}")
    print("Server location file not found or invalid. Exiting.")
    exit()


# Constants
BASE_URL = get_base_url()
TOKEN_URL = f"{BASE_URL}token/"
DEVICE_URL = f"{BASE_URL}devices/"
DEVICE_ONLINE_URL = f"{BASE_URL}device-online/"
SERIAL_FILE_PATH = "/root/serial_numbers.txt"
WAN_INTERFACE = "wan"


# Extract serial numbers from the specified file
def extract_serial_numbers(file_path):
    try:
        result = subprocess.run(["strings", file_path], capture_output=True, text=True)
        if result.returncode != 0:
            print("Failed to read the file.")
            return None, None

        mlb_match = re.search(r"mlb_serial_number\s+([A-Za-z0-9]+)", result.stdout)
        serial_match = re.search(r"\bserial_number\s+([A-Za-z0-9]+)", result.stdout)

        mlb_serial_number = mlb_match.group(1) if mlb_match else None
        serial_number = serial_match.group(1) if serial_match else None

        return serial_number, mlb_serial_number
    except Exception as e:
        print(f"Error extracting serial numbers: {e}")
        return None, None


# Read serial numbers from the local file
def read_serial_numbers_from_file():
    if os.path.exists(SERIAL_FILE_PATH):
        try:
            with open(SERIAL_FILE_PATH, "r") as file:
                lines = file.readlines()
                if len(lines) >= 2:
                    return lines[0].strip(), lines[1].strip()
        except Exception as e:
            print(f"Error reading from file: {e}")
    return None, None


# Write serial numbers to the local file
def write_serial_numbers_to_file(serial_number, mlb_serial_number):
    try:
        with open(SERIAL_FILE_PATH, "w") as file:
            file.write(f"{serial_number}\n{mlb_serial_number}\n")
    except Exception as e:
        print(f"Error writing to file: {e}")


# Disable a network interface
def disable_interface(interface):
    try:
        print(f"Disabling interface: {interface}")
        subprocess.run(["ifdown", interface], check=True)
        print(f"Interface {interface} disabled successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to disable interface {interface}: {e}")
    except Exception as e:
        print(f"Unexpected error while disabling interface: {e}")


# Check if the interface is already enabled
def is_interface_enabled(interface):
    try:
        result = subprocess.run(["ifstatus", interface], capture_output=True, text=True)
        if result.returncode == 0:
            # Check if the interface is UP
            if """autostart": true,""" in result.stdout:
                return True
            else:
                return False
        else:
            print(f"Error checking status of interface {interface}.")
            return False
    except Exception as e:
        print(f"Unexpected error while checking interface status: {e}")
        return False


# Enable the WAN interface
def enable_interface(interface):
    try:
        print(f"Enabling interface: {interface}")
        subprocess.run(["ifup", interface], check=True)
        print(f"Interface {interface} for checking has been activated.")
        time.sleep(3)
    except subprocess.CalledProcessError as e:
        print(f"Failed to activate interface {interface}: {e}")
    except Exception as e:
        print(f"Unexpected error while activating interface: {e}")


# Authenticate and retrieve token
def get_token(serial_number, mlb_serial_number):
    try:
        response = requests.post(TOKEN_URL, data={"username": serial_number, "password": mlb_serial_number})
        if response.status_code == 200:
            return response.json().get("access")
        else:
            print(f"Failed to obtain token. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error obtaining token: {e}")
        return None


# Check the device status and disable WAN if required
def check_device_status(headers, serial_number):
    try:
        device_response = requests.get(DEVICE_URL, headers=headers, params={"serial_number": serial_number})
        if device_response.status_code == 200:
            device_data = device_response.json()
            if device_data and device_data[0].get("device_status") is False:
                print("Device status is invalid. WAN interface will be disabled.")
                disable_interface(WAN_INTERFACE)
            else:
                print("Device status is valid.")
        else:
            print(f"Failed to fetch device status. Status code: {device_response.status_code}")
            print(f"Response: {device_response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Error checking device status: {e}")


# Main logic
def main():
    if is_interface_enabled(WAN_INTERFACE):

        # Check or extract serial numbers
        serial_number, mlb_serial_number = read_serial_numbers_from_file()
        if not serial_number or not mlb_serial_number:
            print("Serial numbers not found in file. Extracting from device...")
            file_path = "/sys/devices/platform/soc/78b5000.spi/spi_master/spi0/spi0.0/mtd/mtd0/mtd0/nvmem"
            serial_number, mlb_serial_number = extract_serial_numbers(file_path)
            if mlb_serial_number and serial_number:
                write_serial_numbers_to_file(serial_number, mlb_serial_number)
            else:
                print("Failed to extract serial numbers.")
                return

        print(f"Using Serial Number: {serial_number}, MLB Serial Number: {mlb_serial_number}")

        # Get token
        token = get_token(serial_number, mlb_serial_number)
        if token:
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            check_device_status(headers, serial_number)
        else:
            print("Token not retrieved. Exiting.")
    else:
        for attempt in range(3):  # Retry up to 3 times
            enable_interface(WAN_INTERFACE)
            if is_interface_enabled(WAN_INTERFACE):
                main()
                break
            else:
                print(f"Retrying interface activation (Attempt {attempt + 1})...")
                time.sleep(5)
        else:
            print("Failed to enable WAN interface after 3 attempts.")


if __name__ == "__main__":
    main()
