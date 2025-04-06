import argparse
import io
import time

import requests
from picamera2 import Picamera2

# Server URL (replace <server_ip> with your server's IP)
FASTAPI_URL = (
    "http://192.168.86.128:8000/roastees/"  # Adjust based on your server's IP and port
)

# Initialize Picamera2
camera = Picamera2()
camera_config = camera.create_still_configuration(
    main={"size": (640, 480)}
)  # Adjust resolution as needed
camera.configure(camera_config)
camera.start()
print("Camera initialized")

# Parse command-line arguments
parser = argparse.ArgumentParser(
    description="Capture and upload a photo to the FastAPI server with an optional timer."
)
parser.add_argument(
    "--timer",
    type=float,
    default=0,
    help="Interval in seconds between captures (default: 0 for single capture)",
)
args = parser.parse_args()

# Timer value (0 means single capture, >0 means continuous with delay)
TIMER_INTERVAL = args.timer


def capture_and_upload():
    """Capture a photo and upload it with a user-specified name."""
    try:
        # Get roastee name from user input
        name = input("Enter the name of the roastee: ").strip()
        if not name:
            print("Name cannot be empty.")
            return False

        # Capture image to a BytesIO buffer
        buffer = io.BytesIO()
        camera.capture_file(buffer, format="jpeg")
        buffer.seek(0)  # Reset buffer position to start
        print("Photo captured")

        # Prepare form data for upload
        files = {"photos": ("photo.jpg", buffer, "image/jpeg")}
        data = {"name": name}

        # Send the image and name to the FastAPI server
        response = requests.post(FASTAPI_URL, files=files, data=data, timeout=10)
        response.raise_for_status()  # Raise exception for bad status codes

        # Print the server response
        print(f"Server response: {response.json()}")
        return True

    except requests.exceptions.RequestException as e:
        print(f"Failed to upload to server: {e}")
        return False
    except Exception as e:
        print(f"An error occurred: {e}")
        return False


try:
    if TIMER_INTERVAL <= 0:
        # Single capture mode
        capture_and_upload()
    else:
        # Continuous capture mode with timer
        print(
            f"Starting continuous capture with {TIMER_INTERVAL}-second interval. Press Ctrl+C to stop."
        )
        while True:
            success = capture_and_upload()
            if not success and TIMER_INTERVAL > 0:
                print("Continuing despite error due to timer mode.")
            time.sleep(TIMER_INTERVAL)

except KeyboardInterrupt:
    print("Script interrupted by user")
finally:
    # Cleanup
    camera.stop()
    camera.close()
    print("Camera stopped and closed")
