#!/usr/bin/env python3
"""Setup database tables and create admin user"""
import sys
import os

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
load_dotenv()

from server import create_app, db
from server.database import User
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    # Create all tables
    print("Creating database tables...")
    db.create_all()
    print("[OK] Tables created successfully.")
    
    # Create admin user if it doesn't exist
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@example.com',
            password_hash=generate_password_hash('admin123'),
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()
        print("[OK] Admin user created:")
        print("  Username: admin")
        print("  Password: admin123")
    else:
        print("[OK] Admin user already exists")

