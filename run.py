import runpy
import sys

# Ensure repository root is on sys.path for package-style imports
sys.path.insert(0, ".")
runpy.run_path("app/main.py", run_name="__main__")
