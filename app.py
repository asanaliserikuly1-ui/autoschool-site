import os
from uuid import uuid4
from functools import wraps
from dotenv import load_dotenv
load_dotenv()
from flask import Flask, render_template, request, redirect, url_for, flash, Response
from flask_sqlalchemy import SQLAlchemy
from config import Config
from sqlalchemy import text
from werkzeug.utils import secure_filename
from flask import send_from_directory

db = SQLAlchemy()


# ---------- Models ----------
class Branch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(40), unique=True, nullable=False)   # shugyla/tolebi/...
    name = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(40), nullable=False)
    whatsapp = db.Column(db.String(40), nullable=False)
    map_embed = db.Column(db.Text, nullable=False)                 # embed link


class Price(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    subtitle = db.Column(db.String(180), nullable=True)
    price_text = db.Column(db.String(80), nullable=False)
    is_highlight = db.Column(db.Boolean, default=False)


class Instructor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    branch_code = db.Column(db.String(40), nullable=False)

    experience = db.Column(db.String(80), nullable=True)
    car = db.Column(db.String(120), nullable=True)
    tags = db.Column(db.String(200), nullable=True)

    photo_url = db.Column(db.String(300), nullable=True)  # "uploads/instructors/abc.jpg"
    is_active = db.Column(db.Boolean, default=True)

    category = db.Column(db.String(10), nullable=False, default="B")  # A/A1/B
    rating = db.Column(db.Float, nullable=False, default=4.9)
    rating_count = db.Column(db.Integer, nullable=False, default=0)


class HomePriceCard(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    # уникальный код для шаблона: B_MT, B_AT, A, A1
    code = db.Column(db.String(20), unique=True, nullable=False)

    # категория группы: B / A (A1 тоже можно хранить как A)
    category = db.Column(db.String(10), nullable=False, default="B")

    # заголовок колонки: МКПП / АКПП / Категория A1 и т.д.
    col_title = db.Column(db.String(80), nullable=False, default="МКПП")

    # строки под ним
    line1 = db.Column(db.String(120), nullable=False, default="2 месяца")
    line2 = db.Column(db.String(120), nullable=False, default="16 уроков теории")
    line3 = db.Column(db.String(120), nullable=True)  # ✅ добавили 3-ю строку (например "5 уроков практики")

    # цена
    price_text = db.Column(db.String(80), nullable=False, default="100 000 тенге")

    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, default=True)


class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    branch_code = db.Column(db.String(40), nullable=False)

    experience = db.Column(db.String(80), nullable=True)
    subject = db.Column(db.String(120), nullable=True)
    tags = db.Column(db.String(200), nullable=True)

    photo_url = db.Column(db.String(300), nullable=True)  # "uploads/teachers/xxx.jpg"
    is_active = db.Column(db.Boolean, default=True)

    rating = db.Column(db.Float, nullable=False, default=4.9)
    rating_count = db.Column(db.Integer, nullable=False, default=0)

class GalleryImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    # путь относительно static, как у instructors/teachers
    photo_url = db.Column(db.String(300), nullable=False)  # "uploads/gallery/xxx.jpg"

    title = db.Column(db.String(140), nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    sort_order = db.Column(db.Integer, nullable=False, default=0)
# ---------- Auth (BasicAuth) ----------
def check_auth(username, password, app):
    return username == app.config.get("ADMIN_USER") and password == app.config.get("ADMIN_PASS")


def authenticate():
    return Response(
        "Нужна авторизация", 401,
        {"WWW-Authenticate": 'Basic realm="Admin Panel"'}
    )


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password, app):
            return authenticate()
        return f(*args, **kwargs)
    return decorated


# ---------- App factory ----------
def create_app():
    global app
    app = Flask(__name__)
    app.config.from_object(Config)

    # DB
    os.makedirs(app.instance_path, exist_ok=True)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(app.instance_path, "app.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Uploads
    app.config["UPLOAD_FOLDER_INSTRUCTORS"] = os.path.join(app.static_folder, "uploads", "instructors")
    app.config["UPLOAD_FOLDER_TEACHERS"] = os.path.join(app.static_folder, "uploads", "teachers")
    app.config["UPLOAD_FOLDER_GALLERY"] = os.path.join(app.static_folder, "uploads", "gallery")
    app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5MB
    ALLOWED_EXT = {"png", "jpg", "jpeg", "webp"}

    db.init_app(app)

    # ===== SEO FILES =====
    @app.get("/sitemap.xml")
    def sitemap():
        return send_from_directory(app.static_folder, "sitemap.xml")

    @app.get("/robots.txt")
    def robots():
        return send_from_directory(app.static_folder, "robots.txt")



    def allowed_file(filename: str) -> bool:
        return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


    # ---------- Photos ----------
    def save_instructor_photo(file_storage) -> str:
        if not file_storage or not getattr(file_storage, "filename", ""):
            return ""
        if file_storage.filename.strip() == "":
            return ""
        if not allowed_file(file_storage.filename):
            return ""

        os.makedirs(app.config["UPLOAD_FOLDER_INSTRUCTORS"], exist_ok=True)
        original = secure_filename(file_storage.filename)
        ext = original.rsplit(".", 1)[1].lower()
        fname = f"{uuid4().hex}.{ext}"
        abs_path = os.path.join(app.config["UPLOAD_FOLDER_INSTRUCTORS"], fname)
        file_storage.save(abs_path)
        return f"uploads/instructors/{fname}"

    def save_gallery_photo(file_storage) -> str:
        if not file_storage or not getattr(file_storage, "filename", ""):
            return ""
        if file_storage.filename.strip() == "":
            return ""
        if not allowed_file(file_storage.filename):
            return ""

        os.makedirs(app.config["UPLOAD_FOLDER_GALLERY"], exist_ok=True)
        original = secure_filename(file_storage.filename)
        ext = original.rsplit(".", 1)[1].lower()
        fname = f"{uuid4().hex}.{ext}"
        abs_path = os.path.join(app.config["UPLOAD_FOLDER_GALLERY"], fname)
        file_storage.save(abs_path)
        return f"uploads/gallery/{fname}"

    def save_teacher_photo(file_storage) -> str:
        if not file_storage or not getattr(file_storage, "filename", ""):
            return ""
        if file_storage.filename.strip() == "":
            return ""
        if not allowed_file(file_storage.filename):
            return ""

        os.makedirs(app.config["UPLOAD_FOLDER_TEACHERS"], exist_ok=True)
        original = secure_filename(file_storage.filename)
        ext = original.rsplit(".", 1)[1].lower()
        fname = f"{uuid4().hex}.{ext}"
        abs_path = os.path.join(app.config["UPLOAD_FOLDER_TEACHERS"], fname)
        file_storage.save(abs_path)
        return f"uploads/teachers/{fname}"

    def try_remove_file(photo_path: str):
        if not photo_path:
            return
        try:
            abs_path = os.path.join(app.static_folder, photo_path)
            if os.path.exists(abs_path):
                os.remove(abs_path)
        except:
            pass

    # ---------- DB ensures (для старой sqlite) ----------
    def _has_column(table, col) -> bool:
        rows = db.session.execute(text(f"PRAGMA table_info({table})")).fetchall()
        return any(r[1] == col for r in rows)

    def _table_exists(table) -> bool:
        rows = db.session.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name=:t"),
            {"t": table}
        ).fetchall()
        return len(rows) > 0

    def ensure_instructor_columns():
        table = "instructor"
        if not _table_exists(table):
            return

        if not _has_column(table, "category"):
            db.session.execute(text("ALTER TABLE instructor ADD COLUMN category VARCHAR(10) NOT NULL DEFAULT 'B'"))
        if not _has_column(table, "rating"):
            db.session.execute(text("ALTER TABLE instructor ADD COLUMN rating FLOAT NOT NULL DEFAULT 4.9"))
        if not _has_column(table, "rating_count"):
            db.session.execute(text("ALTER TABLE instructor ADD COLUMN rating_count INTEGER NOT NULL DEFAULT 0"))
        if not _has_column(table, "photo_url"):
            db.session.execute(text("ALTER TABLE instructor ADD COLUMN photo_url VARCHAR(300)"))

        db.session.commit()

    def ensure_gallery_table_and_columns():
        table = "gallery_image"
        if not _table_exists(table):
            return

        if not _has_column(table, "photo_url"):
            db.session.execute(text("ALTER TABLE gallery_image ADD COLUMN photo_url VARCHAR(300)"))
        if not _has_column(table, "title"):
            db.session.execute(text("ALTER TABLE gallery_image ADD COLUMN title VARCHAR(140)"))
        if not _has_column(table, "is_active"):
            db.session.execute(text("ALTER TABLE gallery_image ADD COLUMN is_active BOOLEAN DEFAULT 1"))
        if not _has_column(table, "sort_order"):
            db.session.execute(text("ALTER TABLE gallery_image ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0"))

        db.session.commit()

    def ensure_teacher_columns():
        table = "teacher"
        if not _table_exists(table):
            return

        if not _has_column(table, "subject"):
            db.session.execute(text("ALTER TABLE teacher ADD COLUMN subject VARCHAR(120)"))
        if not _has_column(table, "tags"):
            db.session.execute(text("ALTER TABLE teacher ADD COLUMN tags VARCHAR(200)"))
        if not _has_column(table, "photo_url"):
            db.session.execute(text("ALTER TABLE teacher ADD COLUMN photo_url VARCHAR(300)"))
        if not _has_column(table, "is_active"):
            db.session.execute(text("ALTER TABLE teacher ADD COLUMN is_active BOOLEAN DEFAULT 1"))
        if not _has_column(table, "rating"):
            db.session.execute(text("ALTER TABLE teacher ADD COLUMN rating FLOAT NOT NULL DEFAULT 4.9"))
        if not _has_column(table, "rating_count"):
            db.session.execute(text("ALTER TABLE teacher ADD COLUMN rating_count INTEGER NOT NULL DEFAULT 0"))

        db.session.commit()

    def ensure_home_price_card_columns():
        """
        Если HomePriceCard был создан раньше без line3 — добавим.
        """
        table = "home_price_card"
        if not _table_exists(table):
            return
        if not _has_column(table, "line3"):
            db.session.execute(text("ALTER TABLE home_price_card ADD COLUMN line3 VARCHAR(120)"))
        db.session.commit()

    with app.app_context():
        db.create_all()
        ensure_instructor_columns()
        ensure_teacher_columns()
        ensure_home_price_card_columns()
        ensure_gallery_table_and_columns()
        seed_if_empty()

    # =========================
    # Admin: Home prices cards
    # =========================
    @app.get("/admin/home-prices")
    @requires_auth
    def admin_home_prices():
        items = HomePriceCard.query.order_by(HomePriceCard.sort_order.asc(), HomePriceCard.id.asc()).all()
        return render_template("admin/home_prices.html", items=items)

    @app.post("/admin/home-prices/create")
    @requires_auth
    def admin_home_prices_create():
        d = request.form
        code = (d.get("code") or "").strip().upper()
        category = (d.get("category") or "B").strip().upper()
        col_title = (d.get("col_title") or "МКПП").strip()
        line1 = (d.get("line1") or "").strip()
        line2 = (d.get("line2") or "").strip()
        line3 = (d.get("line3") or "").strip() or None
        price_text = (d.get("price_text") or "").strip()
        sort_order = int(d.get("sort_order") or 0)
        is_active = True if d.get("is_active") == "on" else False

        if not code or not col_title or not line1 or not line2 or not price_text:
            flash("Обязательные поля: CODE, Заголовок, line1, line2, цена.", "error")
            return redirect(url_for("admin_home_prices"))

        if HomePriceCard.query.filter_by(code=code).first():
            flash("Такой CODE уже есть.", "error")
            return redirect(url_for("admin_home_prices"))

        item = HomePriceCard(
            code=code,
            category=category,
            col_title=col_title,
            line1=line1,
            line2=line2,
            line3=line3,
            price_text=price_text,
            sort_order=sort_order,
            is_active=is_active
        )
        db.session.add(item)
        db.session.commit()
        flash("Добавлено ✅", "success")
        return redirect(url_for("admin_home_prices"))

    @app.post("/admin/home-prices/<int:item_id>/update")
    @requires_auth
    def admin_home_prices_update(item_id):
        item = HomePriceCard.query.get_or_404(item_id)
        d = request.form

        item.category = (d.get("category") or item.category or "B").strip().upper()
        item.col_title = (d.get("col_title") or item.col_title or "МКПП").strip()
        item.line1 = (d.get("line1") or item.line1 or "").strip()
        item.line2 = (d.get("line2") or item.line2 or "").strip()
        item.line3 = (d.get("line3") or "").strip() or None
        item.price_text = (d.get("price_text") or item.price_text or "").strip()
        try:
            item.sort_order = int(d.get("sort_order") or item.sort_order or 0)
        except:
            pass
        item.is_active = True if d.get("is_active") == "on" else False

        db.session.commit()
        flash("Сохранено ✅", "success")
        return redirect(url_for("admin_home_prices"))

    @app.post("/admin/home-prices/<int:item_id>/delete")
    @requires_auth
    def admin_home_prices_delete(item_id):
        item = HomePriceCard.query.get_or_404(item_id)
        db.session.delete(item)
        db.session.commit()
        flash("Удалено 🗑️", "success")
        return redirect(url_for("admin_home_prices"))

    # ===== API =====
    @app.get("/api/branches")
    def api_branches():
        branches = Branch.query.order_by(Branch.id.asc()).all()
        return {"branches": [
            {
                "id": b.id,
                "code": b.code,
                "name": b.name,
                "address": b.address,
                "phone": b.phone,
                "whatsapp": b.whatsapp,
                "map_embed": b.map_embed
            } for b in branches
        ]}

    # ===== Admin: Instructors CRUD =====
    @app.get("/admin/instructors")
    @requires_auth
    def admin_instructors():
        instructors = Instructor.query.order_by(Instructor.id.desc()).all()
        branches = Branch.query.order_by(Branch.name.asc()).all()
        return render_template("admin/instructors.html", instructors=instructors, branches=branches)

    @app.post("/admin/instructors/create")
    @requires_auth
    def admin_instructors_create():
        d = request.form

        def to_float(x, default=4.9):
            try:
                return float(str(x).replace(",", "."))
            except:
                return default

        def to_int(x, default=0):
            try:
                return int(x)
            except:
                return default

        rating = max(0.0, min(5.0, to_float(d.get("rating"), 4.9)))

        cat = (d.get("category") or "B").strip().upper()
        if cat not in ("A", "A1", "B"):
            cat = "B"

        photo_path = save_instructor_photo(request.files.get("photo"))

        ins = Instructor(
            name=(d.get("name") or "").strip(),
            branch_code=(d.get("branch_code") or "").strip(),
            experience=(d.get("experience") or "").strip(),
            car=(d.get("car") or "").strip(),
            tags=(d.get("tags") or "").strip(),
            photo_url=photo_path,
            is_active=True if d.get("is_active") == "on" else False,

            category=cat,
            rating=rating,
            rating_count=max(0, to_int(d.get("rating_count"), 0))
        )

        if not ins.name or not ins.branch_code:
            flash("Имя и филиал обязательны.", "error")
            return redirect(url_for("admin_instructors"))

        db.session.add(ins)
        db.session.commit()
        flash("Инструктор добавлен ✅", "success")
        return redirect(url_for("admin_instructors"))

    @app.post("/admin/instructors/<int:ins_id>/update")
    @requires_auth
    def admin_instructors_update(ins_id):
        ins = Instructor.query.get_or_404(ins_id)
        d = request.form

        def to_float(x, default=ins.rating if ins.rating is not None else 4.9):
            try:
                return float(str(x).replace(",", "."))
            except:
                return default

        def to_int(x, default=ins.rating_count if ins.rating_count is not None else 0):
            try:
                return int(x)
            except:
                return default

        ins.name = (d.get("name") or "").strip()
        ins.branch_code = (d.get("branch_code") or "").strip()
        ins.experience = (d.get("experience") or "").strip()
        ins.car = (d.get("car") or "").strip()
        ins.tags = (d.get("tags") or "").strip()
        ins.is_active = True if d.get("is_active") == "on" else False

        cat = (d.get("category") or (ins.category or "B")).strip().upper()
        if cat not in ("A", "A1", "B"):
            cat = "B"
        ins.category = cat

        ins.rating = max(0.0, min(5.0, to_float(d.get("rating"))))
        ins.rating_count = max(0, to_int(d.get("rating_count")))

        new_photo = save_instructor_photo(request.files.get("photo"))
        if new_photo:
            try_remove_file(ins.photo_url or "")
            ins.photo_url = new_photo

        db.session.commit()
        flash("Инструктор обновлён ✅", "success")
        return redirect(url_for("admin_instructors"))

    @app.post("/admin/instructors/<int:ins_id>/delete")
    @requires_auth
    def admin_instructors_delete(ins_id):
        ins = Instructor.query.get_or_404(ins_id)
        try_remove_file(ins.photo_url or "")
        db.session.delete(ins)
        db.session.commit()
        flash("Инструктор удалён 🗑️", "success")
        return redirect(url_for("admin_instructors"))

    # =========================
    # Admin: Gallery
    # =========================
    @app.get("/admin/gallery")
    @requires_auth
    def admin_gallery():
        items = GalleryImage.query.order_by(GalleryImage.sort_order.asc(), GalleryImage.id.desc()).all()
        return render_template("admin/gallery.html", items=items)

    @app.post("/admin/gallery/upload")
    @requires_auth
    def admin_gallery_upload():
        title = (request.form.get("title") or "").strip()
        sort_order = 0
        try:
            sort_order = int(request.form.get("sort_order") or 0)
        except:
            sort_order = 0
        is_active = True if request.form.get("is_active") == "on" else False

        photo_path = save_gallery_photo(request.files.get("photo"))
        if not photo_path:
            flash("Загрузите изображение (jpg/png/webp).", "error")
            return redirect(url_for("admin_gallery"))

        item = GalleryImage(
            photo_url=photo_path,
            title=title,
            is_active=is_active,
            sort_order=sort_order
        )
        db.session.add(item)
        db.session.commit()
        flash("Фото добавлено в галерею ✅", "success")
        return redirect(url_for("admin_gallery"))

    @app.post("/admin/gallery/<int:item_id>/update")
    @requires_auth
    def admin_gallery_update(item_id):
        item = GalleryImage.query.get_or_404(item_id)
        item.title = (request.form.get("title") or "").strip() or None

        try:
            item.sort_order = int(request.form.get("sort_order") or item.sort_order or 0)
        except:
            pass

        item.is_active = True if request.form.get("is_active") == "on" else False

        new_photo = save_gallery_photo(request.files.get("photo"))
        if new_photo:
            try_remove_file(item.photo_url or "")
            item.photo_url = new_photo

        db.session.commit()
        flash("Сохранено ✅", "success")
        return redirect(url_for("admin_gallery"))

    @app.post("/admin/gallery/<int:item_id>/delete")
    @requires_auth
    def admin_gallery_delete(item_id):
        item = GalleryImage.query.get_or_404(item_id)
        try_remove_file(item.photo_url or "")
        db.session.delete(item)
        db.session.commit()
        flash("Удалено 🗑️", "success")
        return redirect(url_for("admin_gallery"))

    # ===== Admin: Teachers CRUD =====
    @app.get("/admin/teachers")
    @requires_auth
    def admin_teachers():
        teachers = Teacher.query.order_by(Teacher.id.desc()).all()
        branches = Branch.query.order_by(Branch.name.asc()).all()
        return render_template("admin/teachers.html", teachers=teachers, branches=branches)

    @app.post("/admin/teachers/create")
    @requires_auth
    def admin_teachers_create():
        d = request.form

        def to_float(x, default=4.9):
            try:
                return float(str(x).replace(",", "."))
            except:
                return default

        def to_int(x, default=0):
            try:
                return int(x)
            except:
                return default

        rating = max(0.0, min(5.0, to_float(d.get("rating"), 4.9)))
        photo_path = save_teacher_photo(request.files.get("photo"))

        t = Teacher(
            name=(d.get("name") or "").strip(),
            branch_code=(d.get("branch_code") or "").strip(),
            experience=(d.get("experience") or "").strip(),
            subject=(d.get("subject") or "").strip(),
            tags=(d.get("tags") or "").strip(),
            photo_url=photo_path,
            is_active=True if d.get("is_active") == "on" else False,
            rating=rating,
            rating_count=max(0, to_int(d.get("rating_count"), 0))
        )

        if not t.name or not t.branch_code:
            flash("Имя и филиал обязательны.", "error")
            return redirect(url_for("admin_teachers"))

        db.session.add(t)
        db.session.commit()
        flash("Преподаватель добавлен ✅", "success")
        return redirect(url_for("admin_teachers"))

    @app.post("/admin/teachers/<int:t_id>/update")
    @requires_auth
    def admin_teachers_update(t_id):
        t = Teacher.query.get_or_404(t_id)
        d = request.form

        def to_float(x, default=t.rating if t.rating is not None else 4.9):
            try:
                return float(str(x).replace(",", "."))
            except:
                return default

        def to_int(x, default=t.rating_count if t.rating_count is not None else 0):
            try:
                return int(x)
            except:
                return default

        t.name = (d.get("name") or "").strip()
        t.branch_code = (d.get("branch_code") or "").strip()
        t.experience = (d.get("experience") or "").strip()
        t.subject = (d.get("subject") or "").strip()
        t.tags = (d.get("tags") or "").strip()
        t.is_active = True if d.get("is_active") == "on" else False

        t.rating = max(0.0, min(5.0, to_float(d.get("rating"))))
        t.rating_count = max(0, to_int(d.get("rating_count")))

        new_photo = save_teacher_photo(request.files.get("photo"))
        if new_photo:
            try_remove_file(t.photo_url or "")
            t.photo_url = new_photo

        db.session.commit()
        flash("Преподаватель обновлён ✅", "success")
        return redirect(url_for("admin_teachers"))

    @app.post("/admin/teachers/<int:t_id>/delete")
    @requires_auth
    def admin_teachers_delete(t_id):
        t = Teacher.query.get_or_404(t_id)
        try_remove_file(t.photo_url or "")
        db.session.delete(t)
        db.session.commit()
        flash("Преподаватель удалён 🗑️", "success")
        return redirect(url_for("admin_teachers"))

    # ---- Public pages ----
    @app.get("/")
    def home():
        prices = Price.query.order_by(Price.id.desc()).all()
        branches = Branch.query.order_by(Branch.id.asc()).all()

        pB = None
        pA = None
        for p in prices:
            tt = (p.title or "").lower()
            if not pB and "b" in tt:
                pB = p
            if not pA and "a" in tt:
                pA = p

        cards = {x.code: x for x in HomePriceCard.query.filter_by(is_active=True).all()}

        return render_template(
            "pages/home.html",
            prices=prices,
            branches=branches,  # ✅ ВОТ ЭТОГО НЕ ХВАТАЛО
            pB=pB,
            pA=pA,
            B_MT=cards.get("B_MT"),
            B_AT=cards.get("B_AT"),
            A=cards.get("A"),
            A1=cards.get("A1"),
        )

    @app.get("/training")
    def training():
        prices = Price.query.order_by(Price.id.desc()).all()
        return render_template("pages/training.html", prices=prices)

    @app.get("/privacy-policy")
    def privacy_policy():
        return render_template("privacy_policy.html")

    @app.get("/instructors")
    def instructors():
        branch = request.args.get("branch", "all").strip()
        branches = Branch.query.order_by(Branch.id.asc()).all()

        q = Instructor.query.filter_by(is_active=True)
        if branch != "all":
            q = q.filter_by(branch_code=branch)
        instructors_list = q.order_by(Instructor.id.desc()).all()

        tq = Teacher.query.filter_by(is_active=True)
        if branch != "all":
            tq = tq.filter_by(branch_code=branch)
        teachers_list = tq.order_by(Teacher.id.desc()).all()

        branch_map = {b.code: b.name for b in branches}

        return render_template(
            "pages/instructors.html",
            instructors=instructors_list,
            teachers=teachers_list,
            branches=branches,
            branch=branch,
            branch_map=branch_map
        )

    @app.get("/about")
    def about():
        gallery = (GalleryImage.query
                   .filter_by(is_active=True)
                   .order_by(GalleryImage.sort_order.asc(), GalleryImage.id.desc())
                   .all())
        return render_template("pages/about_contacts.html", gallery=gallery)

    @app.get("/admin")
    @requires_auth
    def admin_dashboard():
        branches_count = Branch.query.count()
        prices_count = Price.query.count()
        instructors_count = Instructor.query.count()
        teachers_count = Teacher.query.count()
        home_prices_count = HomePriceCard.query.count()
        gallery_count = GalleryImage.query.count()

        return render_template(
            "admin/dashboard.html",
            branches_count=branches_count,
            prices_count=prices_count,
            instructors_count=instructors_count,
            teachers_count=teachers_count,
            home_prices_count=home_prices_count,
            gallery_count=gallery_count
        )

    @app.get("/kz")
    def home_kz():
        prices = Price.query.order_by(Price.id.desc()).all()
        branches = Branch.query.order_by(Branch.id.asc()).all()

        pB = None
        pA = None
        for p in prices:
            tt = (p.title or "").lower()
            if not pB and "b" in tt:
                pB = p
            if not pA and "a" in tt:
                pA = p

        cards = {x.code: x for x in HomePriceCard.query.filter_by(is_active=True).all()}

        return render_template(
            "kz/pages/home.html",
            prices=prices,
            branches=branches,
            pB=pB,
            pA=pA,
            B_MT=cards.get("B_MT"),
            B_AT=cards.get("B_AT"),
            A=cards.get("A"),
            A1=cards.get("A1"),
        )

    @app.get("/kz/training")
    def training_kz():
        prices = Price.query.order_by(Price.id.desc()).all()
        return render_template("kz/pages/training.html", prices=prices)

    @app.get("/kz/instructors")
    def instructors_kz():
        branch = request.args.get("branch", "all").strip()
        branches = Branch.query.order_by(Branch.id.asc()).all()

        q = Instructor.query.filter_by(is_active=True)
        if branch != "all":
            q = q.filter_by(branch_code=branch)
        instructors_list = q.order_by(Instructor.id.desc()).all()

        tq = Teacher.query.filter_by(is_active=True)
        if branch != "all":
            tq = tq.filter_by(branch_code=branch)
        teachers_list = tq.order_by(Teacher.id.desc()).all()

        branch_map = {b.code: b.name for b in branches}

        return render_template(
            "kz/pages/instructors.html",
            instructors=instructors_list,
            teachers=teachers_list,
            branches=branches,
            branch=branch,
            branch_map=branch_map
        )

    @app.get("/kz/about")
    def about_kz():
        gallery = (GalleryImage.query
                   .filter_by(is_active=True)
                   .order_by(GalleryImage.sort_order.asc(), GalleryImage.id.desc())
                   .all())
        return render_template("kz/pages/about_contacts.html", gallery=gallery)

    @app.get("/kz/privacy-policy")
    def privacy_policy_kz():
        return render_template("kz/privacy_policy.html")

    # Branches CRUD
    @app.get("/admin/branches")
    @requires_auth
    def admin_branches():
        branches = Branch.query.order_by(Branch.id.desc()).all()
        return render_template("admin/branches.html", branches=branches)

    @app.post("/admin/branches/create")
    @requires_auth
    def admin_branches_create():
        data = request.form
        b = Branch(
            code=(data.get("code") or "").strip(),
            name=(data.get("name") or "").strip(),
            address=(data.get("address") or "").strip(),
            phone=(data.get("phone") or "").strip(),
            whatsapp=(data.get("whatsapp") or "").strip(),
            map_embed=(data.get("map_embed") or "").strip(),
        )
        if not b.code or not b.name:
            flash("Код и название обязательны.", "error")
            return redirect(url_for("admin_branches"))
        db.session.add(b)
        db.session.commit()
        flash("Филиал добавлен ✅", "success")
        return redirect(url_for("admin_branches"))

    @app.post("/admin/branches/<int:branch_id>/update")
    @requires_auth
    def admin_branches_update(branch_id):
        b = Branch.query.get_or_404(branch_id)
        data = request.form
        b.code = (data.get("code") or "").strip()
        b.name = (data.get("name") or "").strip()
        b.address = (data.get("address") or "").strip()
        b.phone = (data.get("phone") or "").strip()
        b.whatsapp = (data.get("whatsapp") or "").strip()
        b.map_embed = (data.get("map_embed") or "").strip()
        db.session.commit()
        flash("Филиал обновлён ✅", "success")
        return redirect(url_for("admin_branches"))

    @app.post("/admin/branches/<int:branch_id>/delete")
    @requires_auth
    def admin_branches_delete(branch_id):
        b = Branch.query.get_or_404(branch_id)
        db.session.delete(b)
        db.session.commit()
        flash("Филиал удалён 🗑️", "success")
        return redirect(url_for("admin_branches"))

    # Prices CRUD
    @app.get("/admin/prices")
    @requires_auth
    def admin_prices():
        prices = Price.query.order_by(Price.id.desc()).all()
        return render_template("admin/prices.html", prices=prices)

    @app.post("/admin/prices/create")
    @requires_auth
    def admin_prices_create():
        data = request.form
        p = Price(
            title=(data.get("title") or "").strip(),
            subtitle=(data.get("subtitle") or "").strip(),
            price_text=(data.get("price_text") or "").strip(),
            is_highlight=True if data.get("is_highlight") == "on" else False
        )
        if not p.title or not p.price_text:
            flash("Название и цена обязательны.", "error")
            return redirect(url_for("admin_prices"))
        db.session.add(p)
        db.session.commit()
        flash("Цена добавлена ✅", "success")
        return redirect(url_for("admin_prices"))

    @app.post("/admin/prices/<int:price_id>/update")
    @requires_auth
    def admin_prices_update(price_id):
        p = Price.query.get_or_404(price_id)
        data = request.form
        p.title = (data.get("title") or "").strip()
        p.subtitle = (data.get("subtitle") or "").strip()
        p.price_text = (data.get("price_text") or "").strip()
        p.is_highlight = True if data.get("is_highlight") == "on" else False
        db.session.commit()
        flash("Цена обновлена ✅", "success")
        return redirect(url_for("admin_prices"))

    @app.post("/admin/prices/<int:price_id>/delete")
    @requires_auth
    def admin_prices_delete(price_id):
        p = Price.query.get_or_404(price_id)
        db.session.delete(p)
        db.session.commit()
        flash("Цена удалена 🗑️", "success")
        return redirect(url_for("admin_prices"))

    return app


def seed_if_empty():
    """Заполняем базу стартовыми данными, если она пустая."""
    # Branches
    if Branch.query.count() == 0:
        demo = [
            Branch(code="shugyla", name="Филиал Шұғыла", address="Шұғыла 340/4 к2, цокольный этаж",
                   phone="+7 775 515 6044", whatsapp="+7 775 515 6044",
                   map_embed="https://www.google.com/maps?q=Шұғыла+340/4+Алматы&output=embed"),
            Branch(code="tolebi", name="Филиал Төле би", address="Төле би 180б, 9 этаж, 1 кабинет",
                   phone="+7 778 959 4131", whatsapp="+7 778 959 4131",
                   map_embed="https://www.google.com/maps?q=Төле+би+180б+Алматы&output=embed"),
            Branch(code="abaya", name="Филиал Абая", address="8 мкр 19а, 2 этаж",
                   phone="+7 747 143 7791", whatsapp="+7 747 143 7791",
                   map_embed="https://www.google.com/maps?q=8+мкр+19а+Алматы&output=embed"),
            Branch(code="makataeva", name="Филиал Макатаева", address="Макатаева 117 лит Б, 310 кабинет",
                   phone="+7 747 143 7796", whatsapp="+7 747 143 7796",
                   map_embed="https://www.google.com/maps?q=Макатаева+117+Алматы&output=embed"),
            Branch(code="sayaly", name="Филиал Саялы", address="Саялы 72, цокольный этаж",
                   phone="+7 775 292 1400", whatsapp="+7 775 292 1400",
                   map_embed="https://www.google.com/maps?q=Саялы+72+Алматы&output=embed"),
        ]
        db.session.add_all(demo)
        db.session.commit()

    # Prices (обычные)
    if Price.query.count() == 0:
        demo_prices = [
            Price(title="Категория B", subtitle="популярно", price_text="от 100 000 ₸", is_highlight=False),
            Price(title="Пакет «Комфорт»", subtitle="рекомендуем", price_text="от 100 000 ₸", is_highlight=True),
            Price(title="Доп. занятия", subtitle="по запросу", price_text="от 100 000 ₸", is_highlight=False),
        ]
        db.session.add_all(demo_prices)
        db.session.commit()

    # Instructors
    if Instructor.query.count() == 0:
        demo_ins = [
            Instructor(
                name="Ерлан М.", branch_code="shugyla",
                experience="7 лет", car="Toyota",
                tags="Спокойно,Парковки,Город",
                photo_url="", is_active=True,
                category="B", rating=4.8, rating_count=125
            ),
            Instructor(
                name="Айбек С.", branch_code="tolebi",
                experience="5 лет", car="Hyundai",
                tags="Экзамен,Манёвры,Уверенность",
                photo_url="", is_active=True,
                category="A", rating=4.9, rating_count=83
            ),
            Instructor(
                name="Нуржан К.", branch_code="abaya",
                experience="4 года", car="Kia",
                tags="Мото,Город",
                photo_url="", is_active=True,
                category="A1", rating=4.7, rating_count=41
            ),
        ]
        db.session.add_all(demo_ins)
        db.session.commit()

    # Gallery (optional)
    if GalleryImage.query.count() == 0:
        demo_g = [
            GalleryImage(photo_url="uploads/gallery/demo1.jpg", title="Автодром", is_active=False, sort_order=1),
        ]
        db.session.add_all(demo_g)
        db.session.commit()

    # Teachers
    if Teacher.query.count() == 0:
        demo_t = [
            Teacher(
                name="Алина Н.", branch_code="shugyla",
                experience="6 лет", subject="ПДД / Теория",
                tags="ПДД,Разбор ошибок,Экзамен",
                photo_url="", is_active=True,
                rating=4.9, rating_count=210
            ),
            Teacher(
                name="Мұрат А.", branch_code="tolebi",
                experience="8 лет", subject="ПДД / Экзамен",
                tags="Тесты,Ситуации,Практика ПДД",
                photo_url="", is_active=True,
                rating=5.0, rating_count=180
            ),
        ]
        db.session.add_all(demo_t)
        db.session.commit()

    # ✅ HomePriceCard (главный экран)
    if HomePriceCard.query.count() == 0:
        demo_cards = [
            HomePriceCard(
                code="B_MT", category="B",
                col_title="МКПП",
                line1="2 месяца",
                line2="16 уроков теории",
                line3="5 уроков практики",
                price_text="100 000 тенге",
                sort_order=1, is_active=True
            ),
            HomePriceCard(
                code="B_AT", category="B",
                col_title="АКПП",
                line1="2 месяца",
                line2="16 уроков теории",
                line3="5 уроков практики",
                price_text="120 000 тенге",
                sort_order=2, is_active=True
            ),
            HomePriceCard(
                code="A", category="A",
                col_title="МКПП",
                line1="2 месяца",
                line2="16 уроков теории",
                line3="5 уроков практики",
                price_text="100 000 тенге",
                sort_order=1, is_active=True
            ),
            HomePriceCard(
                code="A1", category="A",
                col_title="МКПП",
                line1="2 месяца",
                line2="16 уроков теории",
                line3="5 уроков практики",
                price_text="95 000 тенге",
                sort_order=2, is_active=True
            ),
        ]
        db.session.add_all(demo_cards)
        db.session.commit()

app = create_app()



if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)