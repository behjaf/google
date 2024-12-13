import os
import requests
import shutil
import time
import hashlib
from datetime import datetime

# Configuration
REMOTE_URLS = [  # List of 5 remote URLs
    "https://raw.githubusercontent.com/behjaf/google/refs/heads/main/led_status.sh",
    "https://raw.githubusercontent.com/behjaf/google/refs/heads/main/online.py",
    "https://raw.githubusercontent.com/behjaf/google/refs/heads/main/validate_router.py",
    "https://raw.githubusercontent.com/behjaf/google/refs/heads/main/get_server_address.py",
    "https://raw.githubusercontent.com/behjaf/google/refs/heads/main/get_new_v2ray.py",
    "https://raw.githubusercontent.com/behjaf/google/refs/heads/main/update_checker.py",
]  # Replace with your own URLs
LOCAL_PATHS = [
    "/root/led_status.sh",
    "/root/online.py",
    "/root/validate_router.py",
    "/root/get_server_address.py",
    "/root/get_new_v2ray.py",
    "/root/update_checker.py",
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
*/1440 * * * * /usr/bin/python3 /root/validate_router.py
*/720 * * * * /usr/bin/python3 /root/get_server_address.py
*/1440 * * * * /usr/bin/python3 /root/get_new_v2ray.py
*/1500 * * * * /usr/bin/python3 /root/update_checker.py
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


if __name__ == "__main__":
    for remote_url, local_path in zip(REMOTE_URLS, LOCAL_PATHS):
        remote_hash, remote_content = get_remote_file_hash(remote_url)
        if remote_hash:
            local_hash = calculate_file_hash(local_path)
            if local_hash != remote_hash:
                print(f"Update detected for {local_path}. Updating local file...")
                update_local_file(local_path, remote_content)
        time.sleep(2)

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
