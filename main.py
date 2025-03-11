#Main Controller: Listens for messages from both agents and takes action when notified.
#asyncio keeps everything in a single event loop.
#Developed using Python 3.11.9

import asyncio, random, json, cv2, numpy as np, pygame, requests, RPi.GPIO as GPIO, time, pyaudio

# Load configuration from JSON file
with open("config.json", "r") as config_file:
    config = json.load(config_file)

# Message queue for inter-agent communication
message_queue = asyncio.Queue()


class TouchAgent:
    """Detects touch input and sends a message to the queue."""
    GPIO.setmode(GPIO.BCM)
    TOUCH_PIN = 17
    GPIO.setup(TOUCH_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    async def detect_touch(self):
        while True:
            if GPIO.input(self.TOUCH_PIN) == GPIO.LOW:
                await message_queue.put("TOUCH")
            await asyncio.sleep(0.1)


class ServoAgent:
    """Moves servos when a touch event is detected."""
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
    """Randomly plays one of the sound files specified in the config."""
    pygame.mixer.init()
    sound_files = config["sounds"]
    error_sound = pygame.mixer.Sound("please_connect.wav")

    async def play_randomly(self):
        while True:
            await asyncio.sleep(random.randint(5, 15))  # Wait randomly before playing
            sound = pygame.mixer.Sound(random.choice(self.sound_files))
            sound.play()

    def play_error_sound(self):
        """Play the error sound when payload sending fails."""
        self.error_sound.play()


class MicrophoneAgent:
    """Detects noise levels and sends a message when a noise threshold is exceeded."""
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
    """Sends a JSON payload when a noise or touch event is detected."""

    def __init__(self, sound_agent):
        self.sound_agent = sound_agent

    def send_payload(self, event_type):
        url = config["url"]
        payload = config["payload"]
        payload["event_type"] = event_type  # Include event type in payload
        try:
            response = requests.post(url, json=payload, timeout=10)
            print(f"Payload sent successfully for {event_type}!")
        except requests.exceptions.RequestException as error:
            print(f"Error sending payload for {event_type}:", error)
            self.sound_agent.play_error_sound()  # Play error sound if payload fails

    async def listen_for_events(self):
        while True:
            message = await message_queue.get()
            if message in ["NOISE_DETECTED", "TOUCH"]:
                self.send_payload(message)


async def main():
    """Main function to initialize agents and run tasks asynchronously."""
    touch_agent = TouchAgent()
    servo_agent = ServoAgent()
    sound_agent = SoundAgent()
    microphone_agent = MicrophoneAgent()
    payload_agent = PayloadAgent(sound_agent)

    tasks = [
        asyncio.create_task(touch_agent.detect_touch()),
        asyncio.create_task(servo_agent.move_servo()),
        asyncio.create_task(sound_agent.play_randomly()),
        asyncio.create_task(microphone_agent.detect_noise()),
        asyncio.create_task(payload_agent.listen_for_events()),
    ]

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        GPIO.cleanup()
        print("Shutting down...")
