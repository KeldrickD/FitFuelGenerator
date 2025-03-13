import os
import tempfile
import pytest
from app import app as flask_app
from extensions import db

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    # Create a temporary file to isolate the database for each test
    db_fd, db_path = tempfile.mkstemp()
    
    # Create the app with test config
    flask_app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'WTF_CSRF_ENABLED': False,
        'SERVER_NAME': 'localhost.localdomain'
    })

    # Create the database and load test data
    with flask_app.app_context():
        db.create_all()
        yield flask_app

    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()

@pytest.fixture
def auth_client(app, client):
    """A test client with authentication."""
    from models import Trainer
    from werkzeug.security import generate_password_hash
    
    with app.app_context():
        # Create a test trainer
        trainer = Trainer(
            username='test_trainer',
            email='test@example.com',
            password_hash=generate_password_hash('password123'),
            business_name='Test Gym'
        )
        db.session.add(trainer)
        db.session.commit()
        
        # Log in
        client.post('/login', data={
            'email': 'test@example.com',
            'password': 'password123'
        }, follow_redirects=True)
        
        return client 