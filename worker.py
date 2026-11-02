"""Cloudflare Workers entry point for the Flask app."""
from workers import wsgi
from app import create_app

app = create_app(cloudflare_runtime=True)

Default = wsgi.entrypoint(app)