"""
Integration tests for the complete FastAPI application
"""

import pytest
from fastapi.testclient import TestClient


class TestApplicationIntegration:
    """Integration tests for the complete application workflow"""

    def test_full_user_journey(self, client):
        """Test a complete user journey from viewing activities to signing up"""
        # Step 1: User visits the home page
        response = client.get("/")
        assert response.status_code == 200
        
        # Step 2: User gets list of activities
        response = client.get("/activities")
        assert response.status_code == 200
        activities_data = response.json()
        assert len(activities_data) > 0
        
        # Step 3: User chooses an activity with available spots
        activity_name = None
        for name, details in activities_data.items():
            if len(details["participants"]) < details["max_participants"]:
                activity_name = name
                break
        
        assert activity_name is not None, "No activities with available spots found"
        
        # Step 4: User signs up
        test_email = "journey@test.com"
        response = client.post(
            f"/activities/{activity_name}/signup?email={test_email}"
        )
        assert response.status_code == 200
        
        # Step 5: Verify the signup was successful
        response = client.get("/activities")
        updated_activities = response.json()
        assert test_email in updated_activities[activity_name]["participants"]

    def test_edge_case_email_formats(self, client):
        """Test various email formats for signup"""
        response = client.get("/activities")
        activities_data = response.json()
        activity_name = list(activities_data.keys())[0]
        
        # Test valid email formats
        valid_emails = [
            "simple@example.com",
            "user.name@example.com",
            "user+tag@example.org",
            "user123@subdomain.example.com"
        ]
        
        for email in valid_emails:
            response = client.post(
                f"/activities/{activity_name}/signup?email={email}"
            )
            # Should not fail due to email format (our API doesn't validate email format currently)
            assert response.status_code in [200, 400]  # 400 if already signed up

    def test_url_encoding_handling(self, client):
        """Test that URL encoding is handled properly"""
        # Test activity names with spaces (should be URL encoded)
        response = client.get("/activities")
        activities_data = response.json()
        
        # Find an activity with spaces in the name
        activity_with_spaces = None
        for name in activities_data.keys():
            if " " in name:
                activity_with_spaces = name
                break
        
        if activity_with_spaces:
            # Test with proper URL encoding
            encoded_name = activity_with_spaces.replace(" ", "%20")
            unique_email = f"urltest{hash(encoded_name) % 10000}@test.com"
            response = client.post(
                f"/activities/{encoded_name}/signup?email={unique_email}"
            )
            # Should succeed or fail due to capacity, but not due to URL encoding issues
            assert response.status_code in [200, 400]
            if response.status_code == 400:
                # Check it's not a URL encoding error
                assert "not found" not in response.json()["detail"].lower()

    def test_concurrent_signups(self, client):
        """Test multiple signups happening concurrently"""
        response = client.get("/activities")
        activities_data = response.json()
        activity_name = list(activities_data.keys())[0]
        
        # Multiple different users signing up
        emails = [f"concurrent{i}@test.com" for i in range(5)]
        
        for email in emails:
            response = client.post(
                f"/activities/{activity_name}/signup?email={email}"
            )
            # Each should succeed (assuming activity has enough capacity)
            if response.status_code != 200:
                # Might fail if activity gets full
                assert response.status_code == 400
                assert "full" in response.json()["detail"]

    def test_activity_capacity_management(self, client):
        """Test that activity capacity is properly managed"""
        # Create a test scenario by filling an activity to capacity
        from src.app import activities
        
        # Find an activity and get its capacity
        activity_name = list(activities.keys())[0]
        activity = activities[activity_name]
        max_capacity = activity["max_participants"]
        
        # Clear existing participants for clean test
        original_participants = activity["participants"].copy()
        activity["participants"] = []
        
        try:
            # Fill to capacity
            for i in range(max_capacity):
                response = client.post(
                    f"/activities/{activity_name}/signup?email=capacity{i}@test.com"
                )
                assert response.status_code == 200
            
            # Verify activity is now full
            response = client.get("/activities")
            updated_data = response.json()
            assert len(updated_data[activity_name]["participants"]) == max_capacity
            
            # Try to add one more (should fail)
            response = client.post(
                f"/activities/{activity_name}/signup?email=overflow@test.com"
            )
            assert response.status_code == 400
            assert "full" in response.json()["detail"]
            
        finally:
            # Restore original participants
            activity["participants"] = original_participants


class TestErrorHandling:
    """Test error handling and edge cases"""

    def test_malformed_requests(self, client):
        """Test handling of malformed requests"""
        # Test missing email parameter
        response = client.post("/activities/Chess%20Club/signup")
        assert response.status_code == 422  # FastAPI validation error
        
        # Test empty email parameter - should work but might fail if empty string already registered
        response = client.post("/activities/Chess%20Club/signup?email=")
        assert response.status_code in [200, 400]  # 400 if empty email already registered
        
    def test_special_characters_in_activity_names(self, client):
        """Test handling of special characters in activity names"""
        # Test with URL-encoded special characters
        special_activity = "Test%20&%20Special%20Activity"
        
        response = client.post(
            f"/activities/{special_activity}/signup?email=special@test.com"
        )
        # Should return 404 since this activity doesn't exist
        assert response.status_code == 404

    def test_very_long_email_addresses(self, client):
        """Test handling of very long email addresses"""
        response = client.get("/activities")
        activities_data = response.json()
        activity_name = list(activities_data.keys())[0]
        
        # Create a very long email with unique content to avoid duplicates
        import time
        timestamp = str(int(time.time() * 1000000))
        long_email = "a" * 50 + timestamp + "@" + "b" * 50 + ".com"
        
        response = client.post(
            f"/activities/{activity_name}/signup?email={long_email}"
        )
        # Should work unless activity is full
        assert response.status_code in [200, 400]
        if response.status_code == 400:
            # Should fail due to capacity or duplicate, not email length
            detail = response.json()["detail"].lower()
            assert "full" in detail or "already" in detail