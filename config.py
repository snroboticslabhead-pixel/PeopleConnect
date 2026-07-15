import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'peopleconnect-premium-secure-key-2026-production')
    DATABASE_PATH = os.path.join(BASE_DIR, 'peopleconnect.db')
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    DEBUG = True
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    
    # Razorpay Integration Credentials
    RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', 'rzp_test_dhYJFlohg88eyl')
    RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', 'dummy_secret_for_validation')