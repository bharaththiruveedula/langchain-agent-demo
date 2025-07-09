import requests
import unittest
import json
import sys
from datetime import datetime

class OpenShiftClusterManagerAPITester:
    def __init__(self, base_url="https://cc04bbf9-680c-493e-865e-b112d44f5aba.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def run_test(self, name, method, endpoint, expected_status, data=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                self.test_results.append({
                    "name": name,
                    "status": "passed",
                    "response": response.json() if response.text else {}
                })
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                self.test_results.append({
                    "name": name,
                    "status": "failed",
                    "expected": expected_status,
                    "actual": response.status_code,
                    "response": response.json() if response.text else {}
                })

            return success, response.json() if response.text and response.headers.get('content-type', '').startswith('application/json') else {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            self.test_results.append({
                "name": name,
                "status": "error",
                "error": str(e)
            })
            return False, {}

    def test_health_check(self):
        """Test the health check endpoint"""
        return self.run_test(
            "Health Check",
            "GET",
            "health",
            200
        )

    def test_chat(self, message):
        """Test the chat endpoint"""
        return self.run_test(
            "Chat Endpoint",
            "POST",
            "chat",
            200,
            data={
                "id": "test-" + datetime.now().strftime("%Y%m%d%H%M%S"),
                "message": message,
                "sender": "user",
                "timestamp": datetime.now().isoformat()
            }
        )

    def test_chat_history(self):
        """Test the chat history endpoint"""
        return self.run_test(
            "Chat History",
            "GET",
            "chat-history",
            200
        )

    def test_operations(self):
        """Test the operations endpoint"""
        return self.run_test(
            "Operations History",
            "GET",
            "operations",
            200
        )

    def test_create_dns_record(self, fqdn, ip_address):
        """Test creating a DNS record"""
        return self.run_test(
            "Create DNS Record",
            "POST",
            "create-dns-record",
            200,
            data={
                "fqdn": fqdn,
                "ip_address": ip_address
            }
        )

    def test_process_cluster(self, sheets_url):
        """Test processing a cluster from Google Sheets"""
        return self.run_test(
            "Process Cluster",
            "POST",
            "process-cluster",
            200,
            data={
                "sheets_url": sheets_url,
                "action": "create_cluster"
            }
        )

    def print_summary(self):
        """Print a summary of test results"""
        print("\n" + "="*50)
        print(f"📊 Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        print("="*50)
        
        for result in self.test_results:
            status_icon = "✅" if result["status"] == "passed" else "❌"
            print(f"{status_icon} {result['name']}: {result['status'].upper()}")
        
        return self.tests_passed == self.tests_run

class TestOpenShiftClusterManager(unittest.TestCase):
    def setUp(self):
        self.tester = OpenShiftClusterManagerAPITester()
        
    def test_api_endpoints(self):
        # Test health check
        success, health_data = self.tester.test_health_check()
        self.assertTrue(success, "Health check should succeed")
        
        # Test chat endpoint
        success, chat_data = self.tester.test_chat("Hello, I need help with OpenShift cluster management")
        self.assertTrue(success, "Chat endpoint should succeed")
        
        # Test chat history
        success, history_data = self.tester.test_chat_history()
        self.assertTrue(success, "Chat history endpoint should succeed")
        
        # Test operations history
        success, operations_data = self.tester.test_operations()
        self.assertTrue(success, "Operations endpoint should succeed")
        
        # Test DNS record creation
        test_fqdn = f"test-node-{datetime.now().strftime('%H%M%S')}.example.com"
        success, dns_data = self.tester.test_create_dns_record(test_fqdn, "192.168.1.100")
        
        # Test Google Sheets processing
        # Using a sample Google Sheets URL
        sample_sheets_url = "https://docs.google.com/spreadsheets/d/1234567890abcdefghijklmnopqrstuvwxyz/edit"
        success, sheets_data = self.tester.test_process_cluster(sample_sheets_url)
        
        # Print summary
        self.tester.print_summary()

def main():
    # Run as standalone script
    tester = OpenShiftClusterManagerAPITester()
    
    # Test health check
    tester.test_health_check()
    
    # Test chat endpoint
    tester.test_chat("Hello, I need help with OpenShift cluster management")
    
    # Test chat history
    tester.test_chat_history()
    
    # Test operations history
    tester.test_operations()
    
    # Test DNS record creation
    test_fqdn = f"test-node-{datetime.now().strftime('%H%M%S')}.example.com"
    tester.test_create_dns_record(test_fqdn, "192.168.1.100")
    
    # Test Google Sheets processing
    # Using a sample Google Sheets URL
    sample_sheets_url = "https://docs.google.com/spreadsheets/d/1234567890abcdefghijklmnopqrstuvwxyz/edit"
    tester.test_process_cluster(sample_sheets_url)
    
    # Print summary
    success = tester.print_summary()
    return 0 if success else 1

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--unittest":
        unittest.main(argv=['first-arg-is-ignored'])
    else:
        sys.exit(main())