"""
Test configuration and fixtures for FastAPI tests
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app

@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture
def sample_activities():
    """Sample activities data for testing"""
    return {
        "Test Activity": {
            "description": "A test activity for unit tests",
            "schedule": "Test Schedule",
            "max_participants": 5,
            "participants": ["test1@example.com", "test2@example.com"]
        }
    }

@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities to known state before each test"""
    from src.app import activities
    
    # Store original activities
    original_activities = activities.copy()
    
    yield
    
    # Restore original activities after test
    activities.clear()
    activities.update(original_activities)