from app import create_app
from datetime import timedelta

app = create_app()

def test_session_config():
    with app.app_context():
        lifetime = app.config.get('PERMANENT_SESSION_LIFETIME')
        refresh = app.config.get('SESSION_REFRESH_EACH_REQUEST')
        
        print(f"PERMANENT_SESSION_LIFETIME: {lifetime}")
        print(f"SESSION_REFRESH_EACH_REQUEST: {refresh}")
        
        assert lifetime == timedelta(minutes=60), f"Expected 60m, got {lifetime}"
        assert refresh is True, "Expected SESSION_REFRESH_EACH_REQUEST to be True"
        print("Session configuration test passed!")

if __name__ == "__main__":
    test_session_config()
