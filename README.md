# Pong Online - Multiplayer Game

A real-time multiplayer Pong game built with Flask, Socket.IO, and SQLAlchemy. Play with friends online or challenge the computer in this modern web-based game.

## Features

- 🎮 **Real-time Multiplayer**: Play Pong with friends using WebSocket connections
- 🤖 **Bot Mode**: Creator-only solo play vs Computer (bot is left, player is right)
- 🔒 **Private Rooms**: Create password-protected rooms for friends
- 📱 **Responsive Design**: Works on desktop and mobile devices
- 🎯 **Customizable**: Set custom win points and game modes
- 🌐 **WebSocket Support**: True real-time gameplay with low latency

## Local Development

### Prerequisites

- Python 3.9+
- pip

### Installation

1. Clone the repository:
```bash
git clone https://github.com/TimothyDY/Pong.git
cd Pong
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
# Option 1: Use the startup script (recommended)
python start.py

# Option 2: Run directly
python run.py
```

5. Open your browser and navigate to `http://localhost:5000`

## Game Controls

- Mouse: Move paddle up and down

## Game Modes

- PvP: Two human players (public/private as configured)
- Bot: Solo vs Computer
  - Bot is always the left paddle
  - Human player is always the right paddle
  - Only the room creator can enter a bot room
  - Dissolve Room is hidden in bot mode (use Leave Room)

## Room Types

- Public: Anyone can join (with mode restrictions)
- Private: Password-protected rooms

## Room Access Rules

- Bot Rooms: Only the creator can join; others are blocked
- PvP Rooms: Up to 2 players can join
- Private Rooms: Require password authentication

## Gameplay Flow

- Start: Only the room creator (PvP) or the human player (Bot) can start
- Game Over:
  - PvP: Overlay shows Leave Room and Refresh (no rematch flow)
  - Bot: Overlay shows Restart (for the creator), Leave Room, and Refresh

## Technical Details

- Backend: Flask + Flask-SocketIO
- Database: SQLAlchemy with SQLite (local development)
- Frontend: HTML5 Canvas + JavaScript
- Real-time: WebSocket connections via Socket.IO with eventlet
- Async Mode: eventlet for optimal WebSocket performance

## Troubleshooting Multiplayer Issues

If you're experiencing multiplayer connection problems:

1. Check WebSocket Connection: Look for the connection status indicator
2. Browser Console: Open dev tools (F12) and check errors
3. Test Connection:
   ```bash
   python test_websocket.py
   ```
4. Multiple Browsers: Try incognito or different browsers
5. Firewall: Ensure port 5000 is open
6. Eventlet: Use `python start.py`

## Testing Multiplayer

1. Start the server: `python start.py`
2. Open two browser tabs/windows
3. Register/login with different accounts
4. Create a PvP room in one tab
5. Join the room from the other tab
6. Both players should see each other and be able to start the game

## Database

The application automatically creates and migrates the database schema. For production, consider using:

- PostgreSQL
- MySQL
- SQLite (development)

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Flask secret key | `"secret!"` |
| `DATABASE_URL` | Database connection string | `sqlite:///pong.db` |

## Production Deployment

Platforms that support WebSockets:

- Heroku
- DigitalOcean App Platform
- AWS Elastic Beanstalk
- Google Cloud Run
- Railway

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the ISC License.

## Support

For issues and questions:
- Create an issue on GitHub
- Check the documentation
- Review the code comments

---

**Enjoy playing Pong Online! 🏓**
