import os
import requests

# Raw GitHub file URL
GITHUB_FILE_URL = "https://raw.githubusercontent.com/behjaf/google/main/v2ray_server"

# File path for storing server location
SERVER_LOCATION_PATH = "/root/server_location.txt"

def fetch_github_file_content(url):
    try:
        # Send a GET request to the GitHub file URL
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors

        # Return the content of the file
        return response.text
    except requests.exceptions.RequestException as e:
        # Handle any errors during the request
        print(f"An error occurred while fetching the file: {e}")
        return None

# Function to write server address to file
def write_server_address_to_file(server_address):
    try:
        with open(SERVER_LOCATION_PATH, 'w') as file:
            file.write(f"{server_address}")
    except Exception as e:
        print(f"Error writing to file: {e}")

# Function to read the current content of the file
def read_server_address_from_file():
    try:
        if os.path.exists(SERVER_LOCATION_PATH):
            with open(SERVER_LOCATION_PATH, 'r') as file:
                return file.read()
        return None
    except Exception as e:
        print(f"Error reading from file: {e}")
        return None

if __name__ == "__main__":
    # Fetch the content of the GitHub file
    new_content = fetch_github_file_content(GITHUB_FILE_URL)

    if new_content is not None:  # Only update if new content was fetched successfully
        write_server_address_to_file(new_content)
        print("Updated server address:")
        print(new_content)
    else:
        current_content = read_server_address_from_file()
        if current_content is not None:
            print("Failed to fetch new server address. Retaining the current address:")
            print(current_content)
        else:
            print("Failed to fetch new server address and no existing address found.")
