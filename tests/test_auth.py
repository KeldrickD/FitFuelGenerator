def test_register(client):
    """Test registration."""
    response = client.post('/register', data={
        'username': 'newtrainer',
        'email': 'new@example.com',
        'password': 'password123',
        'business_name': 'New Gym'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Registration successful!' in response.data

def test_login_logout(client):
    """Test login and logout functionality."""
    # First register a new user
    client.post('/register', data={
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'password123',
        'business_name': 'Test Gym'
    })

    # Test login
    response = client.post('/login', data={
        'email': 'test@example.com',
        'password': 'password123'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Dashboard' in response.data

    # Test logout
    response = client.get('/logout', follow_redirects=True)
    assert response.status_code == 200
    assert b'You have been logged out' in response.data

def test_invalid_login(client):
    """Test login with invalid credentials."""
    response = client.post('/login', data={
        'email': 'wrong@example.com',
        'password': 'wrongpassword'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Invalid email or password' in response.data

def test_protected_route(client, auth_client):
    """Test accessing protected route with and without authentication."""
    # Test without authentication
    response = client.get('/dashboard', follow_redirects=True)
    assert response.status_code == 200
    assert b'Please log in to access this page' in response.data

    # Test with authentication
    response = auth_client.get('/dashboard')
    assert response.status_code == 200
    assert b'Dashboard' in response.data 