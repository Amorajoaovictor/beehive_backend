#!/usr/bin/env python3
"""
Simple test script for Beehive Backend API
"""
import requests
import json
import sys

BASE_URL = "http://localhost:5000/api"

def test_health():
    """Test health endpoint"""
    print("Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'healthy'
    print("✅ Health endpoint working")

def test_honeypots():
    """Test honeypots CRUD operations"""
    print("Testing honeypots CRUD...")
    
    # Test creating honeypot
    honeypot_data = {
        "name": "Test SSH Honeypot",
        "type": "ssh",
        "port": 2222
    }
    response = requests.post(f"{BASE_URL}/honeypots", json=honeypot_data)
    assert response.status_code == 201
    honeypot = response.json()
    honeypot_id = honeypot['id']
    assert honeypot['name'] == "Test SSH Honeypot"
    assert honeypot['type'] == "ssh"
    assert honeypot['port'] == 2222
    print("✅ Honeypot creation working")
    
    # Test getting honeypots
    response = requests.get(f"{BASE_URL}/honeypots")
    assert response.status_code == 200
    honeypots = response.json()
    assert len(honeypots) >= 1
    print("✅ Honeypots listing working")
    
    # Test getting single honeypot
    response = requests.get(f"{BASE_URL}/honeypots/{honeypot_id}")
    assert response.status_code == 200
    honeypot = response.json()
    assert honeypot['id'] == honeypot_id
    print("✅ Single honeypot retrieval working")
    
    return honeypot_id

def test_logs(honeypot_id):
    """Test logs CRUD operations"""
    print("Testing logs CRUD...")
    
    # Test creating log
    log_data = {
        "honeypot_id": honeypot_id,
        "ip_address": "192.168.1.100",
        "event_type": "connection_attempt",
        "details": "Test connection attempt"
    }
    response = requests.post(f"{BASE_URL}/logs", json=log_data)
    assert response.status_code == 201
    log = response.json()
    log_id = log['id']
    assert log['honeypot_id'] == honeypot_id
    assert log['ip_address'] == "192.168.1.100"
    assert log['event_type'] == "connection_attempt"
    print("✅ Log creation working")
    
    # Test getting logs
    response = requests.get(f"{BASE_URL}/logs")
    assert response.status_code == 200
    logs = response.json()
    assert len(logs) >= 1
    print("✅ Logs listing working")
    
    # Test filtering logs by honeypot
    response = requests.get(f"{BASE_URL}/logs?honeypot_id={honeypot_id}")
    assert response.status_code == 200
    logs = response.json()
    assert all(log['honeypot_id'] == honeypot_id for log in logs)
    print("✅ Logs filtering by honeypot working")
    
    # Test filtering logs by IP
    response = requests.get(f"{BASE_URL}/logs?ip_address=192.168.1.100")
    assert response.status_code == 200
    logs = response.json()
    assert all(log['ip_address'] == "192.168.1.100" for log in logs)
    print("✅ Logs filtering by IP working")
    
    return log_id

def test_validation():
    """Test input validation"""
    print("Testing validation...")
    
    # Test invalid honeypot type
    response = requests.post(f"{BASE_URL}/honeypots", json={
        "name": "Invalid",
        "type": "invalid",
        "port": 1234
    })
    assert response.status_code == 400
    print("✅ Honeypot type validation working")
    
    # Test missing required field
    response = requests.post(f"{BASE_URL}/honeypots", json={
        "name": "No Port"
    })
    assert response.status_code == 400
    print("✅ Required field validation working")
    
    # Test invalid honeypot_id in logs
    response = requests.post(f"{BASE_URL}/logs", json={
        "honeypot_id": 99999,
        "ip_address": "1.2.3.4",
        "event_type": "test"
    })
    assert response.status_code == 404
    print("✅ Foreign key validation working")

def main():
    """Run all tests"""
    try:
        print("Starting Beehive Backend API Tests")
        print("=" * 40)
        
        test_health()
        honeypot_id = test_honeypots()
        test_logs(honeypot_id)
        test_validation()
        
        print("=" * 40)
        print("🎉 All tests passed!")
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the API. Make sure the server is running on localhost:5000")
        sys.exit(1)
    except AssertionError as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()