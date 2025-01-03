import os
import requests
import re
import urllib.parse
import subprocess
import json


# Extract serial numbers from the file
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
def get_device_v2ray(api_url, token):
    device_v2ray_endpoint = f"{api_url}/api/device-v2ray/"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    try:
        response = requests.get(device_v2ray_endpoint, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching device-v2ray data: {e}")
        return None


# Step 3: Fetch the server_list data by ID
def get_server_list(api_url, token, server_list_id):
    server_list_endpoint = f"{api_url}/api/server-list/{server_list_id}/"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    try:
        response = requests.get(server_list_endpoint, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching server-list data for ID {server_list_id}: {e}")
        return None


# Restart Passwall2 service
def restart_passwall2_service():
    try:
        subprocess.run(["/etc/init.d/passwall2", "restart"], check=True)
        print("passwall2 service restarted successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error restarting passwall2 service: {e}")
    except FileNotFoundError:
        print("Command not found. Ensure /etc/init.d/passwall2 exists.")


# Function to parse VLESS link and generate configuration
def parse_vless(vless_link):
    config = {}

    match = re.match(r'vless://([a-f0-9\-]+)@([\w\.-]+):(\d+)\?([^#]+)#(.+)', vless_link)
    if not match:
        print("Invalid VLESS link")
        sys.exit(1)

    uuid, address, port, params, remarks = match.groups()
    params_dict = dict(param.split('=') for param in params.split('&'))

    config['uuid'] = uuid
    config['address'] = address
    config['port'] = port
    config['remarks'] = remarks
    config['protocol'] = 'vless'
    config['type'] = 'Xray'
    config['timeout'] = '60'
    config['add_from'] = '导入'
    config['add_mode'] = '1'
    config['encryption'] = params_dict.get('encryption', 'none')
    config['tls'] = '1' if params_dict.get('security') == 'tls' else '0'
    config['tls_allowInsecure'] = '1' if params_dict.get('allowInsecure') == '1' else '0'

    transport_type = params_dict.get('type', 'tcp')
    config['transport'] = 'ws' if transport_type == 'ws' else 'raw'

    if transport_type == 'ws':
        # URL decode ws_path to get the correct value
        config['ws_path'] = urllib.parse.unquote(params_dict.get('path', '/'))
        config['ws_host'] = params_dict.get('host', '')
    elif transport_type == 'tcp':
        config['tcp_guise'] = params_dict.get('headerType', 'none')
        config['tcp_guise_http_host'] = params_dict.get('host', '')

    if config['tls'] == '1':
        config['tls_serverName'] = params_dict.get('sni', '')
        config['fingerprint'] = params_dict.get('fp', 'randomized')

    return config



def update_passwall2_file(new_config):
    passwall_file = "/etc/config/passwall2"

    # Read existing file
    with open(passwall_file, "r") as file:
        lines = file.readlines()

    # Prepare new config block
    new_uuid = new_config['uuid']
    new_node = []
    found_existing = False
    current_node = []

    for line in lines:
        if line.startswith("config nodes"):
            # Check if a node is already being processed
            if current_node:
                # Check if UUID matches
                if f"option uuid '{new_uuid}'" in current_node:
                    # Replace existing node
                    new_node = [
                        f"config nodes 'lFQCkuzv'\n",
                        f"\toption tls '{new_config['tls']}'\n",
                        f"\toption protocol '{new_config['protocol']}'\n",
                        f"\toption encryption '{new_config['encryption']}'\n",
                        f"\toption add_from '{new_config['add_from']}'\n",
                        f"\toption port '{new_config['port']}'\n",
                        f"\toption remarks '🇹🇷 {new_config['remarks']}'\n",
                        f"\toption add_mode '{new_config['add_mode']}'\n",
                        f"\toption type '{new_config['type']}'\n",
                        f"\toption timeout '{new_config['timeout']}'\n",
                        f"\toption fingerprint 'randomized'\n",
                        f"\toption tls_serverName '{new_config.get('tls_serverName', '')}'\n",
                        f"\toption address '{new_config['address']}'\n",
                        f"\toption tls_allowInsecure '{new_config['tls_allowInsecure']}'\n",
                        f"\toption uuid '{new_config['uuid']}'\n",
                        f"\toption transport '{new_config['transport']}'\n",
                    ]

                    # Transport-specific options
                    if new_config["transport"] == "ws":
                        new_node.append(f"\toption ws_path '{new_config['ws_path']}'\n")
                        new_node.append(f"\toption ws_host '{new_config['ws_host']}'\n")
                    elif new_config["transport"] == "raw":
                        new_node.append(f"\toption tcp_guise '{new_config['tcp_guise']}'\n")
                        new_node.append(f"\toption tcp_guise_http_host '{new_config['tcp_guise_http_host']}'\n")

                    found_existing = True
                    current_node = []  # Clear to skip rewriting this node
                else:
                    current_node.append(line)
            else:
                current_node.append(line)
        elif current_node:
            current_node.append(line)

    # Write updated content
    with open(passwall_file, "w") as file:
        for line in current_node:
            file.write(line)
        if found_existing:
            for line in new_node:
                file.write(line)
        else:
            # Append as a new node if no existing match is found
            for line in new_node:
                file.write(line)

    print("passwall2 file updated.")





# File path for storing server location
SERVER_LOCATION_FILE = "/root/server_location.txt"


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


LOCAL_LINK_FILE = "/root/v2ray_link.txt"


# Save link locally
def save_link_locally(vless_link):
    if os.path.exists(LOCAL_LINK_FILE):
        with open(LOCAL_LINK_FILE, 'r') as file:
            saved_link = file.read().strip()
            if saved_link == vless_link:
                print("Same link already saved.")
                exit()
    with open(LOCAL_LINK_FILE, 'w') as file:
        file.write(vless_link)
    print("Link saved locally.")


# Main script execution
if __name__ == "__main__":
    api_url = get_base_url()
    file_path = "/sys/devices/platform/soc/78b5000.spi/spi_master/spi0/spi0.0/mtd/mtd0/mtd0/nvmem"

    # Extract serial numbers
    mlb_serial_number, serial_number = extract_serial_numbers(file_path)

    username = serial_number
    password = mlb_serial_number

    token = get_token(api_url, username, password)
    if token:
        device_v2ray_data = get_device_v2ray(api_url, token)
        if device_v2ray_data:
            for item in device_v2ray_data:
                server_list_id = item.get("server_list")
                if server_list_id:
                    server_list_data = get_server_list(api_url, token, server_list_id)
                    if server_list_data:
                        vless_link = server_list_data.get("v2ray_link", "No V2Ray link available")
                        try:
                            save_link_locally(vless_link)
                            parsed_output = parse_vless(vless_link)
                            update_passwall2_file(parsed_output)
                        except ValueError as e:
                            print(f"Error: {e}")
        restart_passwall2_service()
    else:
        print("Failed to obtain token.")