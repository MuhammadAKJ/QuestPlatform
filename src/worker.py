"""
Cloudflare Workers entry point for the Flask app.
Uses the native WSGI adapter from the workers-py package.
"""
from workers import wsgi
from app import create_app

app = create_app()

# Bind the Flask WSGI app to the Cloudflare Worker entry point
Default = wsgi.entrypoint(app)
