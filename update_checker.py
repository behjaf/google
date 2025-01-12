import shutil
import hashlib
from datetime import datetime
import requests
import json
import subprocess
import re
import os
import time

# Configuration
REMOTE_URLS = [  # List of 5 remote URLs
    "https://raw.githubusercontent.com/behjaf/google/main/led_status.sh",
    "https://raw.githubusercontent.com/behjaf/google/main/online.py",
    "https://raw.githubusercontent.com/behjaf/google/main/validate_router.py",
    "https://raw.githubusercontent.com/behjaf/google/main/get_server_address.py",
    "https://raw.githubusercontent.com/behjaf/google/main/get_new_v2ray.py",
    "https://raw.githubusercontent.com/behjaf/google/main/update_checker.py",
    "https://raw.githubusercontent.com/behjaf/google/main/file_get.py",
    "https://raw.githubusercontent.com/behjaf/google/main/run_command.py",
    "https://raw.githubusercontent.com/behjaf/google/main/change_link.py",
]  # Replace with your own URLs
LOCAL_PATHS = [
    "/root/led_status.sh",
    "/root/online.py",
    "/root/validate_router.py",
    "/root/get_server_address.py",
    "/root/get_new_v2ray.py",
    "/root/update_checker.py",
    "/root/file_get.py",
    "/root/run_command.py",
    "/root/change_link.py",
]  # Corresponding local file paths


def calculate_file_hash(file_path):
    """Calculate the SHA256 hash of a local file."""
    sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    except FileNotFoundError:
        print(f"Local file not found: {file_path}")
        return None


def get_remote_file_hash(url):
    """Download the remote file and calculate its hash."""
    try:
        # Force no-cache by setting headers
        response = requests.get(url, stream=True, headers={"Cache-Control": "no-cache"})
        response.raise_for_status()

        remote_content = b""
        sha256 = hashlib.sha256()
        for chunk in response.iter_content(chunk_size=4096):
            remote_content += chunk
            sha256.update(chunk)

        return sha256.hexdigest(), remote_content
    except requests.RequestException as e:
        print(f"Error fetching remote file: {e}")
        return None, None


def update_local_file(local_path, new_content):
    """Replace the local file with the new content and make it executable."""
    try:
        temp_path = local_path + ".tmp"
        with open(temp_path, "wb") as temp_file:
            temp_file.write(new_content)
        shutil.move(temp_path, local_path)

        # Make the file executable
        os.chmod(local_path, 0o755)  # rwxr-xr-x

        print(f"[*] Local file {local_path} has been updated and made executable at {datetime.now()}")
    except Exception as e:
        print(f"Error updating local file {local_path}: {e}")


def verify_crontab():
    """Verify and update the crontab file if its content differs from the desired schedule."""
    crontab_path = "/etc/crontabs/root"
    desired_crontab_content = """\
*/2 * * * * /root/led_status.sh
*/5 * * * * /usr/bin/python3 /root/online.py
0 */11 * * * /usr/bin/python3 /root/validate_router.py
0 */5 * * * /usr/bin/python3 /root/get_server_address.py
0 */2 * * * /usr/bin/python3 /root/get_new_v2ray.py
0 */7 * * * /usr/bin/python3 /root/update_checker.py
0 */9 * * * /usr/bin/python3 /root/file_get.py
0 */5 * * * /usr/bin/python3 /root/run_command.py
*/20 * * * * /usr/bin/python3 /root/change_link.py
"""

    try:
        # Check if the crontab file exists
        if os.path.exists(crontab_path):
            with open(crontab_path, "r") as crontab_file:
                current_content = crontab_file.read()
        else:
            current_content = ""

        # Compare the content
        if current_content.strip() != desired_crontab_content.strip():
            print(f"[*] Updating crontab file {crontab_path}...")
            with open(crontab_path, "w") as crontab_file:
                crontab_file.write(desired_crontab_content)

            # Reload crontab to apply changes
            os.system("service cron restart")
            print(f"[*] Crontab file {crontab_path} updated and cron service restarted.")
        else:
            print(f"[*] Crontab file {crontab_path} is already up-to-date.")
    except Exception as e:
        print(f"Error verifying or updating crontab file: {e}")


def sent_update_done_to_server():
    # File path for storing server location
    SERVER_LOCATION_FILE = "/root/server_location.txt"

    # Retry logic

    def retry_request(func, max_retries=5, delay=30):
        """Retry a request with exponential backoff."""
        for attempt in range(1, max_retries + 1):
            try:
                response = func()
                if response.ok:  # Covers 2xx responses
                    return response
                else:
                    print(f"Attempt {attempt}/{max_retries}: Failed with status {response.status_code}")
            except requests.RequestException as e:
                print(f"Attempt {attempt}/{max_retries}: Exception {e}")
            time.sleep(delay * (2 ** (attempt - 1)))  # Exponential backoff
        print("Max retries reached. Exiting.")
        exit(1)

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
    DEVICE_UPDATE_URL = f"{BASE_URL}device-update/"

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

        # Prepare payload for Device_Update
        payload = {
            "serial_number": serial_number,
            "mlb_serial_number": mlb_serial_number,
            "device": device_id,
        }

        # Post to Device_Online
        def post_device_update():
            return requests.post(DEVICE_UPDATE_URL, headers=headers, data=json.dumps(payload))

        online_response = retry_request(post_device_update)
        print("Device Time update data posted successfully!")
    else:
        print(f"No device found for serial number: {serial_number}")


if __name__ == "__main__":
    for remote_url, local_path in zip(REMOTE_URLS, LOCAL_PATHS):
        remote_hash, remote_content = get_remote_file_hash(remote_url)
        if remote_hash:
            local_hash = calculate_file_hash(local_path)
            if local_hash != remote_hash:
                print(f"Update detected for {local_path}. Updating local file...")
                update_local_file(local_path, remote_content)
        time.sleep(1)

    server_location_path = "/root/server_location.txt"
    if not os.path.exists(server_location_path):
        print(f"[!] {server_location_path} does not exist. Running get_server_address.py...")
        try:
            get_server_address_path = "/root/get_server_address.py"
            os.system(f"python3 {get_server_address_path}")
            print(f"[*] {server_location_path} created successfully.")
        except Exception as e:
            print(f"Error running {get_server_address_path}: {e}")

    # Verify and update crontab
    verify_crontab()

    # Notify server about update completion
    sent_update_done_to_server()
