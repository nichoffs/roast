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
    description="Capture and upload a photo to the FastAPI server with an optional pre-capture delay."
)
parser.add_argument(
    "--timer",
    type=float,
    default=0,
    help="Delay in seconds before capturing the photo (default: 0 for immediate capture)",
)
args = parser.parse_args()

# Timer value (delay before capture)
TIMER_DELAY = args.timer

try:
    # Get roastee name from user input
    name = input("Enter the name of the roastee: ").strip()
    if not name:
        print("Name cannot be empty. Exiting.")
        exit(1)

    # Apply delay if specified
    if TIMER_DELAY > 0:
        print(f"Get ready! Capturing photo in {TIMER_DELAY} seconds...")
        time.sleep(TIMER_DELAY)
    else:
        print("Capturing photo immediately...")

    # Capture image to a BytesIO buffer
    buffer = io.BytesIO()
    camera.capture_file(buffer, format="jpeg")
    buffer.seek(0)  # Reset buffer position to start
    print("Photo captured")

    # Prepare form data for upload
    files = {"photos": ("photo.jpg", buffer, "image/jpeg")}
    data = {"name": name}

    # Send the image and name to the FastAPI server
    try:
        response = requests.post(FASTAPI_URL, files=files, data=data, timeout=10)
        response.raise_for_status()  # Raise exception for bad status codes

        # Print the server response
        print(f"Server response: {response.json()}")
    except requests.exceptions.RequestException as e:
        print(f"Failed to upload to server: {e}")
        exit(1)

except KeyboardInterrupt:
    print("Script interrupted by user")
except Exception as e:
    print(f"An error occurred: {e}")
    exit(1)

finally:
    # Cleanup
    camera.stop()
    camera.close()
    print("Camera stopped and closed")
