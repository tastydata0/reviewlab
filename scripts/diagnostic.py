import subprocess
import sys
import os

def check_command(cmd, name):
    print(f"Checking {name} ({cmd})... ", end="", flush=True)
    try:
        # We use --version or similar to check if it's really there and executable
        if name == "checkstyle":
             # checkstyle wrapper script
             result = subprocess.run([cmd, "--version"], capture_output=True, text=True, timeout=5)
        else:
             result = subprocess.run([cmd, "--version"], capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0 or (name == "flake8" and result.returncode == 0):
            print("OK ✅")
            return True
        else:
            print(f"FAILED ❌ (exit code {result.returncode})")
            return False
    except FileNotFoundError:
        print("NOT FOUND ❌")
        return False
    except Exception as e:
        print(f"ERROR ❌ ({str(e)})")
        return False

def run_diagnostics():
    print("=== Worker Self-Diagnostic ===")
    
    # Check PATH
    print(f"PATH: {os.environ.get('PATH')}")
    
    checks = [
        ("flake8", "Flake8 (Python)"),
        ("cppcheck", "Cppcheck (C++)"),
        ("checkstyle", "Checkstyle (Java)"),
    ]
    
    all_ok = True
    for cmd, name in checks:
        if not check_command(cmd, name):
            all_ok = False
            
    # Check Java separately
    print("Checking Java Runtime... ", end="", flush=True)
    try:
        res = subprocess.run(["java", "-version"], capture_output=True, text=True, timeout=5)
        print("OK ✅")
    except:
        print("NOT FOUND ❌ (Checkstyle will not work)")
        all_ok = False

    print("==============================")
    if not all_ok:
        print("CRITICAL: Some diagnostics failed! The worker might not function correctly.")
        # We don't exit with 1 here to allow the container to start anyway if needed, 
        # but we could if we wanted it to be a hard failure.
        # sys.exit(1)
    else:
        print("All diagnostics passed. Ready to start.")

if __name__ == "__main__":
    run_diagnostics()
