import time
import subprocess

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
        print(f"File not found: {e}")
        return "error"
    except Exception as e:
        print(f"Unexpected error: {e}")
        return "error"


# Retry logic with check for consecutive 'green-red' status
def retry_request(func, max_retries=4, delay=15, consecutive_threshold=4):
    consecutive_green_red = 0  # Counter for consecutive 'green-red' status

    for attempt in range(max_retries):
        response = func()

        if response == "green-blue":
            print("VPN connected. Resetting green-red counter.")
            consecutive_green_red = 0  # Reset counter
            return response

        elif response == "green-red":
            consecutive_green_red += 1
            print(f"'green-red' status detected {consecutive_green_red}/{consecutive_threshold} times.")

            # Check if threshold is reached
            if consecutive_green_red == consecutive_threshold:
                print(f"'green-red' status detected {consecutive_threshold} times consecutively. Running a.py...")
                subprocess.run(["python3", "a.py"])
                consecutive_green_red = 0  # Reset counter after running the script

        else:
            print(f"Unknown or error status: {response}. Resetting green-red counter.")
            consecutive_green_red = 0  # Reset counter

        # Wait before retrying
        if attempt < max_retries - 1:  # No need to sleep after the last attempt
            print(f"Retry {attempt + 1}/{max_retries} failed. Retrying in {delay} seconds...")
            time.sleep(delay)

    print("Maximum retries reached.")
    return "failed"


# Execute with retries
device_response = retry_request(detect_status_from_led, max_retries=10, delay=15)

if device_response == "failed":
    print("Failed to detect the LED status.")
else:
    print(f"Detected status: {device_response}")
