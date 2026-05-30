import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    ADMIN_USER = os.getenv("ADMIN_USER", "Kayrat_2085@mail.ru")
    ADMIN_PASS = os.getenv("ADMIN_PASS", "autoschool2026@")


