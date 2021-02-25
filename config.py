import os

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

SECRET_KEY = os.environ.get('SECRET_KEY')

SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'social.db')

SQLALCHEMY_TRACK_MODIFICATIONS = False

SQLALCHEMY_COMMIT_ON_TEARDOWN = True

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'media')

TEMPLATES_AUTO_RELOAD = True
