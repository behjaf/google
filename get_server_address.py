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
        return f"An error occurred: {e}"


# Function to write server address to file
def write_server_address_to_file(server_address):
    try:
        with open(SERVER_LOCATION_PATH, 'w') as file:
            file.write(f"{server_address}")
    except Exception as e:
        print(f"Error writing to file: {e}")


if __name__ == "__main__":
    # Fetch and print the content of the GitHub file
    content = fetch_github_file_content(GITHUB_FILE_URL)
    write_server_address_to_file(content)
    print(content)
