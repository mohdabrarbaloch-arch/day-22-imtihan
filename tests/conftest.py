"""Pytest bootstrap — tests run against a throwaway SQLite file."""

import os
import tempfile

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mktemp(suffix='.db')}"
os.environ["JWT_SECRET"] = "test-secret-not-for-production"
os.environ["RATE_LIMIT_REGISTER"] = "10000/minute"
os.environ["RATE_LIMIT_LOGIN"] = "10000/minute"
os.environ["RATE_LIMIT_SUBMIT"] = "10000/minute"
