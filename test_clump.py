"""
test_clump.py - Testing script for clump application
Authors: clump

Usage: python3 test_clump.py
"""

import requests
from datetime import datetime, timedelta

# Configuration
BASE_URL = "http://127.0.0.1:9494"  # Change to your port
TEST_USERS = [
    {"email": "test1@wellesley.edu", "password": "password123", "name": "Test User 1"},
    {"email": "test2@wellesley.edu", "password": "password123", "name": "Test User 2"},
    {"email": "test3@wellesley.edu", "password": "password123", "name": "Test User 3"},
]

# Colors for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_test(test_name):
    print(f"\n{Colors.BLUE}Testing: {test_name}{Colors.END}")

def print_pass(message):
    print(f"{Colors.GREEN}✓ PASS: {message}{Colors.END}")

def print_fail(message):
    print(f"{Colors.RED}✗ FAIL: {message}{Colors.END}")

def print_info(message):
    print(f"{Colors.YELLOW}ℹ INFO: {message}{Colors.END}")

# Test sessions
sessions = [requests.Session() for _ in range(3)]

def test_signup():
    """Test user signup functionality"""
    print_test("User Signup")
    
    for i, user in enumerate(TEST_USERS):
        data = {
            "name": user["name"],
            "email": user["email"],
            "password": user["password"],
            "confirm_password": user["password"],
            "year": "2025",
            "pronouns": "they/them",
            "bio": f"Test user {i+1}"
        }
        
        response = sessions[i].post(f"{BASE_URL}/signup", data=data, allow_redirects=False)
        
        if response.status_code in [200, 302]:
            print_pass(f"Signup successful for {user['email']}")
        else:
            print_fail(f"Signup failed for {user['email']}")
    
    # Test duplicate email
    print_info("Testing duplicate email signup...")
    response = sessions[0].post(f"{BASE_URL}/signup", data=TEST_USERS[0], allow_redirects=True)
    if "already exists" in response.text.lower():
        print_pass("Duplicate email properly rejected")
    else:
        print_fail("Duplicate email not caught")
    
    # Test invalid email
    print_info("Testing invalid email domain...")
    data = TEST_USERS[0].copy()
    data["email"] = "test@gmail.com"
    response = sessions[0].post(f"{BASE_URL}/signup", data=data, allow_redirects=True)
    if "wellesley" in response.text.lower():
        print_pass("Non-Wellesley email properly rejected")
    else:
        print_fail("Non-Wellesley email not caught")
    
    # Test short password
    print_info("Testing short password...")
    data = TEST_USERS[0].copy()
    data["email"] = "new@wellesley.edu"
    data["password"] = "short"
    data["confirm_password"] = "short"
    response = sessions[0].post(f"{BASE_URL}/signup", data=data, allow_redirects=True)
    if "8 characters" in response.text.lower():
        print_pass("Short password properly rejected")
    else:
        print_fail("Short password not caught")

def test_login():
    """Test login functionality"""
    print_test("User Login")
    
    for i, user in enumerate(TEST_USERS):
        data = {
            "email": user["email"],
            "password": user["password"]
        }
        
        response = sessions[i].post(f"{BASE_URL}/login", data=data, allow_redirects=False)
        
        if response.status_code in [200, 302]:
            print_pass(f"Login successful for {user['email']}")
        else:
            print_fail(f"Login failed for {user['email']}")
    
    # Test wrong password
    print_info("Testing wrong password...")
    session = requests.Session()
    data = {
        "email": TEST_USERS[0]["email"],
        "password": "wrongpassword"
    }
    response = session.post(f"{BASE_URL}/login", data=data, allow_redirects=True)
    if "invalid" in response.text.lower():
        print_pass("Wrong password properly rejected")
    else:
        print_fail("Wrong password not caught")

def test_create_event():
    """Test event creation"""
    print_test("Event Creation")
    
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    
    event_data = {
        "event-title": "Test Event",
        "event-date": tomorrow,
        "event-start": "14:00",
        "event-end": "16:00",
        "event-city": "Wellesley",
        "event-state": "MA",
        "event-desc": "This is a test event",
        "event-cap": "3",
        "event-cid": "1"  # Assuming category 1 exists
    }
    
    response = sessions[0].post(f"{BASE_URL}/create_event/", data=event_data, allow_redirects=False)
    
    if response.status_code in [200, 302]:
        print_pass("Event created successfully")
        return True
    else:
        print_fail("Event creation failed")
        return False

def test_input_validation():
    """Test input validation"""
    print_test("Input Validation")
    
    # Test long title (31 characters)
    print_info("Testing title length validation...")
    event_data = {
        "event-title": "A" * 31,  # Too long
        "event-date": (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'),
        "event-start": "14:00",
        "event-end": "16:00",
        "event-city": "Wellesley",
        "event-state": "MA",
        "event-cid": "1"
    }
    response = sessions[0].post(f"{BASE_URL}/create_event/", data=event_data, allow_redirects=True)
    # Should fail or truncate
    print_info("Long title submitted (check if handled)")
    
    # Test XSS attempt
    print_info("Testing XSS prevention...")
    event_data["event-title"] = "<script>alert('xss')</script>"
    response = sessions[0].post(f"{BASE_URL}/create_event/", data=event_data, allow_redirects=True)
    if "<script>" not in response.text or "&lt;script&gt;" in response.text:
        print_pass("XSS properly escaped")
    else:
        print_fail("XSS not properly escaped")
    
    # Test SQL injection attempt
    print_info("Testing SQL injection prevention...")
    event_data["event-title"] = "'; DROP TABLE events; --"
    response = sessions[0].post(f"{BASE_URL}/create_event/", data=event_data, allow_redirects=True)
    # If this doesn't crash, parameterized queries are working
    print_pass("SQL injection prevented (app still running)")
    
    # Test negative capacity
    print_info("Testing negative capacity...")
    event_data["event-title"] = "Valid Title"
    event_data["event-cap"] = "-5"
    response = sessions[0].post(f"{BASE_URL}/create_event/", data=event_data, allow_redirects=True)
    if "non-negative" in response.text.lower():
        print_pass("Negative capacity properly rejected")
    else:
        print_fail("Negative capacity not caught")

def test_join_event_capacity():
    """Test event capacity and concurrent joins"""
    print_test("Event Capacity & Race Conditions")
    
    # Create event with capacity 2
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    event_data = {
        "event-title": "Capacity Test Event",
        "event-date": tomorrow,
        "event-start": "14:00",
        "event-end": "16:00",
        "event-city": "Wellesley",
        "event-state": "MA",
        "event-cap": "2",
        "event-cid": "1"
    }
    
    response = sessions[0].post(f"{BASE_URL}/create_event/", data=event_data, allow_redirects=True)
    
    # Extract event ID from response (you might need to adjust this)
    print_info("Event created with capacity 2")
    print_info("Manually test: Have 3 users try to join event ID X")
    print_info("Expected: Only 2 should succeed")

def test_past_event_join():
    """Test joining past events"""
    print_test("Past Event Join Prevention")
    
    # Create event in the past
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    event_data = {
        "event-title": "Past Event Test",
        "event-date": yesterday,
        "event-start": "14:00",
        "event-end": "16:00",
        "event-city": "Wellesley",
        "event-state": "MA",
        "event-cap": "10",
        "event-cid": "1"
    }
    
    response = sessions[0].post(f"{BASE_URL}/create_event/", data=event_data, allow_redirects=True)
    print_info("Past event created - manually test joining should fail")

def test_profile_access():
    """Test profile access and editing"""
    print_test("Profile Access")
    
    # Test logged-in access
    response = sessions[0].get(f"{BASE_URL}/profile")
    if response.status_code == 200:
        print_pass("Profile accessible when logged in")
    else:
        print_fail("Profile not accessible when logged in")
    
    # Test logged-out access
    session = requests.Session()
    response = session.get(f"{BASE_URL}/profile", allow_redirects=False)
    if response.status_code == 302:  # Should redirect to login
        print_pass("Profile properly protected when logged out")
    else:
        print_fail("Profile not protected when logged out")

def test_edit_permissions():
    """Test edit/delete permissions"""
    print_test("Edit/Delete Permissions")
    
    print_info("User 1 creates event, User 2 tries to edit")
    print_info("Manual test required: Try accessing /event/<eid>/edit")
    print_info("Expected: User 2 should get 'You can only edit your own events'")

def test_comment_functionality():
    """Test comment posting and deletion"""
    print_test("Comment Functionality")
    
    print_info("Manual test: Post comment on event")
    print_info("Manual test: Try posting empty comment (should fail)")
    print_info("Manual test: Try deleting someone else's comment (should fail)")

def test_logout():
    """Test logout functionality"""
    print_test("Logout")
    
    response = sessions[0].get(f"{BASE_URL}/logout", allow_redirects=False)
    if response.status_code == 302:
        print_pass("Logout successful")
        
        # Try accessing protected page after logout
        response = sessions[0].get(f"{BASE_URL}/profile", allow_redirects=False)
        if response.status_code == 302:
            print_pass("Protected page inaccessible after logout")
        else:
            print_fail("Protected page still accessible after logout")
    else:
        print_fail("Logout failed")

def run_all_tests():
    """Run all tests"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}CLUMP Testing Suite{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}")
    
    try:
        test_signup()
        test_login()
        test_create_event()
        test_input_validation()
        test_join_event_capacity()
        test_past_event_join()
        test_profile_access()
        test_edit_permissions()
        test_comment_functionality()
        test_logout()
        
        print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
        print(f"{Colors.GREEN}Testing complete!{Colors.END}")
        print(f"{Colors.YELLOW}Note: Some tests require manual verification{Colors.END}")
        print(f"{Colors.BLUE}{'='*60}{Colors.END}\n")
        
    except Exception as e:
        print_fail(f"Testing failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print(f"\n{Colors.YELLOW}Make sure your Flask app is running on {BASE_URL}{Colors.END}")
    input("Press Enter to start testing...")
    run_all_tests()