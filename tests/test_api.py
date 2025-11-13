"""
Tests for the main FastAPI application endpoints
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


class TestMainEndpoints:
    """Test class for main application endpoints"""

    def test_root_redirect(self, client):
        """Test that root endpoint redirects to static index.html"""
        response = client.get("/")
        assert response.status_code == 200
        # Should redirect and serve the static file

    def test_get_activities(self, client):
        """Test getting all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
        
        # Check that we have some activities
        assert len(data) > 0
        
        # Check structure of first activity
        first_activity = list(data.values())[0]
        assert "description" in first_activity
        assert "schedule" in first_activity
        assert "max_participants" in first_activity
        assert "participants" in first_activity
        
        # Check data types
        assert isinstance(first_activity["max_participants"], int)
        assert isinstance(first_activity["participants"], list)


class TestSignupEndpoint:
    """Test class for activity signup functionality"""

    def test_signup_success(self, client):
        """Test successful signup for an activity"""
        # Get available activities first
        response = client.get("/activities")
        activities_data = response.json()
        activity_name = list(activities_data.keys())[0]
        
        # Test signup
        response = client.post(
            f"/activities/{activity_name}/signup?email=newstudent@test.com"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "newstudent@test.com" in data["message"]
        assert activity_name in data["message"]

    def test_signup_nonexistent_activity(self, client):
        """Test signup for non-existent activity returns 404"""
        response = client.post(
            "/activities/NonExistent/signup?email=test@test.com"
        )
        assert response.status_code == 404
        
        data = response.json()
        assert data["detail"] == "Activity not found"

    def test_signup_duplicate_student(self, client):
        """Test that duplicate signup returns error"""
        # Get an activity with existing participants
        response = client.get("/activities")
        activities_data = response.json()
        
        # Find an activity with participants
        activity_name = None
        existing_email = None
        for name, details in activities_data.items():
            if details["participants"]:
                activity_name = name
                existing_email = details["participants"][0]
                break
        
        if activity_name and existing_email:
            response = client.post(
                f"/activities/{activity_name}/signup?email={existing_email}"
            )
            assert response.status_code == 400
            assert "already signed up" in response.json()["detail"]

    def test_signup_activity_full(self, client):
        """Test signup when activity is at max capacity"""
        # First, let's modify an activity to be nearly full
        from src.app import activities
        
        # Find an activity and fill it to capacity
        activity_name = list(activities.keys())[0]
        activity = activities[activity_name]
        max_participants = activity["max_participants"]
        
        # Fill activity to capacity
        activity["participants"] = [f"student{i}@test.com" for i in range(max_participants)]
        
        # Try to add one more
        response = client.post(
            f"/activities/{activity_name}/signup?email=overflow@test.com"
        )
        assert response.status_code == 400
        assert "full" in response.json()["detail"]


class TestRemoveParticipantEndpoint:
    """Test class for participant removal functionality"""

    def test_remove_participant_success(self, client):
        """Test successful removal of a participant"""
        # Get activities and find one with participants
        response = client.get("/activities")
        activities_data = response.json()
        
        activity_name = None
        existing_email = None
        for name, details in activities_data.items():
            if details["participants"]:
                activity_name = name
                existing_email = details["participants"][0]
                break
        
        if activity_name and existing_email:
            response = client.delete(
                f"/activities/{activity_name}/remove?email={existing_email}"
            )
            assert response.status_code == 200
            
            data = response.json()
            assert "message" in data
            assert existing_email in data["message"]
            assert activity_name in data["message"]

    def test_remove_participant_nonexistent_activity(self, client):
        """Test removal from non-existent activity returns 404"""
        response = client.delete(
            "/activities/NonExistent/remove?email=test@test.com"
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_remove_nonexistent_participant(self, client):
        """Test removal of participant not in activity"""
        # Get first activity
        response = client.get("/activities")
        activities_data = response.json()
        activity_name = list(activities_data.keys())[0]
        
        response = client.delete(
            f"/activities/{activity_name}/remove?email=notregistered@test.com"
        )
        assert response.status_code == 404
        assert "not registered" in response.json()["detail"]


class TestDataIntegrity:
    """Test class for data consistency and integrity"""

    def test_signup_and_remove_cycle(self, client):
        """Test complete signup and removal cycle"""
        # Get initial state
        response = client.get("/activities")
        initial_data = response.json()
        activity_name = list(initial_data.keys())[0]
        initial_count = len(initial_data[activity_name]["participants"])
        
        # Sign up new participant
        test_email = "cycletest@test.com"
        response = client.post(
            f"/activities/{activity_name}/signup?email={test_email}"
        )
        assert response.status_code == 200
        
        # Verify participant was added
        response = client.get("/activities")
        updated_data = response.json()
        assert len(updated_data[activity_name]["participants"]) == initial_count + 1
        assert test_email in updated_data[activity_name]["participants"]
        
        # Remove participant
        response = client.delete(
            f"/activities/{activity_name}/remove?email={test_email}"
        )
        assert response.status_code == 200
        
        # Verify participant was removed
        response = client.get("/activities")
        final_data = response.json()
        assert len(final_data[activity_name]["participants"]) == initial_count
        assert test_email not in final_data[activity_name]["participants"]

    def test_multiple_signups_different_activities(self, client):
        """Test that a student can sign up for multiple different activities"""
        response = client.get("/activities")
        activities_data = response.json()
        activity_names = list(activities_data.keys())[:2]  # Get first two activities
        
        test_email = "multisignup@test.com"
        
        # Sign up for multiple activities
        for activity_name in activity_names:
            response = client.post(
                f"/activities/{activity_name}/signup?email={test_email}"
            )
            assert response.status_code == 200
        
        # Verify student is in both activities
        response = client.get("/activities")
        final_data = response.json()
        
        for activity_name in activity_names:
            assert test_email in final_data[activity_name]["participants"]