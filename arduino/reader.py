import serial
import sys
import time
import csv
from datetime import datetime
import os

PORT = "COM5"  # Change this to your COM port number
BAUD = 9600

capturing = False
total_pickups = 0
total_seconds = 0.0
all_sessions = []

try:
    ser = serial.Serial(PORT, BAUD, timeout=1)
except serial.SerialException as e:
    print(f"ERROR: Could not connect to {PORT}: {e}")
    print("Make sure the Arduino is plugged in and the port is correct.")
    sys.exit(1)

print("Connected to Arduino on " + PORT)
print("Flip switch ON to start, OFF to save CSV")
print("--------------------------------------------")
time.sleep(2)

try:
    while True:
        line = ser.readline().decode("utf-8", errors="ignore").strip()
        if not line:
            continue
        print(line)

        if "SESSION END" in line:
            capturing = True
            total_pickups = 0
            total_seconds = 0.0
            all_sessions = []
        if capturing:
            if line.startswith("TOTAL_PICKUPS,"):
                total_pickups = int(line.split(",")[1])
            elif line.startswith("TOTAL_SECONDS,"):
                total_seconds = float(line.split(",")[1])
            elif line.startswith("SESSION,"):
                parts = line.split(",")
                all_sessions.append({
                    "session": int(parts[1]),
                    "seconds": float(parts[2])
                })
            elif "END DATA" in line:
                capturing = False

                project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                logs_dir = os.path.join(project_dir, "logs")
                os.makedirs(logs_dir, exist_ok=True)
                filename = os.path.join(logs_dir, "pickedup.csv")

                file_exists = os.path.isfile(filename)
                with open(filename, "a", newline="") as csvfile:
                    writer = csv.writer(csvfile)
                    if not file_exists:
                        writer.writerow(["iteration", "time_held"])
                    for s in all_sessions:
                        writer.writerow([s["session"], s["seconds"]])

                print(f"\nCSV saved to {filename}")
                print("--------------------------------------------")
                print("Flip switch ON to start a new session")

except KeyboardInterrupt:
    print("Stopped.")
finally:
    ser.close()
