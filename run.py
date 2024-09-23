import subprocess
import os

def start_server(script_name, port):
    """Starts a uvicorn server for a given script on a specific port."""
    # Change the working directory to 'server'
    cwd = os.path.join(os.getcwd(), 'server')

    subprocess.Popen([
        "uvicorn", f"{script_name}:app", 
        "--reload", 
        "--port", str(port)
    ], cwd=cwd)

if __name__ == "__main__":
    # Start server.py on port 8000
    start_server("server", 8000)

    # Start polling_server.py on port 8001
    start_server("polling_server", 8001)

    print("Servers are running:")
    print("  server.py on http://127.0.0.1:8000")
    print("  polling_server.py on http://127.0.0.1:8001")

    # Keep the script running
    try:
        while True:
            pass  # Just keeping the script alive
    except KeyboardInterrupt:
        print("\nShutting down servers...")