import subprocess

PROCESS = []

PROCESS.append(subprocess.Popen(["konsole", "-e", f"python server.py"]))
for i in range(2):
    PROCESS.append(
        subprocess.Popen(
            ["konsole", "-e", f"python client.py -n user{i+1} -p 123456"]
        )
    )
