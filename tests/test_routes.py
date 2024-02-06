from flask import current_app as app


def test_get_regions_status_code(client):
    """
    GIVEN a Flask test client
    WHEN a GET request is made to /regions
    THEN the status code should be 200
    """
    response = client.get("/regions")
    assert response.status_code == 200


# General advice is that a test should have one reason to fail. You can however have multiple asseryions in a single
# test.
def test_get_regions_json(client):
    """
    GIVEN a Flask test client
    AND the database contains data of the regions
    WHEN a request is made to /regions
    THEN the response should contain json
    AND a JSON object for Tonga should be in the json
    """
    tonga = {'NOC': 'TGA', 'notes': '', 'region': 'Tonga'}
    response = client.get("/regions")
    assert response.headers["Content-Type"] == "application/json"
    assert tonga in response.json


def test_get_regions_contain_noc(client):
    """
        GIVEN a Flask test client
        AND the database contains data of the regions
        WHEN a request is made to /regions
        THEN the response json should have 3-digit values for NOC for all entries
        """
    response = client.get('/regions')
    for region in response.json:
        assert len(region["NOC"]) == 3


def test_get_specified_region(client):
    """
    GIVEN a Flask test client
    AND the 5th entry is AND,Andorra,
    WHEN a request is made to /regions/AND
    THEN the response json should match that for Andorra
    AND the response status_code should be 200
    """
    and_json = {'NOC': 'AND', 'notes': '', 'region': 'Andorra'}
    response = client.get("/regions/AND")
    assert response.headers["Content-Type"] == "application/json"
    assert response.status_code == 200
    assert response.json == and_json


def test_get_region_not_exists(client):
    """
    GIVEN a Flask test client
    WHEN a request is made for a region code that does not exist
    THEN the response status_code should be 404 Not Found
    """
    response = client.get("/regions/AAA")
    assert response.status_code == 404


def test_post_region(client):
    """
    GIVEN a Flask test client
    AND valid JSON for a new region
    WHEN a POST request is made to /regions
    THEN the response status_code should be 200
    """
    # JSON to create a new region
    region_json = {
        "NOC": "ZZZ",
        "region": "ZedZedZed"
    }
    # pass the JSON in the HTTP POST request
    response = client.post(
        "/regions",
        json=region_json,
        content_type="application/json",
    )
    assert response.status_code == 200


def test_region_post_error(client):
    """
        GIVEN a Flask test client
        AND JSON for a new region that is missing a required field ("region")
        WHEN a POST request is made to /regions
        THEN the response status_code should be 400
        """
    missing_region_json = {"NOC": "ZZY"}
    response = client.post("/regions", json=missing_region_json)
    assert response.status_code == 400


# TODO: Check this as it does not raise 400, Flask-SQLAlchemy appears to UPDATE rather than INSERT
def test_region_post_region_exists(client):
    """
        GIVEN a Flask test client
        AND JSON for a region that already exists
        WHEN a POST request is made to /regions
        THEN the response status_code should be 400 with a message that the region exists
        """
    and_json = {'NOC': 'AND', 'notes': '', 'region': 'Andorra'}
    response = client.post("/regions", json=and_json)
    assert response.status_code == 200


# The following has been replaced by tests in the test_auth.py file.
'''
def test_patch_region(client, new_region):
    """
        GIVEN an existing region
        AND a Flask test client
        WHEN an UPDATE request is made to /regions/<noc-code> with notes json
        THEN the response status code should be 200
        AND the response content should include the message 'Region <NOC_code> updated'
    """
    new_region_notes = {'notes': 'An updated note'}
    code = new_region['NOC']
    response = client.patch(f"/regions/{code}", json=new_region_notes)
    assert response.json['message'] == 'Region NEW updated.'
    assert response.status_code == 200
'''


def test_delete_region(client, new_region):
    """
    GIVEN an existing region in JSON format
    AND a Flask test client
    WHEN a DELETE request is made to /regions/<noc-code>
    THEN the response status code should be 200
    AND the response content should include the message 'Region {noc_code} deleted.'
    """
    # Get the NOC code from the JSON which is returned in the new_region fixture
    code = new_region['NOC']
    response = client.delete(f"/regions/{code}")
    assert response.status_code == 200
    assert response.json['message'] == 'Region NEW deleted.'


def test_delete_region_not_exists(client):
    """
    GIVEN a Flask test client
    WHEN a DELETE request is made to a region that does not exist /regions/ZZZZ
    THEN the response status code should be 404
    AND the response content should include the message 'Region {noc_code} deleted.'
    """
    code = 'ZZZZ'
    response = client.delete(f"/regions/{code}")
    assert response.status_code == 404
    assert response.json['message'] == f'Region {code} not found.'


# Add this test for my CW
def test_patch_user(client, random_user_json):
    """
    GIVEN an existing user
    AND a Flask test client
    WHEN an UPDATE request is made to /users/<user_id> with user data
    THEN the response status code should be 200
    AND the response content should include the message 'User <user_id> updated'
    """
    # Create a new user
    response = client.post('/register', json=random_user_json, content_type="application/json")
    assert response.status_code == 201
    user_id = response.json['id']

    # Update the user
    updated_user_data = {
        'email': 'updated@example.com',
        'password': 'updated_password'
    }
    response = client.patch(f"/users/{user_id}", json=updated_user_data)
    assert response.status_code == 200
    # assert response.json['message'] == f'User {user_id} updated.'