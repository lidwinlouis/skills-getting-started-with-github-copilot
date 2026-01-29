"""
Tests for the FastAPI application
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add src directory to path to import app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app, activities


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities state before each test"""
    # Store original state
    original_activities = {
        key: {
            "description": details["description"],
            "schedule": details["schedule"],
            "max_participants": details["max_participants"],
            "participants": details["participants"].copy(),
        }
        for key, details in activities.items()
    }
    
    yield
    
    # Restore original state
    for key in activities:
        activities[key]["participants"] = original_activities[key]["participants"].copy()


class TestGetActivities:
    """Tests for GET /activities endpoint"""

    def test_get_activities_returns_all_activities(self, client):
        """Test that GET /activities returns all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) > 0
        assert "Basketball Team" in data
        assert "Soccer Club" in data

    def test_get_activities_contains_required_fields(self, client):
        """Test that activities contain required fields"""
        response = client.get("/activities")
        data = response.json()
        activity = data["Basketball Team"]
        assert "description" in activity
        assert "schedule" in activity
        assert "max_participants" in activity
        assert "participants" in activity


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""

    def test_signup_new_participant(self, client, reset_activities):
        """Test signing up a new participant"""
        response = client.post(
            "/activities/Basketball Team/signup",
            params={"email": "test@example.com"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "test@example.com" in data["message"]

    def test_signup_participant_added_to_activity(self, client, reset_activities):
        """Test that participant is actually added to activity"""
        client.post(
            "/activities/Basketball Team/signup",
            params={"email": "test@example.com"}
        )
        response = client.get("/activities")
        data = response.json()
        assert "test@example.com" in data["Basketball Team"]["participants"]

    def test_signup_duplicate_participant_fails(self, client, reset_activities):
        """Test that signing up the same participant twice fails"""
        # First signup
        client.post(
            "/activities/Basketball Team/signup",
            params={"email": "test@example.com"}
        )
        # Duplicate signup
        response = client.post(
            "/activities/Basketball Team/signup",
            params={"email": "test@example.com"}
        )
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"]

    def test_signup_nonexistent_activity_fails(self, client):
        """Test that signing up for a nonexistent activity fails"""
        response = client.post(
            "/activities/Nonexistent Activity/signup",
            params={"email": "test@example.com"}
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]

    def test_signup_multiple_participants(self, client, reset_activities):
        """Test that multiple participants can sign up"""
        emails = ["student1@example.com", "student2@example.com", "student3@example.com"]
        for email in emails:
            response = client.post(
                "/activities/Soccer Club/signup",
                params={"email": email}
            )
            assert response.status_code == 200

        response = client.get("/activities")
        data = response.json()
        for email in emails:
            assert email in data["Soccer Club"]["participants"]


class TestUnregisterFromActivity:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""

    def test_unregister_existing_participant(self, client, reset_activities):
        """Test unregistering an existing participant"""
        # First signup
        client.post(
            "/activities/Art Club/signup",
            params={"email": "test@example.com"}
        )
        # Then unregister
        response = client.delete(
            "/activities/Art Club/unregister",
            params={"email": "test@example.com"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "Unregistered" in data["message"]

    def test_unregister_removes_participant(self, client, reset_activities):
        """Test that unregistering actually removes the participant"""
        # Signup
        client.post(
            "/activities/Drama Society/signup",
            params={"email": "test@example.com"}
        )
        # Unregister
        client.delete(
            "/activities/Drama Society/unregister",
            params={"email": "test@example.com"}
        )
        # Verify removed
        response = client.get("/activities")
        data = response.json()
        assert "test@example.com" not in data["Drama Society"]["participants"]

    def test_unregister_nonexistent_participant_fails(self, client):
        """Test that unregistering a non-existent participant fails"""
        response = client.delete(
            "/activities/Mathletes/unregister",
            params={"email": "nonexistent@example.com"}
        )
        assert response.status_code == 400
        data = response.json()
        assert "not registered" in data["detail"]

    def test_unregister_nonexistent_activity_fails(self, client):
        """Test that unregistering from nonexistent activity fails"""
        response = client.delete(
            "/activities/Nonexistent Activity/unregister",
            params={"email": "test@example.com"}
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]

    def test_unregister_from_activity_with_existing_participants(self, client, reset_activities):
        """Test unregistering from activities that have existing participants"""
        # Chess Club already has participants
        response = client.delete(
            "/activities/Chess Club/unregister",
            params={"email": "michael@mergington.edu"}
        )
        assert response.status_code == 200
        
        # Verify the participant was removed
        response = client.get("/activities")
        data = response.json()
        assert "michael@mergington.edu" not in data["Chess Club"]["participants"]
        assert "daniel@mergington.edu" in data["Chess Club"]["participants"]


class TestActivityCapacity:
    """Tests for activity capacity limits"""

    def test_get_activities_max_participants(self, client):
        """Test that max_participants field is returned correctly"""
        response = client.get("/activities")
        data = response.json()
        assert data["Basketball Team"]["max_participants"] == 15
        assert data["Soccer Club"]["max_participants"] == 18
        assert data["Mathletes"]["max_participants"] == 10
