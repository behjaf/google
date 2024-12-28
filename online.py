import requests
import json
import subprocess
import re
import os
import time

# File path for storing server location
SERVER_LOCATION_FILE = "/root/server_location.txt"


def detect_status_from_led():
    try:
        # Define paths to LED trigger files
        red_path = "/sys/class/leds/LED0_Red/trigger"
        green_path = "/sys/class/leds/LED0_Green/trigger"
        blue_path = "/sys/class/leds/LED0_Blue/trigger"

        # Read the content of each file
        with open(red_path, 'r') as red_file:
            red_status = red_file.read().strip()
        with open(green_path, 'r') as green_file:
            green_status = green_file.read().strip()
        with open(blue_path, 'r') as blue_file:
            blue_status = blue_file.read().strip()

        # Check conditions for 'green-blue' (VPN connected)
        if '[none]' in red_status and '[default-on]' in green_status and '[default-on]' in blue_status:
            print("VPN is connected")
            return "green-blue"

        # Check conditions for 'green-red' (Internet connected, no VPN)
        elif '[default-on]' in red_status and '[default-on]' in green_status and '[none]' in blue_status:
            print("Internet is connected but without VPN")
            return "green-red"

        else:
            print("Unknown status")
            return "unknown"

    except FileNotFoundError as e:
        print(f"Error: {e}")
        return "error"
    except Exception as e:
        print(f"Error: {e}")
        return "error"


# Retry logic
def retry_request(func, max_retries=4, delay=15):
    for attempt in range(max_retries):
        response = func()
        if response.status_code == 200 or response.status_code == 201:
            return response
        else:
            print(f"Retry {attempt + 1}/{max_retries} failed. Retrying in {delay} seconds...")
            time.sleep(delay)
    print("Max retries reached. restarting Wireless client interface and WAN interface.")
    exit()


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


# Read the base URL dynamically
BASE_URL = get_base_url()
TOKEN_URL = f"{BASE_URL}token/"
DEVICE_URL = f"{BASE_URL}devices/"
DEVICE_ONLINE_URL = f"{BASE_URL}device-online/"

# File path for storing serial numbers
SERIAL_FILE_PATH = "/root/serial_numbers.txt"


# Function to extract serial numbers from the file
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

        return mlb_serial_number, serial_number

    except Exception as e:
        print(f"Error extracting serial numbers: {e}")
        return None, None


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


# Function to write serial numbers to file
def write_serial_numbers_to_file(serial_number, mlb_serial_number):
    try:
        with open(SERIAL_FILE_PATH, 'w') as file:
            file.write(f"{serial_number}\n{mlb_serial_number}\n")
    except Exception as e:
        print(f"Error writing to file: {e}")


# Check if serial numbers file exists, if not extract and save
serial_number, mlb_serial_number = read_serial_numbers_from_file()

if not mlb_serial_number or not serial_number:
    print("Serial numbers not found in file. Extracting from device...")
    # Path to the file containing the serial numbers
    file_path = "/sys/devices/platform/soc/78b5000.spi/spi_master/spi0/spi0.0/mtd/mtd0/mtd0/nvmem"
    mlb_serial_number, serial_number = extract_serial_numbers(file_path)

    if mlb_serial_number and serial_number:
        print(f"Extracted serial numbers: {serial_number}, {mlb_serial_number}")
        # Write the extracted serial numbers to the file
        write_serial_numbers_to_file(serial_number, mlb_serial_number)
    else:
        print("Failed to extract serial numbers.")
        exit()


# Get token each time the script runs
def get_token():
    return requests.post(TOKEN_URL, data={"username": serial_number, "password": mlb_serial_number})


response = retry_request(get_token)

token = response.json()["access"]
# print("Token obtained successfully!")

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
}


# Fetch device ID using serial_number
def fetch_device():
    return requests.get(DEVICE_URL, headers=headers, params={"serial_number": serial_number})


device_response = retry_request(fetch_device)

device_data = device_response.json()

if device_data:
    device_id = device_data[0]["id"]
    net_status = detect_status_from_led()
    if net_status == "green-blue":

        # Prepare payload for Device_Online
        payload = {
            "serial_number": serial_number,
            "mlb_serial_number": mlb_serial_number,
            "device": device_id,
            "vpn_status": True,
        }
    elif net_status == "green-red":
        # Prepare payload for Device_Online
        payload = {
            "serial_number": serial_number,
            "mlb_serial_number": mlb_serial_number,
            "device": device_id,
            "vpn_status": False,
        }
    else:
        # Prepare payload for Device_Online
        payload = {
            "serial_number": serial_number,
            "mlb_serial_number": mlb_serial_number,
            "device": device_id,
        }


    # Post to Device_Online
    def post_device_online():
        return requests.post(DEVICE_ONLINE_URL, headers=headers, data=json.dumps(payload))


    online_response = retry_request(post_device_online)
    print("Device online data posted successfully!")
else:
    print(f"No device found for serial number: {serial_number}")
