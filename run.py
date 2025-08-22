from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify
from flask_socketio import SocketIO, join_room, leave_room, emit
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
from datetime import datetime, timedelta
import threading
import time
import random
import math

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
# Use environment variable for database URL or fallback to SQLite
import os
database_url = os.environ.get('DATABASE_URL', 'sqlite:///pong.db')
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
# Use threading async mode to avoid requiring eventlet/gevent in local/dev
# For Vercel, we'll use threading mode which is more compatible
socketio = SocketIO(app, async_mode='threading', manage_session=False, cors_allowed_origins="*")


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Room(db.Model):
    id = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    type = db.Column(db.String(20), nullable=False, default='public')  # public/private
    password = db.Column(db.String(255), nullable=True)  # store hashed or plain for demo
    mode = db.Column(db.String(20), nullable=False, default='pvp')  # pvp / bot
    win_points = db.Column(db.Integer, nullable=False, default=5)  # points needed to win
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, nullable=True, default=datetime.utcnow)


# In-memory active room state for Pong
active_rooms = {}
# active_rooms[room_id] = {
#   'members': set([username,...]),
#   'mode': 'pvp' or 'bot',
#   'players': {'left': username, 'right': username}, # in bot mode: left='Computer', right=username
#   'game_state': {
#     'ball': {'x': 400, 'y': 300, 'dx': 5, 'dy': 3},
#     'paddles': {'left': {'y': 250}, 'right': {'y': 250}},
#     'score': {'left': 0, 'right': 0}
#   },
#   'game_running': False,
#   'winner': None,
#   'rematch_votes': set(['left','right']),
#   'rematch_requested': False,
#   'rematch_pending': set(),
#   'room_creator': username
# }


def init_database():
    """Initialize database with proper migration"""
    with app.app_context():
        # For Vercel, use in-memory database if we can't write to filesystem
        try:
            # Create all tables
            db.create_all()
            
            # Check if win_points column exists in room table, if not add it
            try:
                # Try to query win_points to see if column exists
                db.session.execute(db.text('SELECT win_points FROM room LIMIT 1'))
            except Exception:
                # Column doesn't exist, add it
                print("Adding missing win_points column to room table...")
                try:
                    db.session.execute(db.text('ALTER TABLE room ADD COLUMN win_points INTEGER DEFAULT 5'))
                    db.session.commit()
                    print("Successfully added win_points column")
                except Exception as e:
                    print(f"Error adding win_points column: {e}")
                    db.session.rollback()
            
            print("Database initialized successfully")
        except Exception as e:
            print(f"Database initialization failed: {e}")
            # For Vercel, this might be expected due to read-only filesystem
            # The app will still work with in-memory data
            pass

init_database()

@app.route("/")
def landing():
    if "username" in session:
        return redirect(url_for("dashboard"))
    return render_template('landing.html')

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        
        if not username or not password:
            flash("Username and password cannot be empty", "error")
            return render_template("login.html")
        
        user = User.query.filter_by(username=username).first()
        if not user:
            flash("Username not registered", "error")
            return render_template("login.html")
        
        if not user.check_password(password):
            flash("Incorrect password", "error")
            return render_template("login.html")
        
        session["username"] = user.username
        session["user_id"] = user.id
        return redirect(url_for("dashboard"))
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        
        if not username:
            flash("Username needs to be filled", "error")
            return render_template("register.html")
        
        if not password:
            flash("Password needs to be filled", "error")
            return render_template("register.html")
        
        if User.query.filter_by(username=username).first():
            flash("Username unavailable", "error")
            return render_template("register.html")
        
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        session["username"] = user.username
        session["user_id"] = user.id
        flash("Registered", "success")
        return redirect(url_for("dashboard"))
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "username" not in session:
        return redirect(url_for("login"))
    
    if request.method == "POST":
        room_name = request.form["room_name"].strip()
        room_type = request.form["room_type"]
        mode = request.form.get("room_mode", "pvp")
        win_points = int(request.form.get("win_points", 5)) if request.form.get("win_points") else 5
        password = request.form.get("password") if room_type == "private" else None
        room_id = str(uuid.uuid4())

        new_room = Room(
            id=room_id,
            name=room_name,
            type=room_type,
            password=password,
            mode=mode,
            win_points=win_points,
            created_by=session.get("user_id"),
            created_at=datetime.utcnow()
        )
        
        # Try to add win_points if column doesn't exist
        try:
            db.session.add(new_room)
            db.session.commit()
        except Exception as e:
            # If win_points column doesn't exist, try to add it and retry
            if "win_points" in str(e):
                print("win_points column missing, attempting to add it...")
                try:
                    db.session.rollback()
                    db.session.execute(db.text('ALTER TABLE room ADD COLUMN win_points INTEGER DEFAULT 5'))
                    db.session.commit()
                    # Now try to add the room again
                    db.session.add(new_room)
                    db.session.commit()
                    print("Successfully added room after adding win_points column")
                except Exception as e2:
                    print(f"Failed to add win_points column: {e2}")
                    db.session.rollback()
                    # Fallback: create room without win_points
                    new_room = Room(
                        id=room_id,
                        name=room_name,
                        type=room_type,
                        password=password,
                        mode=mode,
                        created_by=session.get("user_id"),
                        created_at=datetime.utcnow()
                    )
                    db.session.add(new_room)
                    db.session.commit()
            else:
                raise e

        # initialize in-memory state for Pong
        active_rooms[room_id] = {
            'members': set(),
            'mode': mode,
            'win_points': win_points,
            'players': {'left': None, 'right': None},
            'game_state': {
                'ball': {'x': 400, 'y': 300, 'dx': 4, 'dy': 2},  # Use consistent starting values
                'paddles': {'left': {'y': 250}, 'right': {'y': 250}},
                'score': {'left': 0, 'right': 0}
            },
            'game_running': False,
            'winner': None,
            'rematch_votes': set(),
            'rematch_requested': False,
            'rematch_pending': set(),
            'room_creator': session["username"]
        }
        
        # Emit realtime room update to all connected users
        socketio.emit('room_created', {
            'room': {
                'id': room_id,
                'name': room_name,
                'type': room_type,
                'mode': mode,
                'players': 0,
                'win_points': win_points,
                'created_by': session["username"]
            }
        })
        
        return redirect(url_for("game", room_id=room_id))
    
    # list rooms with simple counts from in-memory when available
    try:
        # Cleanup: delete rooms with zero members older than 5 minutes
        now_utc = datetime.utcnow()
        to_delete_ids = []
        for r in Room.query.all():
            members = active_rooms.get(r.id, {}).get('members', set())
            member_count = len(members)
            created_at = r.created_at or now_utc
            room_age = (now_utc - created_at)
            if member_count == 0 and room_age > timedelta(minutes=5):
                to_delete_ids.append(r.id)

        if to_delete_ids:
            for rid in to_delete_ids:
                # Remove from memory
                active_rooms.pop(rid, None)
                # Remove from DB
                stale_room = Room.query.filter_by(id=rid).first()
                if stale_room:
                    db.session.delete(stale_room)
            db.session.commit()
            # Notify dashboards to update
            for rid in to_delete_ids:
                socketio.emit('room_dissolved', {'room_id': rid})

        # Build fresh list after cleanup
        all_rooms = Room.query.all()
        room_list = []
        for r in all_rooms:
            count = len(active_rooms.get(r.id, {}).get('members', set()))
            creator_name = "Unknown"
            if r.created_by:
                creator = User.query.get(r.created_by)
                if creator:
                    creator_name = creator.username
            # Get win_points from database
            win_points = getattr(r, 'win_points', 5)  # Fallback to 5 if column doesn't exist
            room_list.append({
                'id': r.id,
                'name': r.name,
                'type': r.type,
                'mode': r.mode,
                'players': count,
                'win_points': win_points,
                'created_by': creator_name
            })
    except Exception as e:
        print(f"Error loading rooms: {e}")
        room_list = []
    
    return render_template("dashboard.html", rooms=room_list)

@app.route("/game/<room_id>")
def game(room_id):
    if "username" not in session:
        return redirect(url_for("login"))
    room = Room.query.filter_by(id=room_id).first()
    if not room:
        return redirect(url_for("dashboard"))

    # private room: require password once, then mark access in session
    if room.type == 'private':
        # Check if user is the room creator - they get immediate access
        if room.created_by == session.get("user_id"):
            # Room creator gets immediate access
            ra = session.get('room_access', {})
            ra[room_id] = True
            session['room_access'] = ra
        else:
            # Other users need password
            allowed = session.get('room_access', {}).get(room_id)
            if not allowed:
                supplied = request.args.get('password') or request.form.get('password')
                if not supplied:
                    flash('Enter the password to join this private room', 'error')
                    return redirect(url_for('dashboard'))
                if room.password != supplied:
                    flash('Incorrect password for this room', 'error')
                    return redirect(url_for('dashboard'))
                # mark access
                ra = session.get('room_access', {})
                ra[room_id] = True
                session['room_access'] = ra

    # ensure in-memory state exists
    if room_id not in active_rooms:
        creator_name = "Unknown"
        if room.created_by:
            creator = User.query.get(room.created_by)
            if creator:
                creator_name = creator.username
        
        active_rooms[room_id] = {
            'members': set(),
            'mode': room.mode,
            'win_points': getattr(room, 'win_points', 5),  # Fallback to 5 if column doesn't exist
            'players': {'left': None, 'right': None},
            'game_state': {
                'ball': {'x': 400, 'y': 300, 'dx': 5, 'dy': 3},
                'paddles': {'left': {'y': 250}, 'right': {'y': 250}},
                'score': {'left': 0, 'right': 0}
            },
            'game_running': False,
            'winner': None,
            'rematch_votes': set(),
            'rematch_requested': False,
            'rematch_pending': set(),
            'room_creator': creator_name
        }
    return render_template("game.html", room_id=room_id, username=session["username"])

@socketio.on("disconnect")
def handle_disconnect():
    username = session.get("username")
    if username:
        # Remove user from all active rooms
        rooms_to_clean = []
        for room_id, state in active_rooms.items():
            if username in state['members']:
                state['members'].discard(username)
                
                # Clear paddle assignment
                if state['players']['left'] == username:
                    state['players']['left'] = None
                elif state['players']['right'] == username:
                    state['players']['right'] = None
                
                # Stop game if running and player disconnected
                if state['game_running']:
                    state['game_running'] = False
                    state['winner'] = None
                
                # Emit room update
                socketio.emit('room_updated', {
                    'room_id': room_id,
                    'players': len(state['members'])
                })
                
                # Notify remaining players
                socketio.emit("user_left", {
                    "username": username,
                    "players": state['players'],
                    "members": list(state['members'])
                }, room=room_id)
                
                # Mark room for cleanup if empty
                if len(state['members']) == 0:
                    rooms_to_clean.append(room_id)
        
        # Clean up empty rooms
        for room_id in rooms_to_clean:
            del active_rooms[room_id]
        
        # No global user disconnected broadcast needed

@socketio.on("join_room")
def handle_join(data):
    room_id = data.get("room_id") or data.get("room")
    if not room_id:
        emit("error", {"message": "room_id required"})
        return
    username = session.get("username")
    if not username:
        emit("error", {"message": "Not authenticated"})
        return

    room = Room.query.filter_by(id=room_id).first()
    if not room:
        emit("error", {"message": "Room not found"})
        return

    # private room access check
    if room.type == 'private':
        # Check if user is the room creator - they get immediate access
        if room.created_by == session.get("user_id"):
            # Room creator gets immediate access
            ra = session.get('room_access', {})
            ra[room_id] = True
            session['room_access'] = ra
        else:
            # Other users need password
            allowed = session.get('room_access', {}).get(room_id)
            supplied = data.get('password')
            if not allowed and (not supplied or supplied != room.password):
                emit("error", {"message": "Wrong room password"})
                return

    # initialize state if needed
    state = active_rooms.get(room_id)
    if not state:
        creator_name = "Unknown"
        if room.created_by:
            creator = User.query.get(room.created_by)
            if creator:
                creator_name = creator.username
        
        state = {
            'members': set(),
            'mode': room.mode,
            'win_points': getattr(room, 'win_points', 5),  # Fallback to 5 if column doesn't exist
            'players': {'left': None, 'right': None},
            'game_state': {
                'ball': {'x': 400, 'y': 300, 'dx': 4, 'dy': 2},  # Use consistent starting values
                'paddles': {'left': {'y': 250}, 'right': {'y': 250}},
                'score': {'left': 0, 'right': 0}
            },
            'game_running': False,
            'winner': None,
            'rematch_votes': set(),
            'rematch_requested': False,
            'rematch_pending': set(),
            'room_creator': creator_name
        }
        active_rooms[room_id] = state

    # enforce player limit (bot mode allows only 1 human)
    current_players = state['members']
    max_humans = 1 if state.get('mode') == 'bot' else 2
    if len(current_players) >= max_humans and username not in current_players:
        emit("error", {"message": f"Room full ({max_humans} player{'s' if max_humans>1 else ''} max)"})
        return

    join_room(room_id)
    state['members'].add(username)
    
    # assign paddle positions (left/right)
    your_paddle = None
    if state['mode'] == 'bot':
        # In bot mode: Computer is left, player is right
        state['players']['left'] = 'Computer'
        state['players']['right'] = username
        your_paddle = 'right'
    else:
        # PvP mode: assign positions as players join
        if state['players']['left'] is None:
            state['players']['left'] = username
            your_paddle = 'left'
        elif state['players']['right'] is None:
            state['players']['right'] = username
            your_paddle = 'right'
        else:
            # already assigned, find existing assignment
            your_paddle = 'left' if state['players']['left'] == username else ('right' if state['players']['right'] == username else None)

    # Emit realtime room update to dashboard
    socketio.emit('room_updated', {
        'room_id': room_id,
        'players': len(state['members'])
    })

    # notify the joiner with game state
    emit('pong_init', {
        'game_state': state['game_state'],
        'game_running': state['game_running'],
        'winner': state['winner'],
        'you': your_paddle,
        'players': state['players'],
        'mode': state['mode'],
        'win_points': state.get('win_points', 5),
        'room_creator': state['room_creator'],
        'is_creator': username == state['room_creator']
    })
    
    # notify room about players update
    emit("players_update", {
        "players": state['players'],
        "members": list(state['members']),
        "room_creator": state['room_creator']
    }, room=room_id)

def _check_winner(score, win_points=5):
    """Check if someone won (first to win_points)"""
    if score['left'] >= win_points:
        return 'left'
    elif score['right'] >= win_points:
        return 'right'
    return None

def _update_computer_paddle(game_state):
    """Update computer paddle position with smooth AI for new dimensions"""
    ball = game_state['ball']
    computer_paddle = game_state['paddles']['left']
    
    paddle_height = 80  # Updated to match new paddle height
    canvas_height = 600  # Updated to match new canvas height
    paddle_width = 10
    left_paddle_x = 10
    
    # Initialize AI state if not present
    if 'ai_state' not in computer_paddle:
        computer_paddle['ai_state'] = {
            'target_y': 250,  # Updated center position
            'current_velocity': 0,
            'reaction_delay': 0,
            'last_ball_x': ball['x'],
            'prediction_time': 0
        }
    
    ai_state = computer_paddle['ai_state']
    
    # Only react when ball is moving towards computer paddle
    if ball['dx'] < 0:  # Ball moving left
        # Calculate time until ball reaches paddle
        time_to_paddle = (ball['x'] - left_paddle_x - paddle_width) / abs(ball['dx']) if ball['dx'] != 0 else 0
        
        # Predict where ball will be when it reaches the paddle
        predicted_y = ball['y'] + (ball['dy'] * time_to_paddle)
        
        # Add some prediction error (makes AI more human-like)
        prediction_error = random.uniform(-20, 20)  # Slightly increased for taller canvas
        predicted_y += prediction_error
        
        # Target is center of paddle aligned with predicted ball position
        target_y = predicted_y - (paddle_height // 2)
        
        # Add reaction delay (AI doesn't react instantly)
        ai_state['reaction_delay'] = max(0, ai_state['reaction_delay'] - 1)
        if ai_state['reaction_delay'] > 0:
            target_y = ai_state['target_y']  # Keep previous target during delay
        
        # Occasionally miss the target (human-like mistakes)
        if random.random() < 0.02:  # 2% chance of mistake
            target_y += random.uniform(-40, 40)  # Increased range for taller canvas
        
        ai_state['target_y'] = target_y
        ai_state['prediction_time'] = time_to_paddle
    else:
        # Ball moving away, slowly return to center
        ai_state['target_y'] = (canvas_height - paddle_height) // 2
        ai_state['reaction_delay'] = random.randint(3, 8)  # Random reaction delay
    
    # Clamp target to valid range
    ai_state['target_y'] = max(0, min(canvas_height - paddle_height, ai_state['target_y']))
    
    # Current paddle position
    current_y = computer_paddle['y']
    
    # Smooth movement with acceleration/deceleration
    target_velocity = (ai_state['target_y'] - current_y) * 0.08  # Proportional control
    
    # Limit maximum velocity for smooth movement
    max_velocity = 1.5  # Slightly increased for taller canvas
    target_velocity = max(-max_velocity, min(max_velocity, target_velocity))
    
    # Smooth acceleration
    acceleration = 0.15  # Slightly increased for more responsive movement
    if target_velocity > ai_state['current_velocity']:
        ai_state['current_velocity'] = min(target_velocity, ai_state['current_velocity'] + acceleration)
    elif target_velocity < ai_state['current_velocity']:
        ai_state['current_velocity'] = max(target_velocity, ai_state['current_velocity'] - acceleration)
    
    # Apply velocity to position
    new_y = current_y + ai_state['current_velocity']
    
    # Ensure paddle stays within bounds
    new_y = max(0, min(canvas_height - paddle_height, new_y))
    
    # If we hit the boundary, stop velocity in that direction
    if new_y <= 0 or new_y >= canvas_height - paddle_height:
        ai_state['current_velocity'] = 0
    
    computer_paddle['y'] = new_y
    
    # Update last ball position for next frame
    ai_state['last_ball_x'] = ball['x']

def _update_ball_position(game_state):
    """Update ball position and handle collisions with improved physics"""
    ball = game_state['ball']
    paddles = game_state['paddles']
    score = game_state['score']
    
    # Update ball position
    ball['x'] += ball['dx']
    ball['y'] += ball['dy']
    
    # Constants to match client rendering - adjusted dimensions
    ball_radius = 8
    canvas_width = 800
    canvas_height = 600  # Increased height for better proportions
    left_paddle_x = 10
    right_paddle_x = canvas_width - 20
    paddle_width = 10
    paddle_height = 80  # Slightly taller paddles

    # Ball collision with top and bottom walls
    if ball['y'] <= ball_radius:
        ball['y'] = ball_radius
        ball['dy'] = abs(ball['dy'])  # Bounce down
    elif ball['y'] >= canvas_height - ball_radius:
        ball['y'] = canvas_height - ball_radius
        ball['dy'] = -abs(ball['dy'])  # Bounce up
    
    # Ball collision with paddles - improved collision detection
    # Left paddle collision
    if (ball['x'] - ball_radius <= left_paddle_x + paddle_width and 
        ball['x'] + ball_radius >= left_paddle_x and 
        ball['y'] + ball_radius >= paddles['left']['y'] and 
        ball['y'] - ball_radius <= paddles['left']['y'] + paddle_height):
        
        # Ensure ball doesn't get stuck inside paddle
        ball['x'] = left_paddle_x + paddle_width + ball_radius
        
        # Calculate relative intersection point (-1 to 1)
        relative_intersect_y = (paddles['left']['y'] + (paddle_height/2)) - ball['y']
        normalized_relative_intersection_y = relative_intersect_y / (paddle_height/2)
        
        # Clamp to prevent extreme angles
        normalized_relative_intersection_y = max(-0.8, min(0.8, normalized_relative_intersection_y))
        
        # Calculate bounce angle (between -30 and 30 degrees for more controlled gameplay)
        bounce_angle = normalized_relative_intersection_y * (math.pi/6)  # 30 degrees max angle
        
        # Calculate new direction with controlled speed increase
        current_speed = math.sqrt(ball['dx']**2 + ball['dy']**2)
        new_speed = min(current_speed * 1.02, 12)  # Max speed cap to prevent runaway
        
        ball['dx'] = new_speed * math.cos(bounce_angle)
        ball['dy'] = -new_speed * math.sin(bounce_angle)
        
        # Ensure ball moves right after hitting left paddle
        ball['dx'] = abs(ball['dx'])
        
        # Ensure minimum horizontal speed to prevent vertical-only movement
        if abs(ball['dx']) < 2:
            ball['dx'] = 2 if ball['dx'] > 0 else -2
    
    # Right paddle collision
    if (ball['x'] + ball_radius >= right_paddle_x and 
        ball['x'] - ball_radius <= right_paddle_x + paddle_width and 
        ball['y'] + ball_radius >= paddles['right']['y'] and 
        ball['y'] - ball_radius <= paddles['right']['y'] + paddle_height):
        
        # Ensure ball doesn't get stuck inside paddle
        ball['x'] = right_paddle_x - ball_radius
        
        # Calculate relative intersection point (-1 to 1)
        relative_intersect_y = (paddles['right']['y'] + (paddle_height/2)) - ball['y']
        normalized_relative_intersection_y = relative_intersect_y / (paddle_height/2)
        
        # Clamp to prevent extreme angles
        normalized_relative_intersection_y = max(-0.8, min(0.8, normalized_relative_intersection_y))
        
        # Calculate bounce angle (between -30 and 30 degrees for more controlled gameplay)
        bounce_angle = normalized_relative_intersection_y * (math.pi/6)  # 30 degrees max angle
        
        # Calculate new direction with controlled speed increase
        current_speed = math.sqrt(ball['dx']**2 + ball['dy']**2)
        new_speed = min(current_speed * 1.02, 12)  # Max speed cap to prevent runaway
        
        ball['dx'] = -new_speed * math.cos(bounce_angle)
        ball['dy'] = -new_speed * math.sin(bounce_angle)
        
        # Ensure ball moves left after hitting right paddle
        ball['dx'] = -abs(ball['dx'])
        
        # Ensure minimum horizontal speed to prevent vertical-only movement
        if abs(ball['dx']) < 2:
            ball['dx'] = 2 if ball['dx'] > 0 else -2
    
    # Score points (ball went past boundaries)
    if ball['x'] < -ball_radius*2:  # Ball went past left boundary
        score['right'] += 1
        return 'right'
    elif ball['x'] > canvas_width + ball_radius*2:  # Ball went past right boundary
        score['left'] += 1
        return 'left'
    
    return None

def _reset_ball(ball):
    """Reset ball to center with controlled random direction"""
    ball['x'] = 400  # Center of 800 width
    ball['y'] = 300  # Center of 600 height
    # Ensure non-zero dy for visible motion; controlled speed
    ball['dx'] = random.choice([-4, 4])  # Reduced speed for better control
    ball['dy'] = random.choice([-2, -1, 1, 2])  # Reduced vertical speed
    
    # Ensure minimum speeds to prevent stuck balls
    if abs(ball['dx']) < 2:
        ball['dx'] = 2 if ball['dx'] > 0 else -2
    if abs(ball['dy']) < 1:
        ball['dy'] = 1 if ball['dy'] > 0 else -1

@socketio.on('pong_paddle_move')
def on_pong_paddle_move(data):
    room_id = data.get('room_id')
    if room_id not in active_rooms:
        return
    
    room = active_rooms[room_id]
    if not room['game_running'] and room['mode'] != 'bot':
        return
    
    username = session.get('username')
    if not username:
        return
    
    # Determine which paddle this user controls
    paddle_side = None
    if room['players'].get('left') == username:
        paddle_side = 'left'
    elif room['players'].get('right') == username:
        paddle_side = 'right'
    
    if not paddle_side:
        return
    
    paddle = room['game_state']['paddles'][paddle_side]
    paddle_height = 80  # Updated to match new paddle height
    canvas_height = 600  # Updated to match new canvas height

    # Support absolute mouse movement (y) and keyboard (direction)
    if 'y' in data:
        # y is canvas-relative already from the client
        try:
            target_y = float(data.get('y')) - (paddle_height / 2.0)
        except (TypeError, ValueError):
            target_y = paddle['y']
        # Clamp within bounds
        paddle['y'] = max(0, min(canvas_height - paddle_height, target_y))
    else:
        # Fallback to direction-based movement
        direction = data.get('direction')
        if not direction:
            return
        paddle_speed = 25  # Slightly increased for taller canvas
        if direction == 'up':
            paddle['y'] = max(0, paddle['y'] - paddle_speed)
        elif direction == 'down':
            paddle['y'] = min(canvas_height - paddle_height, paddle['y'] + paddle_speed)
    
    # Update the game state
    room['game_state']['paddles'][paddle_side] = paddle
    
    # Emit the updated paddle position to all clients
    emit('pong_paddle_update', {
        'paddle': paddle_side,
        'y': paddle['y']
    }, room=room_id, include_self=True)

@socketio.on('pong_start_game')
def on_pong_start_game(data):
    room_id = data.get('room_id')
    username = session.get('username')
    
    if room_id not in active_rooms or not username:
        return
        
    state = active_rooms[room_id]
    
    # Permissions: Room creator can always start. In bot mode, allow the human player to start as well.
    if username != state['room_creator']:
        if state.get('mode') == 'bot' and state['players'].get('right') == username:
            pass
        else:
            emit('error', {'message': 'Only room creator can start game'})
            return
    
    # Check if we can start the game
    if state['mode'] == 'bot':
        # Bot mode: allow start if right paddle is assigned to any human
        if not state['players'].get('right'):
            emit('error', {'message': 'Assign right paddle before starting bot game'})
            return
    else:
        # PvP mode: need 2 human players
        if len(state['members']) < 2:
            emit('error', {'message': f'Need 2 players to start (currently {len(state["members"])})'})
            return
    
    # Also check that both paddle positions are assigned
    if not state['players']['left'] or not state['players']['right']:
        emit('error', {'message': 'Both paddle positions must be filled'})
        return
    
    if state['game_running']:
        emit('error', {'message': 'Game already running'})
        return
    
    # Start game
    state['game_running'] = True
    state['winner'] = None
    
    # Reset game state
    state['game_state'] = {
        'ball': {'x': 400, 'y': 300, 'dx': 4, 'dy': 2},  # Use consistent starting values
        'paddles': {'left': {'y': 250}, 'right': {'y': 250}},
        'score': {'left': 0, 'right': 0}
    }
    
    # Start game loop in a separate thread
    import threading
    game_thread = threading.Thread(target=game_loop, args=(room_id,))
    game_thread.daemon = True
    game_thread.start()
    
    emit('pong_game_started', {
        'game_state': state['game_state']
    }, room=room_id)

# Game loop for each room
def game_loop(room_id):
    """Main game loop for Pong with consistent timing and frame rate"""
    if room_id not in active_rooms:
        return
    
    room = active_rooms[room_id]
    
    try:
        last_time = time.time()
        fixed_dt = 1.0 / 60.0  # Target 60 FPS for smoother gameplay
        accumulator = 0.0
        
        while room_id in active_rooms and room['game_running']:
            current_time = time.time()
            frame_delta = min(current_time - last_time, 0.25)  # Prevent spiral of death
            last_time = current_time
            
            accumulator += frame_delta
            
            # Fixed timestep updates for consistent gameplay
            while accumulator >= fixed_dt and room_id in active_rooms and room['game_running']:
                # Update ball position and check for scoring
                scoring_side = _update_ball_position(room['game_state'])
                if scoring_side:
                    # On score, pause for 1 second and broadcast updated state
                    socketio.emit('pong_score', {
                        'game_state': room['game_state'],
                        'scoring_side': scoring_side
                    }, room=room_id)
                    time.sleep(1.0)  # Pause for 1 second
                    # Reset ball after pause
                    _reset_ball(room['game_state']['ball'])
                    if scoring_side == 'right':
                        room['game_state']['ball']['dx'] = abs(room['game_state']['ball']['dx'])
                    else:
                        room['game_state']['ball']['dx'] = -abs(room['game_state']['ball']['dx'])
                
                # Update computer paddle in bot mode with improved AI
                if room['mode'] == 'bot' and 'left' in room['players'] and room['players']['left'] == 'Computer':
                    _update_computer_paddle(room['game_state'])
                
                # Check for winner using room's win_points
                winner_side = _check_winner(room['game_state']['score'], room.get('win_points', 5))
                if winner_side:
                    room['game_running'] = False
                    room['winner'] = winner_side
                    socketio.emit('pong_game_over', {
                        'winner': winner_side,
                        'game_state': room['game_state'],
                        'score': room['game_state']['score'],
                        'win_points': room.get('win_points', 5)
                    }, room=room_id)
                    room['rematch_votes'] = set()
                    room['rematch_requested'] = False
                    room['rematch_pending'] = set()
                    break
                
                accumulator -= fixed_dt
            
            # Only send updates if game is still running
            if room_id in active_rooms and room['game_running']:
                # Emit game state to all clients less frequently (20 FPS) to reduce network traffic
                if time.time() - room.get('last_update_time', 0) > 0.05:  # 20 FPS for network updates
                    socketio.emit('pong_update', {
                        'game_state': room['game_state']
                    }, room=room_id)
                    room['last_update_time'] = time.time()
            
            # Small sleep to prevent 100% CPU usage
            time.sleep(0.001)
            
    except Exception as e:
        print(f"Error in game loop for room {room_id}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up if room still exists
        if room_id in active_rooms:
            active_rooms[room_id]['game_running'] = False

@socketio.on('pong_rematch_request')
def on_pong_rematch_request(data):
    room_id = data.get('room_id')
    username = session.get('username')
    if not room_id or room_id not in active_rooms or not username:
        return
    
    state = active_rooms[room_id]
    
    # Only room creator can request rematch
    if username != state['room_creator']:
        emit('error', {'message': 'Only room creator can request rematch'})
        return
    
    # Only allow when game is over
    if not state.get('winner'):
        emit('error', {'message': 'Game still in progress'})
        return
    
    # Bot mode: instant reset (no second player to vote)
    if state.get('mode') == 'bot':
        state['game_state'] = {
            'ball': {'x': 400, 'y': 300, 'dx': 4, 'dy': 2},  # Use consistent starting values
            'paddles': {'left': {'y': 250}, 'right': {'y': 250}},
            'score': {'left': 0, 'right': 0}
        }
        state['winner'] = None
        state['game_running'] = False
        state['rematch_votes'].clear()
        state['rematch_requested'] = False
        state['rematch_pending'].clear()
        emit('pong_reset', {
            'game_state': state['game_state']
        }, room=room_id)
        return

    # PvP: collect votes
    state['rematch_requested'] = True
    state['rematch_pending'] = set()
    paddle = 'left' if state['players'].get('left') == username else ('right' if state['players'].get('right') == username else None)
    if paddle:
        state['rematch_votes'].add(paddle)
    emit('rematch_requested', {
        'requested_by': username,
        'creator_vote': paddle
    }, room=room_id)

@socketio.on('pong_rematch_response')
def on_pong_rematch_response(data):
    room_id = data.get('room_id')
    response = data.get('response')  # 'accept' or 'decline'
    username = session.get('username')
    
    if not room_id or room_id not in active_rooms or not username:
        return
    
    state = active_rooms[room_id]
    
    if not state.get('rematch_requested'):
        emit('error', {'message': 'No rematch request'})
        return
    
    if username == state['room_creator']:
        emit('error', {'message': 'You are the room creator'})
        return
    
    if response == 'accept':
        # Add player's vote
        paddle = 'left' if state['players'].get('left') == username else ('right' if state['players'].get('right') == username else None)
        if paddle:
            state['rematch_votes'].add(paddle)
            state['rematch_pending'].add(username)
        
        # Check if both players voted
        if len(state['rematch_votes']) >= 2:
            # Reset game (use same helper as start)
            state['game_state'] = {
                'ball': {'x': 400, 'y': 300, 'dx': 4, 'dy': 2},  # Use consistent starting values
                'paddles': {'left': {'y': 250}, 'right': {'y': 250}},
                'score': {'left': 0, 'right': 0}
            }
            state['winner'] = None
            state['game_running'] = False
            state['rematch_votes'].clear()
            state['rematch_requested'] = False
            state['rematch_pending'].clear()
            
            emit('pong_reset', {
                'game_state': state['game_state']
            }, room=room_id)
        else:
            emit('rematch_status', {
                'votes': list(state['rematch_votes']),
                'pending': list(state['rematch_pending'])
            }, room=room_id)
    
    elif response == 'decline':
        # Reset rematch state
        state['rematch_requested'] = False
        state['rematch_votes'].clear()
        state['rematch_pending'].clear()
        
        emit('rematch_declined', {
            'declined_by': username
        }, room=room_id)

@socketio.on('dissolve_room')
def on_dissolve_room(data):
    room_id = data.get('room_id')
    username = session.get('username')
    
    if not room_id or not username:
        return
    
    state = active_rooms.get(room_id)
    if not state:
        return
    
    # Only room creator can dissolve room
    if username != state['room_creator']:
        emit('error', {'message': 'Only room creator can dissolve room'})
        return
    
    # Emit realtime room update to dashboard
    socketio.emit('room_dissolved', {'room_id': room_id})
    
    # delete from memory and database if exists
    active_rooms.pop(room_id, None)
    room = Room.query.filter_by(id=room_id).first()
    if room:
        db.session.delete(room)
        db.session.commit()
    
    emit('room_dissolved', {'room_id': room_id}, room=room_id)

@socketio.on("leave_room")
def on_leave(data):
    room_id = data.get('room_id') or data.get('room')
    username = session.get('username')
    if not room_id or not username:
        return
    
    leave_room(room_id)
    state = active_rooms.get(room_id)
    if state and username in state['members']:
        state['members'].remove(username)
        
        # Emit realtime room update to dashboard
        socketio.emit('room_updated', {
            'room_id': room_id,
            'players': len(state['members'])
        })
        
        emit("user_left", {
            "username": username, 
            "players": list(state['members'])
        }, room=room_id)
        
        # cleanup if empty
        if not state['members']:
            active_rooms.pop(room_id, None)
            room = Room.query.filter_by(id=room_id).first()
            if room:
                db.session.delete(room)
                db.session.commit()
            
            # Emit realtime room update to dashboard
            socketio.emit('room_dissolved', {'room_id': room_id})

if __name__ == "__main__":
    # For local development only
    # Vercel will use the app object directly
    socketio.run(app, debug=True, port=5000, use_reloader=False, allow_unsafe_werkzeug=True)

# For Vercel production deployment
app.debug = False
