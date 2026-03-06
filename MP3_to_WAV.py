import os
import random
from pathlib import Path
import subprocess

# Paths to FFmpeg executables
ffmpeg_path = r".\ffmpeg.exe"
ffprobe_path = r".\ffprobe.exe"

dir_path = str(Path.cwd())
sound_folder_path = os.path.join(dir_path, "Data", "Sound")
input_folder = sound_folder_path
output_folder = os.path.join(dir_path, "Data", "WAV_Segments")

window_length = 30  # seconds
min_windows = 30
max_windows = 50

# Function to get MP3 duration in seconds using ffprobe
def get_mp3_duration(mp3_path):
    result = subprocess.run(
        [ffprobe_path, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", mp3_path],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())

# Loop through all folders and MP3 files
for root, dirs, files in os.walk(input_folder):

    # Relative class folder
    relative_path = os.path.relpath(root, input_folder)
    output_class_folder = os.path.join(output_folder, relative_path)
    os.makedirs(output_class_folder, exist_ok=True)

    for file in files:
        if file.lower().endswith(".mp3"):
            mp3_path = os.path.join(root, file)
            print(f"Processing {file} in {root}")

            try:
                duration = get_mp3_duration(mp3_path)
            except Exception as e:
                print(f"Failed to get duration for {file}: {e}")
                continue

            if duration < window_length:
                print(f"Skipping {file} (too short)")
                continue

            n_windows = random.randint(min_windows, max_windows)

            for i in range(n_windows):
                start = random.uniform(0, duration - window_length)
                output_name = f"{Path(file).stem}_{i}.wav"
                output_path = os.path.join(output_class_folder, output_name)

                # Use ffmpeg to extract segment directly to WAV
                cmd = [
                    ffmpeg_path,
                    "-ss", str(start),
                    "-t", str(window_length),
                    "-i", mp3_path,
                    "-ar", "16000",   # 16 kHz
                    "-ac", "1",       # mono
                    "-y",             # overwrite if exists
                    output_path
                ]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

print("Finished dataset creation.")