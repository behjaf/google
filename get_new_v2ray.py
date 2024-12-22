import os
import requests
import re
import urllib.parse
import subprocess


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


# Parse VLESS link
def parse_vless(vless_link):
    match = re.match(r"^vless://([a-fA-F0-9-]+)@([a-zA-Z0-9\.\-]+):(\d+)", vless_link)
    if not match:
        raise ValueError("Invalid VLESS link format: Could not extract UUID, address, or port.")

    uuid, address, port = match.groups()

    if "?" in vless_link:
        params_and_fragment = vless_link.split("?", 1)[1]
    else:
        raise ValueError("Invalid VLESS link format: Missing query parameters.")

    if "#" in params_and_fragment:
        params, fragment = params_and_fragment.split("#", 1)
        remarks = re.sub(r"%[0-9A-Fa-f]{2}", lambda m: chr(int(m.group(0)[1:], 16)), fragment)
    else:
        params = params_and_fragment
        remarks = "No remarks"

    params_dict = {k: v for k, v in (param.split("=", 1) for param in params.split("&"))}
    encryption = params_dict.get("encryption", "none")
    security = params_dict.get("security", "")
    sni = params_dict.get("sni", "")
    fingerprint = params_dict.get("fp", "")
    transport = params_dict.get("type", "")
    ws_host = params_dict.get("host", "")
    ws_path = urllib.parse.unquote(params_dict.get("path", ""))

    output = f"""
    config nodes 'lFQCkuzv'
	option tls '1'
	option protocol 'vless'
	option encryption '{encryption}'
	option add_from '导入'
	option port '{port}'
	option ws_path '{ws_path}'
	option remarks '{remarks}'
	option add_mode '1'
	option ws_host '{ws_host}'
	option type 'Xray'
	option timeout '60'
	option fingerprint '{fingerprint}'
	option tls_serverName '{sni}'
	option address '{address}'
	option tls_allowInsecure '1'
	option uuid '{uuid}'
	option transport '{transport}'
	""".strip()

    return output


# Update Passwall2 configuration file
def update_passwall2_file(new_config):
    file_path = "/etc/config/passwall2"

    with open(file_path, "r", encoding="utf-8") as file:
        lines = file.readlines()

    start_index = None
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip().startswith("config nodes 'lFQCkuzv'"):
            start_index = i
            break

    if start_index is not None:
        end_index = start_index + 1
        while end_index < len(lines) and lines[end_index].strip().startswith("option"):
            end_index += 1
        del lines[start_index:end_index]

    lines.append(new_config + "\n")

    with open(file_path, "w", encoding="utf-8") as file:
        file.writelines(lines)

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
