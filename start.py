#!/usr/bin/env python3
"""
Startup script for Pong multiplayer game
This script ensures proper eventlet initialization for WebSocket support
"""
import eventlet
eventlet.monkey_patch()

from run import app, socketio

if __name__ == "__main__":
    print("🚀 Starting Pong Multiplayer Server...")
    print("🌐 WebSocket server will be available at: http://localhost:5000")
    print("📱 Open multiple browser tabs to test multiplayer!")
    print("⚠️  Press Ctrl+C to stop the server")
    print("-" * 50)
    
    try:
        # Run the SocketIO server with eventlet
        socketio.run(
            app, 
            host='0.0.0.0', 
            port=5000, 
            debug=True, 
            use_reloader=False,
            allow_unsafe_werkzeug=True
        )
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")
        import traceback
        traceback.print_exc()
