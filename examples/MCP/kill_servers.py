import os
import signal
import subprocess
import time

def kill_mcp_servers():
    """
    Finds processes based on script name and forcefully terminates them with SIGKILL (kill -9).
    """
    print("Attempting to forcefully kill existing MCP server processes (SIGKILL)...")
    # Define the names of the server scripts you might be running
    server_script_names = [
        "lammps_mcp_server.py",
        "mcp_server_http.py",
        "mcp_server_http2.py", # Include any variants you use
        # Add other script names if you use them, e.g., "minimal_mcp_server.py"
    ]

    current_pid = os.getpid()
    killed_count = 0

    for script_name in server_script_names:
        # Use pgrep to find PIDs whose command line contains the script name
        try:
            # -f matches the full command line
            result = subprocess.run(
                ["pgrep", "-f", f"python.*{script_name}"],
                capture_output=True,
                text=True,
                check=False # Don't raise exception if no match
            )

            if result.returncode == 0 and result.stdout:
                # PIDs are newline separated in stdout
                pids_str = result.stdout.strip().split('\n')
                # print(f"Found processes matching '{script_name}': {', '.join(pids_str)}") # Uncomment for more detail

                for pid_str in pids_str:
                    try:
                        pid = int(pid_str)
                        # Don't kill the script that's currently running this function!
                        if pid == current_pid:
                            continue

                        # Attempt to send the SIGKILL signal
                        print(f"Killing PID {pid} ({script_name})...")
                        os.kill(pid, signal.SIGKILL)
                        killed_count += 1
                        # print(f"Sent SIGKILL to PID {pid}") # Uncomment for more detail

                    except ProcessLookupError:
                         # Process already gone - that's fine
                        pass
                    except PermissionError:
                        print(f"Permission denied to kill PID {pid} ({script_name}). You may need sufficient privileges (e.g., sudo).")
                    except ValueError:
                        print(f"Could not parse PID '{pid_str}'.")
                    except Exception as e:
                        print(f"An unexpected error occurred while trying to kill PID {pid} ({script_name}): {e}")

            elif result.returncode == 1:
                 # pgrep exit code 1 means no processes matched
                 pass # No processes found for this script name - just continue

            else:
                # Other non-zero exit code from pgrep indicates an issue
                print(f"Warning: 'pgrep -f python.*{script_name}' returned exit code {result.returncode}. Stderr:\n{result.stderr.strip()}")


        except FileNotFoundError:
            print("\nERROR: 'pgrep' command not found. Cannot automatically kill processes.")
            print("Please install it (e.g., sudo apt install procps).")
            # If pgrep isn't available, we can't proceed with automatic killing
            return # Exit the function

    if killed_count > 0:
        print(f"Attempted to terminate {killed_count} process(es). Waiting 1 second for clean up.")
        time.sleep(1) # Give the system a moment
    else:
        print("No target processes found to terminate.")

    print("Finished forceful termination attempt.")