"""
Tests for the Mergington High School Activities API
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities data before each test"""
    # Store original state
    original_activities = {
        activity: {
            "description": details["description"],
            "schedule": details["schedule"],
            "max_participants": details["max_participants"],
            "participants": details["participants"].copy()
        }
        for activity, details in activities.items()
    }
    
    yield
    
    # Restore original state after test
    for activity_name in activities:
        activities[activity_name]["participants"] = original_activities[activity_name]["participants"].copy()


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_static(self, client):
        """Test that root redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_returns_all_activities(self, client):
        """Test that GET /activities returns all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) == 9  # We have 9 activities
        assert "Soccer Team" in data
        assert "Programming Class" in data
    
    def test_activity_structure(self, client):
        """Test that each activity has the correct structure"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_details in data.items():
            assert "description" in activity_details
            assert "schedule" in activity_details
            assert "max_participants" in activity_details
            assert "participants" in activity_details
            assert isinstance(activity_details["participants"], list)


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_successful(self, client):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Chess Club/signup?email=test@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "test@mergington.edu" in data["message"]
        
        # Verify participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "test@mergington.edu" in activities_data["Chess Club"]["participants"]
    
    def test_signup_duplicate_participant(self, client):
        """Test that duplicate signup is rejected"""
        email = "duplicate@mergington.edu"
        
        # First signup
        response1 = client.post(
            f"/activities/Art Studio/signup?email={email}"
        )
        assert response1.status_code == 200
        
        # Second signup (should fail)
        response2 = client.post(
            f"/activities/Art Studio/signup?email={email}"
        )
        assert response2.status_code == 400
        assert "already signed up" in response2.json()["detail"]
    
    def test_signup_nonexistent_activity(self, client):
        """Test signup for non-existent activity"""
        response = client.post(
            "/activities/Nonexistent Activity/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_signup_url_encoded_activity_name(self, client):
        """Test signup with URL-encoded activity name"""
        response = client.post(
            "/activities/Drama%20Club/signup?email=test@mergington.edu"
        )
        assert response.status_code == 200


class TestUnregisterFromActivity:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_successful(self, client):
        """Test successful unregistration from an activity"""
        email = "unregister-test@mergington.edu"
        
        # First, sign up
        client.post(f"/activities/Debate Team/signup?email={email}")
        
        # Then unregister
        response = client.delete(
            f"/activities/Debate Team/unregister?email={email}"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        
        # Verify participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email not in activities_data["Debate Team"]["participants"]
    
    def test_unregister_not_registered(self, client):
        """Test unregistering a participant who is not registered"""
        response = client.delete(
            "/activities/Basketball Club/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == 400
        assert "not registered" in response.json()["detail"].lower()
    
    def test_unregister_nonexistent_activity(self, client):
        """Test unregistering from non-existent activity"""
        response = client.delete(
            "/activities/Fake Activity/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_unregister_existing_participant(self, client):
        """Test unregistering an existing participant"""
        # Use an existing participant
        response = client.delete(
            "/activities/Soccer Team/unregister?email=alex@mergington.edu"
        )
        assert response.status_code == 200
        
        # Verify participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "alex@mergington.edu" not in activities_data["Soccer Team"]["participants"]


class TestEndToEndWorkflow:
    """End-to-end workflow tests"""
    
    def test_complete_signup_and_unregister_workflow(self, client):
        """Test the complete workflow of signing up and unregistering"""
        email = "workflow@mergington.edu"
        activity = "Science Olympiad"
        
        # Get initial participant count
        initial_response = client.get("/activities")
        initial_count = len(initial_response.json()[activity]["participants"])
        
        # Sign up
        signup_response = client.post(
            f"/activities/{activity}/signup?email={email}"
        )
        assert signup_response.status_code == 200
        
        # Verify count increased
        after_signup = client.get("/activities")
        after_signup_count = len(after_signup.json()[activity]["participants"])
        assert after_signup_count == initial_count + 1
        
        # Unregister
        unregister_response = client.delete(
            f"/activities/{activity}/unregister?email={email}"
        )
        assert unregister_response.status_code == 200
        
        # Verify count returned to original
        after_unregister = client.get("/activities")
        after_unregister_count = len(after_unregister.json()[activity]["participants"])
        assert after_unregister_count == initial_count
    
    def test_multiple_activities_signup(self, client):
        """Test signing up for multiple activities"""
        email = "multi@mergington.edu"
        
        # Sign up for multiple activities
        activities_to_join = ["Gym Class", "Programming Class", "Chess Club"]
        
        for activity in activities_to_join:
            response = client.post(
                f"/activities/{activity}/signup?email={email}"
            )
            assert response.status_code == 200
        
        # Verify participant is in all activities
        all_activities = client.get("/activities").json()
        for activity in activities_to_join:
            assert email in all_activities[activity]["participants"]
