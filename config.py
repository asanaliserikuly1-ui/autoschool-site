import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    ADMIN_USER = os.getenv("ADMIN_USER", "Kayrat_2085@mail.ru")
    ADMIN_PASS = os.getenv("ADMIN_PASS", "autoschool2026@")

    os.environ["DATABASE_URL"] = "postgresql://postgres.ivykupcbocmlklkngvtn:Autoschool2026StrongPass@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"
    os.environ["CLOUDINARY_URL"] = "cloudinary://758634731699414:Y0BiXtXcDkyzk1md096FgAjYhlQ@dksgnnnwy"
