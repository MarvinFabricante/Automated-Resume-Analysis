import sys
import subprocess
print("Python:", sys.version)
print("Chrome check:")
subprocess.run(["google-chrome", "--version"])
