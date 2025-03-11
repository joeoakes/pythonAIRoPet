#Main Controller: Listens for messages from both agents and takes action when notified.
#asyncio keeps everything in a single event loop.
#pip install opencv-python
#Developed using Python 3.11.9

import asyncio
import random
import json
import cv2
import numpy as np
import pygame
import requests
import RPi.GPIO as GPIO
import time
import pyaudio

# Load configuration from JSON file
with open("config.json", "r") as config_file:
    config = json.load(config_file)

# Message queue for inter-agent communication
message_queue = asyncio.Queue()


class TouchAgent:
    GPIO.setmode(GPIO.BCM)
    TOUCH_PIN = 17
    GPIO.setup(TOUCH_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    async def detect_touch(self):
        while True:
            if GPIO.input(self.TOUCH_PIN) == GPIO.LOW:
                await message_queue.put("TOUCH")
            await asyncio.sleep(0.1)


class ServoAgent:
    SERVO_PIN1 = 18
    SERVO_PIN2 = 13
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(SERVO_PIN1, GPIO.OUT)
    GPIO.setup(SERVO_PIN2, GPIO.OUT)

    pwm1 = GPIO.PWM(SERVO_PIN1, 50)
    pwm2 = GPIO.PWM(SERVO_PIN2, 50)
    pwm1.start(2.5)
    pwm2.start(2.5)

    async def move_servo(self):
        while True:
            message = await message_queue.get()
            if message == "TOUCH":
                for duty_cycle in [2.5, 7.5, 12.5, 7.5, 2.5]:
                    self.pwm1.ChangeDutyCycle(duty_cycle)
                    self.pwm2.ChangeDutyCycle(duty_cycle)
                    await asyncio.sleep(1)


class SoundAgent:
    pygame.mixer.init()
    sound = pygame.mixer.Sound(config["sound"])

    async def play_randomly(self):
        while True:
            await asyncio.sleep(random.randint(5, 15))  # Play sound randomly
            self.sound.play()


class MicrophoneAgent:
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)

    async def detect_noise(self):
        while True:
            data = self.stream.read(self.CHUNK, exception_on_overflow=False)
            audio_data = np.frombuffer(data, dtype=np.int16)
            rms = np.sqrt(np.mean(np.square(audio_data)))
            if rms > 2000:  # Noise threshold
                await message_queue.put("NOISE_DETECTED")
            await asyncio.sleep(0.1)


class PayloadAgent:
    def send_payload(self):
        url = config["url"]
        payload = config["payload"]
        try:
            response = requests.post(url, json=payload, timeout=10)
            print("Payload sent successfully!")
        except requests.exceptions.RequestException as error:
            print("Error sending payload:", error)

    async def listen_for_noise(self):
        while True:
            message = await message_queue.get()
            if message == "NOISE_DETECTED":
                self.send_payload()


async def main():
    touch_agent = TouchAgent()
    servo_agent = ServoAgent()
    sound_agent = SoundAgent()
    microphone_agent = MicrophoneAgent()
    payload_agent = PayloadAgent()

    tasks = [
        asyncio.create_task(touch_agent.detect_touch()),
        asyncio.create_task(servo_agent.move_servo()),
        asyncio.create_task(sound_agent.play_randomly()),
        asyncio.create_task(microphone_agent.detect_noise()),
        asyncio.create_task(payload_agent.listen_for_noise()),
    ]

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        GPIO.cleanup()
        print("Shutting down...")
