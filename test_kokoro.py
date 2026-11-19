from kokoro_onnx import Kokoro
import soundfile as sf

model = Kokoro(
    "models/kokoro/kokoro-v1.0.int8.onnx",
    "models/kokoro/voices-v1.0.bin"
)

samples, sample_rate = model.create(
    "Hello! This is a test of my free local AI voice generator.",
    voice="af_heart",
    speed=1.0,
    lang="en-us"
)

sf.write("models/kokoro/test_voice.wav", samples, sample_rate)

print("Voice generated successfully!")
print("Sample rate:", sample_rate)
print("Duration:", round(len(samples) / sample_rate, 2), "seconds")
