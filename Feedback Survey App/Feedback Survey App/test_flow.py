import requests
import time
import subprocess
import os
import signal

# Start server in background
print("Starting server...")
proc = subprocess.Popen(['python', 'App.py'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
time.sleep(3)  # Wait for server to start

try:
    url = 'http://127.0.0.1:5000'
    session = requests.Session()
    
    # Sign up
    print("\n1. Signing up user...")
    import random
    email = f"test{random.randint(1000, 9999)}@example.com"
    resp = session.post(url + '/api/signup', json={
        'name': 'Test User',
        'email': email,
        'password': 'password123',
        'confirm_password': 'password123'
    })
    print(f"Signup response: {resp.status_code}")
    print(resp.json())
    
    # Submit feedback
    print("\n2. Submitting feedback...")
    resp = session.post(url + '/api/submit', json={
        'rating': '5',
        'category': 'Product',
        'message': 'Great product!',
        'recommend': 'Yes'
    })
    print(f"Submit response: {resp.status_code}")
    print(f"Response JSON: {resp.json()}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    # Kill server
    print("\nStopping server...")
    os.kill(proc.pid, signal.SIGTERM)
    proc.wait()
