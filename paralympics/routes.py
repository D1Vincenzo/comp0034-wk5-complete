import datetime

from flask import current_app as app, request, abort, jsonify, make_response
from sqlalchemy import exc
from marshmallow.exceptions import ValidationError

from paralympics import db
from paralympics.models import Region, Event, User
from paralympics.schemas import RegionSchema, EventSchema, UserSchema
from paralympics.helpers import token_required, encode_auth_token

# Flask-Marshmallow Schemas
regions_schema = RegionSchema(many=True)
region_schema = RegionSchema()
events_schema = EventSchema(many=True)
event_schema = EventSchema()
user_schema = UserSchema()


# REGION ROUTES
@app.get("/regions")
def get_regions():
    """Returns a list of NOC region codes and their details in JSON.

    Returns:
        JSON for all the regions, or 500 error if not found
    """
    try:
        # Select all the regions using Flask-SQLAlchemy
        all_regions = db.session.execute(db.select(Region)).scalars()
        # Dump the data using the Marshmallow regions schema; '.dump()' returns JSON.
        try:
            result = regions_schema.dump(all_regions)
            # If all OK then return the data in the HTTP response
            return result
        except ValidationError as e:
            app.logger.error(f"A Marshmallow ValidationError occurred dumping all regions: {str(e)}")
            msg = {'message': "An Internal Server Error occurred."}
            return make_response(msg, 500)
    except exc.SQLAlchemyError as e:
        app.logger.error(f"An error occurred while fetching regions: {str(e)}")
        msg = {'message': "An Internal Server Error occurred."}
        return make_response(msg, 500)


@app.get('/regions/<code>')
def get_region(code):
    """ Returns one region in JSON.

    Returns 404 if the region code is not found in the database.

    Args:
        code (str): The 3 digit NOC code of the region to be searched for

    Returns: 
        JSON for the region if found otherwise 404
    """
    # Query structure shown at https://flask-sqlalchemy.palletsprojects.com/en/3.1.x/queries/#select
    # Try to find the region, if it is ot found, catch the error and return 404
    try:
        region = db.session.execute(db.select(Region).filter_by(NOC=code)).scalar_one()
        # Dump the data using the Marshmallow region schema; '.dump()' returns JSON.
        result = region_schema.dump(region)
        # Return the data in the HTTP response
        return result
    except exc.NoResultFound as e:
        # See https://flask.palletsprojects.com/en/2.3.x/errorhandling/#returning-api-errors-as-json
        app.logger.error(f'Region code {code} was not found. Error: {e}')
        abort(404, description="Region not found")


@app.post('/regions')
def add_region():
    """ Adds a new region.

    Gets the JSON data from the request body and uses this to deserialise JSON to an object using Marshmallow
   region_schema.loads()

    Returns: 
        JSON message  If there is an error, return 400if the issue is with the validation, 500 if there is a
        database issue, otherwise return message 'Region added with NOC= {region.NOC}'
    """
    json_data = request.get_json()
    try:
        region = region_schema.load(json_data)

        try:
            db.session.add(region)
            db.session.commit()
            return {"message": f"Region added with NOC= {region.NOC}"}
        except exc.SQLAlchemyError as e:
            app.logger.error(f"An error occurred saving the Region: {str(e)}")
            msg = {'message': "An Internal Server Error occurred."}
            return make_response(msg, 500)

    except ValidationError as e:
        app.logger.error(f"A Marshmallow ValidationError loading the region: {str(e)}")
        msg = {'message': "The Region details failed validation."}
        return make_response(msg, 400)


@app.delete('/regions/<noc_code>')
def delete_region(noc_code):
    """ Deletes the region with the given code.

    Args:
        param code (str): The 3-character NOC code of the region to delete
    Returns:
        JSON If successful, return success message, other return 500 Internal Server Error
    """
    try:
        region = db.session.execute(db.select(Region).filter_by(NOC=noc_code)).scalar_one()
        db.session.delete(region)
        db.session.commit()
        return {"message": f"Region {noc_code} deleted."}
    except exc.SQLAlchemyError as e:
        # Log the exception with the error
        app.logger.error(f"A SQLAlchemy database error occurred: {str(e)}")
        # Report a 404 error to the user who made the request
        msg_content = f'Region {noc_code} not found.'
        msg = {'message': msg_content}
        return make_response(msg, 404)


@app.patch("/regions/<noc_code>")
@token_required
def update_region(noc_code):
    """Updates changed fields for the specified region.

    Args:
        noc_code (str): 3 character NOC region code

    Returns:
        JSON message
            If the region for the code is not found, return 404
            If the JSON contents are not valid, return 500
            If the update is not saved, return 500
            If all OK then return 200
    """
    app.logger.error(f"Started the patch")
    # Find the region in the database
    try:
        existing_region = db.session.execute(
            db.select(Region).filter_by(NOC=noc_code)
        ).scalar_one_or_none()
    except exc.SQLAlchemyError as e:
        app.logger.error(f"A SQLAlchemy database error occurred: {str(e)}")
        msg_content = f'Region {noc_code} not found'
        msg = {'message': msg_content}
        return make_response(msg, 404)
    # Get the updated details from the json sent in the HTTP patch request
    region_json = request.get_json()
    app.logger.error(f"region_json: {str(region_json)}")
    # Use Marshmallow to update the existing records with the changes from the json
    try:
        region_update = region_schema.load(region_json, instance=existing_region, partial=True)
    except ValidationError as e:
        app.logger.error(f"A Marshmallow schema validation error occurred: {str(e)}")
        msg = f'Failed Marshmallow schema validation'
        return make_response(msg, 500)
    # Commit the changes to the database
    try:
        db.session.add(region_update)
        db.session.commit()
        # Return json message
        response = {"message": f"Region {noc_code} updated."}
        return response
    except exc.SQLAlchemyError as e:
        app.logger.error(f"A SQLAlchemy database error occurred: {str(e)}")
        msg = f'An Internal Server Error occurred.'
        return make_response(msg, 500)


# EVENT ROUTES
@app.get("/events")
def get_events():
    """Returns a list of events and their details in JSON.

    Returns:
        JSON for all events
    """
    all_events = db.session.execute(db.select(Event)).scalars()
    result = events_schema.dump(all_events)
    return result


@app.get('/events/<event_id>')
def get_event(event_id):
    """ Returns the event with the given id JSON.

    Args:
        event_id (int): The id of the event to return
    Returns:
        JSON
    """
    event = db.session.execute(db.select(Event).filter_by(id=event_id)).scalar_one()
    result = event_schema.dump(event)
    return result


@app.post('/events')
def add_event():
    """ Adds a new event.

   Gets the JSON data from the request body and uses this to deserialise JSON to an object using Marshmallow
   event_schema.loads()

   Returns:
        JSON
   """
    ev_json = request.get_json()
    event = event_schema.load(ev_json)
    db.session.add(event)
    db.session.commit()
    return {"message": f"Event added with id= {event.id}"}


@app.delete('/events/<int:event_id>')
def delete_event(event_id):
    """ Deletes the event with the given id.

    Args: 
        event_id (int): The id of the event to delete
    Returns: 
        JSON
    """
    event = db.session.execute(db.select(Event).filter_by(id=event_id)).scalar_one()
    db.session.delete(event)
    db.session.commit()
    return {"message": f"Event {event_id} deleted."}


@app.patch("/events/<event_id>")
def event_update(event_id):
    """ Update fields for the specified event.
    
    Returns:
        JSON message
    """
    # Find the event in the database
    existing_event = db.session.execute(
        db.select(Event).filter_by(event_id=event_id)
    ).scalar_one_or_none()
    # Get the updated details from the json sent in the HTTP patch request
    event_json = request.get_json()
    # Use Marshmallow to update the existing records with the changes from the json
    event_updated = event_schema.load(event_json, instance=existing_event, partial=True)
    # Commit the changes to the database
    db.session.add(event_updated)
    db.session.commit()
    # Return json success message
    response = {"message": f"Event with id={event_id} updated."}
    return response

# Add this route for my CW
@app.delete('/users/<int:user_id>')
def delete_user(user_id):
    """ Deletes the user with the given id.

    Args:
        user_id (int): The id of the user to delete
    Returns:
        JSON
    """
    user = db.session.execute(db.select(User).filter_by(id=user_id)).scalar_one()
    db.session.delete(user)
    db.session.commit()
    return {"message": f"User {user_id} deleted."}


# AUTHENTICATION ROUTES
@app.post("/register")
def register():
    """Register a new user for the REST API

    If successful, return 201 Created.
    If email already exists, return 409 Conflict (resource already exists).
    If any other error occurs, return 500 Server error
    """
    # Get the JSON data from the request
    user_json = request.get_json()
    # Check if user already exists, returns None if the user does not exist
    user = db.session.execute(
        db.select(User).filter_by(email=user_json.get("email"))
    ).scalar_one_or_none()
    if not user:
        try:
            # Create new User object
            user = User(email=user_json.get("email"))
            # Set the hashed password
            user.set_password(password=user_json.get("password"))
            # Add user to the database
            db.session.add(user)
            db.session.commit()
            # Return success message
            response = {
                "message": "Successfully registered.",
                "id": user.id
            }
            # Log the registered user
            app.logger.info(f"{user.email} registered at {datetime.datetime.utcnow()}")
            return make_response(jsonify(response)), 201
        except exc.SQLAlchemyError as e:
            app.logger.error(f"A SQLAlchemy database error occurred: {str(e)}")
            response = {
                "message": "An error occurred. Please try again.",
            }
            return make_response(jsonify(response)), 500
    else:
        response = {
            "message": "User already exists. Please Log in.",
        }
        return make_response(jsonify(response)), 409


@app.post('/login')
def login():
    """Logins in the User and generates a token

    If the email and password are not present in the HTTP request, return 401 error
    If the user is not found in the database, or the password is incorrect, return 401 error
    If the user is logged in and the token is generated, return the token and 201 Success
    """
    auth = request.get_json()

    # Check the email and password are present, if not return a 401 error
    if not auth or not auth.get('email') or not auth.get('password'):
        msg = {'message': 'Missing email or password'}
        return make_response(msg, 401)

    # Find the user in the database
    user = db.session.execute(
        db.select(User).filter_by(email=auth.get("email"))
    ).scalar_one_or_none()

    # If the user is not found, or the password is incorrect, return 401 error
    if not user or not user.check_password(auth.get('password')):
        msg = {'message': 'Incorrect email or password.'}
        return make_response(msg, 401)

    # If all OK then create the token
    token = encode_auth_token(user.id)

    # Return the token and the user_id of the logged in user
    return make_response(jsonify({"user_id": user.id, "token": token}), 201)


# Add this route for my CW
@app.patch("/users/<int:user_id>")
def update_user(user_id):
    """Update the email and/or password of an existing user

    If successful, return 200 OK.
    If the user does not exist, return 404 Not Found.
    If the new email already exists, return 409 Conflict.
    If any other error occurs, return 500 Server error.
    """
    # Get the JSON data from the request
    user_json = request.get_json()
    new_email = user_json.get("email")
    new_password = user_json.get("password")

    try:
        # Find the user by user_id
        user = db.session.query(User).filter_by(id=user_id).first()
        
        if not user:
            return make_response(jsonify({"message": "User not found."})), 404

        # Update email if provided and it's different from the current one
        if new_email and new_email != user.email:
            # Check if the new email already exists
            if db.session.query(db.exists().where(User.email == new_email)).scalar():
                return make_response(jsonify({"message": "Email already in use."})), 409
            user.email = new_email

        # Update password if provided
        if new_password:
            user.set_password(new_password)
        
        # Commit changes to the database
        db.session.commit()
        
        # Log the update
        app.logger.info(f"User {user_id} updated at {datetime.datetime.utcnow()}")
        
        return make_response(jsonify({"message": "User updated successfully."})), 200

    except exc.SQLAlchemyError as e:
        app.logger.error(f"A database error occurred: {str(e)}")
        return make_response(jsonify({"message": "An error occurred. Please try again."})), 500