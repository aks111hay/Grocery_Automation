from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_socketio import SocketIO, emit
import asyncio
import threading
import json
import time
from agent import graph, _safe_preview
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
import uuid
import base64
import io
import subprocess
import os
import signal
import psutil
from llm_parser import extract_products
from blinkit_tool_original import run_blinkit
from tool_original import run_zepto
from blinkit_tool_original import set_blinkit_otp
from tool_original import set_zepto_otp

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Store active sessions and browser instances
active_sessions = {}
browser_processes = {}
session_to_sid = {}  # Map session_id to socket.io sid

class ChatSession:
    def __init__(self, session_id):
        self.session_id = session_id
        self.config = {"configurable": {"thread_id": session_id}}
        self.messages = []
        self.browser_port = None
        self.browser_process = None
        self.socket_sid = None  # Store the socket.io session ID
        
    def add_message(self, role, content):
        self.messages.append({"role": role, "content": content, "timestamp": time.time()})

def start_browser_with_remote_debugging(session_id):
    """Start Chrome with remote debugging enabled"""
    try:
        # Find available port
        import socket
        sock = socket.socket()
        sock.bind(('', 0))
        port = sock.getsockname()[1]
        sock.close()
        
        # Chrome executable paths for different OS
        chrome_paths = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",  # macOS
            "/usr/bin/google-chrome",  # Linux
            "/usr/bin/chromium-browser",  # Linux Chromium
            "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",  # Windows
            "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"  # Windows x86
        ]
        
        chrome_path = None
        for path in chrome_paths:
            if os.path.exists(path):
                chrome_path = path
                break
        
        # Try using Playwright's chromium first (more reliable)
        try:
            from playwright.sync_api import sync_playwright
            
            # Create persistent playwright instance
            playwright = sync_playwright().start()
            browser = playwright.chromium.launch(
                headless=False,
                args=[
                    f'--remote-debugging-port={port}',
                    '--no-first-run',
                    '--no-default-browser-check',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ]
            )
            
            # Keep reference to both playwright and browser
            browser_processes[session_id] = {
                'playwright': playwright,
                'browser': browser,
                'port': port,
                'type': 'playwright'
            }
            
            # Wait for browser to be ready
            time.sleep(3)
            
            # Test if the debugging port is accessible
            import requests
            try:
                response = requests.get(f'http://localhost:{port}/json', timeout=5)
                if response.status_code == 200:
                    print(f"Playwright browser started successfully on port {port}")
                    return port
                else:
                    raise Exception("Browser not responding")
            except Exception as e:
                print(f"Browser port test failed: {e}")
                # Clean up and try Chrome
                browser.close()
                playwright.stop()
                del browser_processes[session_id]
                
        except Exception as e:
            print(f"Failed to start Playwright browser: {e}")
        
        # Fallback to Chrome if available
        if chrome_path:
            # Start Chrome with remote debugging
            cmd = [
                chrome_path,
                f'--remote-debugging-port={port}',
                '--no-first-run',
                '--no-default-browser-check',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
                '--disable-web-security',
                f'--user-data-dir=/tmp/chrome-session-{session_id}',
                'about:blank'
            ]
            
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            browser_processes[session_id] = {
                'process': process,
                'port': port,
                'type': 'chrome'
            }
            
            # Wait for Chrome to start and test connection
            time.sleep(3)
            
            import requests
            try:
                response = requests.get(f'http://localhost:{port}/json', timeout=5)
                if response.status_code == 200:
                    print(f"Chrome browser started successfully on port {port}")
                    return port
                else:
                    raise Exception("Chrome not responding")
            except Exception as e:
                print(f"Chrome port test failed: {e}")
                # Clean up
                process.terminate()
                del browser_processes[session_id]
                return None
        
        print("No suitable browser found")
        return None
        
    except Exception as e:
        print(f"Error starting browser: {e}")
        return None

def stop_browser(session_id):
    """Stop the browser for a session"""
    if session_id in browser_processes:
        browser_info = browser_processes[session_id]
        try:
            if browser_info['type'] == 'chrome' and 'process' in browser_info:
                process = browser_info['process']
                # Try graceful shutdown first
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
            elif browser_info['type'] == 'playwright' and 'browser' in browser_info:
                browser_info['browser'].close()
                browser_info['playwright'].stop()
        except Exception as e:
            print(f"Error stopping browser: {e}")
        finally:
            del browser_processes[session_id]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/browser/<session_id>')
def browser_proxy(session_id):
    """Serve the browser interface for a specific session"""
    # Find session by session_id instead of socket.io sid
    for sid, session in active_sessions.items():
        if session.session_id == session_id:
            if session.browser_port:
                return render_template('browser_frame.html', 
                                     port=session.browser_port,
                                     session_id=session_id)
    return "Browser not available", 404

@socketio.on('connect')
def handle_connect():
    session_id = str(uuid.uuid4())
    session = ChatSession(session_id)
    session.socket_sid = request.sid  # Store the socket.io session ID
    
    # Start browser with remote debugging
    browser_port = start_browser_with_remote_debugging(session_id)
    if browser_port:
        session.browser_port = browser_port
        
    active_sessions[request.sid] = session
    session_to_sid[session_id] = request.sid  # Map session_id to socket.io sid
    
    emit('session_created', {
        'session_id': session_id,
        'browser_port': browser_port,
        'browser_url': f'/browser/{session_id}' if browser_port else None
    })
    print(f"Client connected: {request.sid}, Browser port: {browser_port}")

@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in active_sessions:
        session = active_sessions[request.sid]
        stop_browser(session.session_id)
        # Clean up mappings
        if session.session_id in session_to_sid:
            del session_to_sid[session.session_id]
        del active_sessions[request.sid]
    print(f"Client disconnected: {request.sid}")

@socketio.on('send_message')
def handle_message(data):
    if request.sid not in active_sessions:
        emit('error', {'message': 'Session not found'})
        return
    
    session = active_sessions[request.sid]
    user_message = data['message']
    
    # Add user message to session
    session.add_message('user', user_message)
    
    # Emit user message to frontend
    emit('message_received', {
        'role': 'user',
        'content': user_message,
        'timestamp': time.time()
    })
    
    # Process message with agent in a separate thread
    # Pass the socket.io session ID to the thread
    threading.Thread(target=process_agent_message, args=(session, user_message, request.sid)).start()

def process_agent_message(session, user_message, socket_sid):
    try:
        # Set browser context for tools if available
        if session.browser_port:
            os.environ['BROWSER_DEBUG_PORT'] = str(session.browser_port)
            os.environ['SESSION_ID'] = session.session_id
        
        # Stream agent response
        events = graph.stream(
            {"messages": [{"role": "user", "content": user_message}]},
            session.config,
            stream_mode="values",
        )
        
        for event in events:
            if "messages" in event and event["messages"]:
                last_message = event["messages"][-1]
                
                if hasattr(last_message, 'type'):
                    role = last_message.type
                elif hasattr(last_message, 'role'):
                    role = last_message.role
                else:
                    role = 'assistant'
                
                content = last_message.content if hasattr(last_message, 'content') else str(last_message)
                
                # Check for OTP requests in tool output
                if role == 'tool' and isinstance(content, str):
                    # Check for Blinkit OTP requests
                    if "waiting for blinkit otp" in content.lower() or "enter the otp" in content.lower() and "blinkit" in content.lower():
                        otp_prompt = " I need the OTP code for Blinkit. Please enter it when you receive it on your phone using the format: 'Blinkit OTP: 123456'"
                        
                        session.add_message('assistant', otp_prompt)
                        socketio.emit('message_received', {
                            'role': 'assistant',
                            'content': otp_prompt,
                            'timestamp': time.time(),
                            'isOtpRequest': True  # Special flag for frontend highlighting
                        }, room=socket_sid)
                    
                    # Check for Zepto OTP requests
                    elif "waiting for zepto otp" in content.lower() or "enter the otp" in content.lower() and "zepto" in content.lower():
                        otp_prompt = " I need the OTP code for Zepto. Please enter it when you receive it on your phone using the format: 'Zepto OTP: 123456'"
                        
                        session.add_message('assistant', otp_prompt)
                        socketio.emit('message_received', {
                            'role': 'assistant',
                            'content': otp_prompt,
                            'timestamp': time.time(),
                            'isOtpRequest': True  # Special flag for frontend highlighting
                        }, room=socket_sid)
                
                # Add to session
                session.add_message(role, content)
                
                # Emit to frontend using the passed socket_sid
                socketio.emit('message_received', {
                    'role': role,
                    'content': _safe_preview(content) if isinstance(content, str) else str(content),
                    'timestamp': time.time()
                }, room=socket_sid)
                
                # If this is a tool message, notify browser activity
                if role == 'tool':
                    socketio.emit('browser_activity', {
                        'message': 'Tool execution completed',
                        'timestamp': time.time()
                    }, room=socket_sid)
    
    except Exception as e:
        error_msg = f"Error processing message: {str(e)}"
        session.add_message('error', error_msg)
        socketio.emit('message_received', {
            'role': 'error',
            'content': error_msg,
            'timestamp': time.time()
        }, room=socket_sid)

@socketio.on('get_chat_history')
def handle_get_history():
    if request.sid in active_sessions:
        session = active_sessions[request.sid]
        emit('chat_history', {'messages': session.messages})

# Cleanup on shutdown
def cleanup_browsers():
    """Clean up all browser processes on shutdown"""
    for session_id in list(browser_processes.keys()):
        stop_browser(session_id)

import atexit
atexit.register(cleanup_browsers)

# Global results dictionary
results = {
    "blinkit": None,
    "zepto": None
}

@app.route("/get_mobile", methods=["GET", "POST"])
def get_mobile():
    if request.method == "POST":
        phone_number = request.form["mobile"]
        ADDRESS_TO_SEARCH = request.form["address"]
        session["phone_number"] = phone_number
        session["address"] = ADDRESS_TO_SEARCH
        # Get values from session before passing to threads
        search_items = session["search_items"]
        
        # Start Blinkit and Zepto in parallel
        def run_blinkit_thread():
            results["blinkit"] = run_blinkit(
                 phone_number,search_items,ADDRESS_TO_SEARCH
            )
        def run_zepto_thread():
            results["zepto"] = run_zepto(
                 phone_number,search_items
            )
        threading.Thread(target=run_blinkit_thread).start()
        threading.Thread(target=run_zepto_thread).start()

        return redirect(url_for("enter_otp"))
    return render_template("mobile.html")

@app.route("/enter_otp", methods=["GET", "POST"])
def enter_otp():
    if request.method == "POST":
        blinkit_otp = request.form.get("blinkit_otp")
        zepto_otp = request.form.get("zepto_otp")
        if blinkit_otp:
            set_blinkit_otp(blinkit_otp)
        if zepto_otp:
            set_zepto_otp(zepto_otp)
        return redirect(url_for("results_view"))
    return render_template("otp.html")

@app.route("/results")
def results_view():
    if not results["blinkit"] or not results["zepto"]:
        return redirect(url_for("loading"))
    return render_template("results.html",blinkit_data=results["blinkit"], zepto_data=results["zepto"])

@app.route("/loading")
def loading():
    if results["blinkit"] and results["zepto"]:
        return redirect(url_for("results_view"))
    return render_template("loading.html")

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        # Step 1: Extract product names from user input
        user_text = request.form["user_text"]
        search_items = extract_products(user_text)
        session["search_items"] = search_items
        return redirect(url_for("get_mobile"))
    return render_template("home.html")

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
