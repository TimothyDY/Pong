#!/usr/bin/env python3
"""
Simple WebSocket test script for Pong multiplayer
"""
import socketio
import time
import threading

def test_websocket():
    # Create a Socket.IO client
    sio = socketio.Client()
    
    @sio.event
    def connect():
        print("✅ Connected to server!")
        
    @sio.event
    def disconnect():
        print("❌ Disconnected from server!")
        
    @sio.event
    def connect_error(data):
        print(f"⚠️ Connection error: {data}")
        
    @sio.event
    def pong_init(data):
        print(f"🎮 Received pong_init: {data}")
        
    @sio.event
    def players_update(data):
        print(f"👥 Players update: {data}")
        
    @sio.event
    def error(data):
        print(f"❌ Error: {data}")
        
    try:
        # Connect to the server
        print("🔌 Attempting to connect to http://localhost:5000...")
        sio.connect('http://localhost:5000')
        
        # Wait a bit for connection
        time.sleep(1)
        
        if sio.connected:
            print("🎯 Testing room join...")
            # Try to join a test room
            sio.emit('join_room', {'room_id': 'test-room-123'})
            
            # Keep connection alive for a few seconds
            time.sleep(5)
            
            print("🔌 Disconnecting...")
            sio.disconnect()
        else:
            print("❌ Failed to connect to server")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
    finally:
        if sio.connected:
            sio.disconnect()

if __name__ == "__main__":
    print("🧪 Starting WebSocket test...")
    test_websocket()
    print("✅ Test completed!")
