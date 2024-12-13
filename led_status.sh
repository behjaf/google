URL_TELEGRAM="https://telegram.org"
URL_GOOGLE="https://www.google.com"
PROXY="socks5h://127.0.0.1:1070"

# Initialize status variable
status="unknown"

# Check connection to Google
curl -v -L --max-time 8 $URL_GOOGLE > /dev/null 2>&1
if [ $? -eq 0 ]; then
    # Google is accessible, check Telegram via proxy
    curl -v -L -x $PROXY --max-time 10 $URL_TELEGRAM > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        # Both Google and Telegram are accessible
        status="green-blue"
    else
        # Google accessible, Telegram not accessible
        status="green-red"
    fi
else
    # Google not accessible
    status="red-heartbeat"
fi

# Function to update LED state only if it needs to change
update_led() {
    local led_path=$1
    local desired_state=$2
    # Extract the current state (inside [...])
    local current_state=$(cat $led_path | grep -o "\[.*\]" | tr -d '[]')
    if [ "$current_state" != "$desired_state" ]; then
        echo $desired_state > $led_path
    fi
}

# Set LEDs based on status
case $status in
    "green-blue")
        update_led "/sys/class/leds/LED0_Red/trigger" "none"
        update_led "/sys/class/leds/LED0_Green/trigger" "default-on"
        update_led "/sys/class/leds/LED0_Blue/trigger" "default-on"
        ;;
    "green-red")
        update_led "/sys/class/leds/LED0_Red/trigger" "default-on"
        update_led "/sys/class/leds/LED0_Green/trigger" "default-on"
        update_led "/sys/class/leds/LED0_Blue/trigger" "none"
        ;;
    "red-heartbeat")
        update_led "/sys/class/leds/LED0_Red/trigger" "heartbeat"
        update_led "/sys/class/leds/LED0_Green/trigger" "none"
        update_led "/sys/class/leds/LED0_Blue/trigger" "none"
        ;;
    *)
        # Fallback case (shouldn't happen)
        update_led "/sys/class/leds/LED0_Red/trigger" "none"
        update_led "/sys/class/leds/LED0_Green/trigger" "none"
        update_led "/sys/class/leds/LED0_Blue/trigger" "none"
        ;;
esac
