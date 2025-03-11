#Sonic Agent: Runs an async loop to read the sensor and sends notifications when an object is detected.
#Camera Agent: Captures frames asynchronously and processes them for object detection.
#Main Controller: Listens for messages from both agents and takes action when notified.
#asyncio keeps everything in a single event loop.
#pip install opencv-python
#Developed using Python 3.11.9

import asyncio
import random  # Simulating sensor data
import cv2
import numpy as np
import pygame
import requests
import RPi.GPIO as GPIO
import time

# Message queue for inter-agent communication
message_queue = asyncio.Queue()

class SonicAgent:
    """Asynchronous Sonic Sensor Agent"""

    def __init__(self, threshold=10):
        self.threshold = threshold  # Distance threshold in cm

    async def detect_object(self):
        while True:
            await asyncio.sleep(1)  # Simulate sensor reading delay
            distance = random.uniform(5, 20)  # Simulated ultrasonic sensor reading

            if distance < self.threshold:
                await message_queue.put(f"SonicAgent: Object detected at {distance:.2f} cm")

            print(f"SonicAgent: Distance = {distance:.2f} cm")


class CameraAgent:
    """Asynchronous Camera Agent"""

    def __init__(self, camera_index=0):
        self.cap = cv2.VideoCapture(camera_index)

    async def detect_object(self):
        while True:
            await asyncio.sleep(2)  # Simulate frame processing delay
            ret, frame = self.cap.read()
            if not ret:
                print("CameraAgent: Failed to capture image")
                continue

            # Simulated object detection (randomly trigger detection)
            if random.random() > 0.7:
                await message_queue.put("CameraAgent: Object detected in frame")

            print("CameraAgent: Captured frame.")

    def release(self):
        """Release the camera resource"""
        self.cap.release()

class TouchAgent:
    # Set up GPIO using BCM numbering
    GPIO.setmode(GPIO.BCM)

    # Define the GPIO pin connected to the touch sensor (adjust as needed)
    TOUCH_PIN = 17

    # Configure the sensor pin as an input.
    # Using a pull-up resistor here; if your sensor outputs HIGH when touched,
    # you may need to change the pull direction.
    GPIO.setup(TOUCH_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    print("Monitoring touch sensor. Press Ctrl+C to exit.")

    try:
        while True:
            # If the sensor outputs LOW when touched
            if GPIO.input(TOUCH_PIN) == GPIO.LOW:
                print("Touch sensor activated!")
            else:
                print("Touch sensor inactive.")
            time.sleep(0.1)  # Short delay for debouncing and to reduce CPU load
    except KeyboardInterrupt:
        print("\nExiting program.")
    finally:
        GPIO.cleanup()  # Clean up GPIO resources when exiting

class ServoAgent:
    # Define the GPIO pin where the servo is connected
    SERVO_PIN = 18
    SERVO_PIN2 = 13

    # Set up the GPIO using BCM numbering
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(SERVO_PIN, GPIO.OUT)
    GPIO.setup(SERVO_PIN2, GPIO.OUT)

    # Initialize PWM on the servo pin at 50Hz
    pwm = GPIO.PWM(SERVO_PIN, 50)
    pwm.start(2.5)  # Start at 0° position (duty cycle may vary based on your servo)
    pwm2 = GPIO.PWM(SERVO_PIN2, 50)
    pwm2.start(2.5)

    try:
        # Move to 0° (approximately 2.5% duty cycle)
        pwm.ChangeDutyCycle(2.5)
        pwm2.ChangeDutyCycle(2.5)
        time.sleep(1)

        # Move to 90° (approximately 7.5% duty cycle)
        pwm.ChangeDutyCycle(7.5)
        pwm2.ChangeDutyCycle(7.5)
        time.sleep(1)

        # Move to 180° (approximately 12.5% duty cycle)
        pwm.ChangeDutyCycle(12.5)
        pwm2.ChangeDutyCycle(12.5)
        time.sleep(1)

        # Optionally, return to 0°
        pwm.ChangeDutyCycle(2.5)
        pwm2.ChangeDutyCycle(2.5)
        time.sleep(1)

    finally:
        # Stop PWM and clean up GPIO settings
        pwm.stop()
        pwm2.stop()
        GPIO.cleanup()

class SoundAgent:
    # Initialize pygame mixer
    pygame.mixer.init()
    pygame.mixer.music.set_volume(1.0)  # Max volume (range is 0.0 to 1.0)

    # Load sound file
    sound = pygame.mixer.Sound("cat_purr.wav")  # Replace with your file

    # Play the sound
    sound.play()

class PayloadAgent:
    def send_payload(resident_id, resident_room, pet_id, pet_name):
        # Replace with your web service URL
        url = "http://192.168.1.236:5000/api/receive"

        # Construct the JSON payload
        payload = {
            "resident_id": resident_id,
            "resident_room": resident_room,
            "pet_id": pet_id,
            "pet_name": pet_name
        }

        try:
            # Send a POST request with the JSON payload
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()  # Raise an error for bad status codes
            print("Payload successfully sent!")
            print("Response:", response.json())
        except requests.exceptions.RequestException as error:
            print("Error sending payload:", error)

class MainController:
    """Main Controller listening for notifications"""
    print(f"MainController Active")
    async def listen_for_notifications(self):
        while True:
            message = await message_queue.get()
            print(f"MainController: Received -> {message}")


async def main():
    sonic_agent = SonicAgent()
    camera_agent = CameraAgent()
    controller = MainController()

    # Run agents asynchronously
    tasks = [
        asyncio.create_task(sonic_agent.detect_object()),
        asyncio.create_task(camera_agent.detect_object()),
        asyncio.create_task(controller.listen_for_notifications()),
    ]

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Shutting down...")
