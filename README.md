# Pong Online - Multiplayer Game

A real-time multiplayer Pong game built with Flask, Socket.IO, and SQLAlchemy. Play with friends online or challenge the computer in this modern web-based game.

## Features

- 🎮 **Real-time Multiplayer**: Play Pong with friends using WebSocket connections
- 🤖 **Bot Mode**: Practice against an AI opponent
- 🔒 **Private Rooms**: Create password-protected rooms for friends
- 📱 **Responsive Design**: Works on desktop and mobile devices
- 🎯 **Customizable**: Set custom win points and game modes
- 🏆 **Score Tracking**: Keep track of wins and losses

## Local Development

### Prerequisites

- Python 3.9+
- pip

### Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd SocketGame
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

## Vercel Deployment

### Prerequisites

- Vercel account
- Git repository

### Deployment Steps

1. **Push your code to GitHub/GitLab/Bitbucket**

2. **Connect to Vercel**:
   - Go to [vercel.com](https://vercel.com)
   - Click "New Project"
   - Import your Git repository

3. **Configure Environment Variables** (optional):
   - `SECRET_KEY`: Custom secret key for Flask
   - `DATABASE_URL`: Database connection string (if using external database)

4. **Deploy**:
   - Vercel will automatically detect the Python configuration
   - Click "Deploy"

### Vercel Configuration

The project includes:
- `vercel.json`: Vercel deployment configuration
- `wsgi.py`: WSGI entry point for Vercel
- `requirements.txt`: Python dependencies
- `runtime.txt`: Python version specification

## Game Controls

- **Mouse**: Move paddle up and down
- **Touch**: Swipe on mobile devices
- **Keyboard**: Arrow keys (if enabled)

## Game Modes

- **PvP**: Two human players
- **Bot**: Play against computer AI

## Room Types

- **Public**: Anyone can join
- **Private**: Password-protected rooms

## Technical Details

- **Backend**: Flask + Flask-SocketIO
- **Database**: SQLAlchemy with SQLite (local) / PostgreSQL (production)
- **Frontend**: HTML5 Canvas + JavaScript
- **Real-time**: WebSocket connections via Socket.IO
- **Deployment**: Vercel serverless functions

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
