"""Cloudflare Workers entry point for the Flask app."""
from workers import wsgi
from app import create_app

app = create_app()

Default = wsgi.entrypoint(app)