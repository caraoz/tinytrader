import os
import subprocess
import time

# Define the virtual environment's Python executable
current_dir = os.path.dirname(os.path.abspath(__file__))
venv_python = os.path.join(current_dir, "../venv", "bin", "python")

# List of services to start, assuming they are in the 'server' directory
services = [
    {"name": "Order Ingestion Service", "script": "order_ingestion_service.py", "port": 8000},
    {"name": "Order Book Service", "script": "order_book_service.py", "port": 8001},
    {"name": "Matching Engine Service", "script": "matching_engine_service.py", "port": 8002},
    {"name": "Trade Execution Service", "script": "trade_execution_service.py", "port": 8003},
    {"name": "Notification Service", "script": "notification_service.py", "port": 8004},
    {"name": "User Management Service", "script": "user_management_service.py", "port": 8007},
    {"name": "Persistence Service", "script": "persistence_service.py", "port": 8005},
]

processes = []

try:
    for service in services:
        service_name = service['name']
        script_path = os.path.join(current_dir, service['script'])
        port = service['port']

        command = f"{venv_python} {script_path}"
        print(f"Starting {service_name} on port {port} with command: {command}...")

        proc = subprocess.Popen([venv_python, script_path])
        processes.append(proc)
        
        # Give each service a moment to start up to avoid race conditions
        time.sleep(1)

    # Wait for all processes to complete (infinite wait to keep the orchestrator running)
    for proc in processes:
        proc.wait()

except KeyboardInterrupt:
    print("Shutting down services...")
    for proc in processes:
        proc.terminate()
        proc.wait()