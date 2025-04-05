from picamera2 import Picamera2
import requests
import pygame
import time
import io

# Server URL (replace <server_ip> with your server's IP)
FASTAPI_URL = "http://192.168.86.128:8000/process_frame/"

# Initialize Picamera2
camera = Picamera2()
camera_config = camera.create_still_configuration(main={"size": (640, 480)})  # Adjust resolution as needed
camera.configure(camera_config)
camera.start()
print("Camera initialized")

# Initialize audio playback
#pygame.mixer.init()
print("Pygame mixer initialized")

try:
    while True:
        # Capture image to a BytesIO buffer
        buffer = io.BytesIO()
        camera.capture_file(buffer, format="jpeg")
        buffer.seek(0)  # Reset buffer position to start

        # Send the image to the FastAPI server
        files = {"frame": ("frame.jpg", buffer, "image/jpeg")}
        response = requests.post(FASTAPI_URL, files=files)

        # Play audio if received
        if response.status_code == 200 and response.content:
            print("Received audio")
            #with open("audio.mp3", "wb") as audio_file:
            #    audio_file.write(response.content)
            #pygame.mixer.music.load("audio.mp3")
            #pygame.mixer.music.play()
            #while pygame.mixer.music.get_busy():
            #    time.sleep(0.1)  # Wait for audio to finish playing

        # Wait before next capture
        time.sleep(SEND_INTERVAL)

except KeyboardInterrupt:
    print("Script interrupted by user")
finally:
    # Cleanup
    camera.stop()
    camera.close()
    print("Camera stopped and closed")
