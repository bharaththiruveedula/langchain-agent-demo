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
        self.test_sheet_url = "https://docs.google.com/spreadsheets/d/1BzoO69YV0oI1aAOFYcXPxetvO7d3XbGmomXcr9OL-yc/edit?usp=sharing"

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

    def test_chat(self, message, test_name="Chat Endpoint"):
        """Test the chat endpoint with a specific message"""
        return self.run_test(
            test_name,
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

    def test_general_chat(self):
        """Test general chat functionality"""
        return self.test_chat(
            "Hello, what can you help me with?",
            "General Chat"
        )

    def test_create_dns_record(self):
        """Test creating a DNS record via chat"""
        return self.test_chat(
            "Hey, can you create a DNS A record for IP 1.2.3.4 and FQDN is test.example.com",
            "Create DNS Record"
        )

    def test_parse_sheets(self):
        """Test parsing Google Sheets via chat"""
        return self.test_chat(
            f"Hey, can you parse google sheet at {self.test_sheet_url} and provide FQDN and subnet and list console IPs of the nodes",
            "Parse Google Sheets"
        )

    def test_allocate_ips(self):
        """Test allocating IPs via chat"""
        return self.test_chat(
            f"Hey, allocate IPs for all the nodes listed in google sheet {self.test_sheet_url} with the subnet",
            "Allocate IPs"
        )

    def test_workflow_progress_dns_record(self):
        """Test workflow progress for DNS record creation"""
        return self.test_chat(
            "Hey, can you create a DNS A record for IP 10.20.30.40 and FQDN is workflow-test.example.com",
            "Workflow Progress - DNS Record"
        )
        
    def test_workflow_progress_sheets_parsing(self):
        """Test workflow progress for Google Sheets parsing"""
        return self.test_chat(
            f"Hey, can you parse google sheet at {self.test_sheet_url} and provide FQDN and subnet and list console IPs",
            "Workflow Progress - Sheets Parsing"
        )
        
    def test_workflow_progress_cluster_creation(self):
        """Test workflow progress for full cluster creation"""
        return self.test_chat(
            f"Hey, I want to build new openshift cluster, details are at google sheet {self.test_sheet_url}",
            "Workflow Progress - Cluster Creation"
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

    def analyze_response(self, response_data, test_name):
        """Analyze the response data for specific test cases"""
        if not response_data:
            print(f"⚠️ No response data for {test_name}")
            return
            
        print(f"\n📋 Response Analysis for {test_name}:")
        
        # Check for message content
        if 'message' in response_data:
            print(f"Message: {response_data['message'][:150]}...")
        
        # Check for workflow progress
        if 'workflow_progress' in response_data and response_data['workflow_progress']:
            progress_steps = response_data['workflow_progress']
            print(f"✅ Workflow progress present with {len(progress_steps)} steps")
            
            # Print workflow progress details
            for i, step in enumerate(progress_steps):
                status_icon = "✅" if step.get("status") == "completed" else "⏳" if step.get("status") == "started" else "❌"
                print(f"  {status_icon} Step {i+1}: {step.get('agent', 'Unknown')} - {step.get('status', 'Unknown')}")
                print(f"    Message: {step.get('message', 'No message')}")
                print(f"    Timestamp: {step.get('timestamp', 'No timestamp')}")
                if step.get('details'):
                    print(f"    Details: {json.dumps(step.get('details'), indent=2)[:100]}...")
                print()
        elif 'workflow_progress' in response_data:
            print("❌ Workflow progress field present but empty")
        else:
            print("❌ No workflow progress in response")
            
        # Check for current agent
        if 'current_agent' in response_data and response_data['current_agent']:
            print(f"✅ Current agent: {response_data['current_agent']}")
        elif 'current_agent' in response_data:
            print("❌ Current agent field present but empty")
        else:
            print("❌ No current agent in response")
            
        # Check for processing status
        if 'processing_status' in response_data and response_data['processing_status']:
            print(f"✅ Processing status: {response_data['processing_status']}")
        elif 'processing_status' in response_data:
            print("❌ Processing status field present but empty")
        else:
            print("❌ No processing status in response")
        
        # Check for table data
        if 'table_data' in response_data and response_data['table_data']:
            print(f"✅ Table data present with {len(response_data['table_data'])} rows")
            # Print first row as sample
            if len(response_data['table_data']) > 0:
                print(f"Sample row: {json.dumps(response_data['table_data'][0], indent=2)}")
        elif 'table_data' in response_data:
            print("Table data field present but empty")
        else:
            print("No table data in response")

class TestOpenShiftClusterManager(unittest.TestCase):
    def setUp(self):
        self.tester = OpenShiftClusterManagerAPITester()
        
    def test_api_endpoints(self):
        # Test health check
        success, health_data = self.tester.test_health_check()
        self.assertTrue(success, "Health check should succeed")
        
        # Test general chat
        success, chat_data = self.tester.test_general_chat()
        self.assertTrue(success, "General chat should succeed")
        
        # Test chat history
        success, history_data = self.tester.test_chat_history()
        self.assertTrue(success, "Chat history endpoint should succeed")
        
        # Test operations history
        success, operations_data = self.tester.test_operations()
        self.assertTrue(success, "Operations endpoint should succeed")
        
        # Test DNS record creation
        success, dns_data = self.tester.test_create_dns_record()
        self.assertTrue(success, "DNS record creation should succeed")
        
        # Test Google Sheets parsing
        success, sheets_data = self.tester.test_parse_sheets()
        self.assertTrue(success, "Google Sheets parsing should succeed")
        
        # Test IP allocation
        success, ip_data = self.tester.test_allocate_ips()
        self.assertTrue(success, "IP allocation should succeed")
        
        # Test cluster creation
        success, cluster_data = self.tester.test_create_cluster()
        self.assertTrue(success, "Cluster creation should succeed")
        
        # Print summary
        self.tester.print_summary()

def main():
    # Run as standalone script
    tester = OpenShiftClusterManagerAPITester()
    
    # Test health check
    success, health_data = tester.test_health_check()
    
    # Test workflow progress features
    print("\n" + "="*50)
    print("TESTING WORKFLOW PROGRESS FEATURES")
    print("="*50)
    
    # Test DNS record creation with workflow progress
    success, dns_data = tester.test_workflow_progress_dns_record()
    tester.analyze_response(dns_data, "Workflow Progress - DNS Record")
    
    # Test Google Sheets parsing with workflow progress
    success, sheets_data = tester.test_workflow_progress_sheets_parsing()
    tester.analyze_response(sheets_data, "Workflow Progress - Sheets Parsing")
    
    # Test cluster creation with workflow progress
    success, cluster_data = tester.test_workflow_progress_cluster_creation()
    tester.analyze_response(cluster_data, "Workflow Progress - Cluster Creation")
    
    # Print summary
    success = tester.print_summary()
    return 0 if success else 1

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--unittest":
        unittest.main(argv=['first-arg-is-ignored'])
    else:
        sys.exit(main())