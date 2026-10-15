"""Inert parent/child/grandchild RSS fixture; no scientific data or imports."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

folder, depth = Path(sys.argv[1]), int(sys.argv[2])
stopping = False
independent_session = False

def stop(signum, frame):
    global stopping
    stopping = True

def change_session(signum, frame):
    global independent_session
    os.setsid()
    independent_session = True

signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)
if depth == 2:
    signal.signal(signal.SIGUSR1, change_session)
allocated_bytes = (24 + 8 * depth) * 1024**2
payload = bytearray(allocated_bytes)
for offset in range(0, len(payload), 4096):
    payload[offset] = (depth + 1)
child = None
if depth < 2:
    child = subprocess.Popen([sys.executable, '-B', __file__, str(folder), str(depth + 1)])
record = {'synthetic': True, 'software_validation_only': True, 'depth': depth,
          'pid': os.getpid(), 'ppid': os.getppid(), 'session': os.getsid(0),
          'pgrp': os.getpgrp(), 'allocated_and_touched_bytes': allocated_bytes}
with (folder / ('node-' + str(depth) + '-ready.json')).open('x') as stream:
    json.dump(record, stream)
    stream.write('\n')
announced = False
while not stopping:
    if independent_session and not announced:
        with (folder / 'grandchild-independent-session.json').open('x') as stream:
            json.dump({'pid': os.getpid(), 'ppid': os.getppid(),
                       'session': os.getsid(0), 'pgrp': os.getpgrp()}, stream)
            stream.write('\n')
        announced = True
    time.sleep(0.025)
if child is not None:
    child.wait(timeout=5)
