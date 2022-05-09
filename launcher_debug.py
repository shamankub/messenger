import subprocess
import time

PROCESS = []
# run_path = "temp/"
run_path = "Lesson_14_Eseneev/"

PROCESS.append(subprocess.Popen(["konsole", "-e", f"python {run_path}server.py"]))
time.sleep(0.5)
for i in range(2):
    PROCESS.append(
        subprocess.Popen(
            ["konsole", "-e", f"python {run_path}client.py -n user{i+1} -p 123456"]
        )
    )
    time.sleep(0.1)
