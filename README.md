# Pong Online - Multiplayer Game

A real-time multiplayer Pong game built with Flask, Socket.IO, and SQLAlchemy. Play with friends online or challenge the computer in this modern web-based game.

## Features

- 🎮 **Real-time Multiplayer**: Play Pong with friends using WebSocket connections
- 🤖 **Bot Mode**: Practice against an AI opponent (creator-only access)
- 🔒 **Private Rooms**: Create password-protected rooms for friends
- 📱 **Responsive Design**: Works on desktop and mobile devices
- 🎯 **Customizable**: Set custom win points and game modes
- 🏆 **Score Tracking**: Keep track of wins and losses
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
python run.py
```

5. Open your browser and navigate to `http://localhost:5000`

## Game Controls

- **Mouse**: Move paddle up and down
- **Touch**: Swipe on mobile devices

## Game Modes

- **PvP**: Two human players (anyone can join)
- **Bot**: Play against computer AI (only room creator can join)

## Room Types

- **Public**: Anyone can join (with mode restrictions)
- **Private**: Password-protected rooms

## Room Access Rules

- **Bot Rooms**: Only the creator can join (prevents others from interfering)
- **PvP Rooms**: Up to 2 players can join
- **Private Rooms**: Require password authentication

## Technical Details

- **Backend**: Flask + Flask-SocketIO
- **Database**: SQLAlchemy with SQLite (local development)
- **Frontend**: HTML5 Canvas + JavaScript
- **Real-time**: WebSocket connections via Socket.IO with eventlet
- **Async Mode**: eventlet for optimal WebSocket performance

## Database

The application automatically creates and migrates the database schema. For production, consider using:

- **PostgreSQL**: Better for concurrent users
- **MySQL**: Alternative relational database
- **SQLite**: Good for development and small deployments

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Flask secret key | `'secret!'` |
| `DATABASE_URL` | Database connection string | `sqlite:///pong.db` |

## Production Deployment

For production deployment, consider these platforms that support WebSockets:

- **Heroku**: Good for small to medium applications
- **DigitalOcean App Platform**: Scalable with good WebSocket support
- **AWS Elastic Beanstalk**: Enterprise-grade hosting
- **Google Cloud Run**: Serverless with WebSocket support
- **Railway**: Simple deployment with good WebSocket support

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
