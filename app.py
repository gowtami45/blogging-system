from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import jwt, datetime
from pg8000 import connect

app = Flask(__name__)
CORS(app)

SECRET_KEY = "blog-secret-key"

# ---------------- DATABASE ----------------
def get_db():
    return connect(
        host="localhost",
        database="blog_db",
        user="postgres",
        password="gowthami"   # change if needed
    )

def init_tables():
    db = get_db()
    cur = db.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS blogs (
        id SERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        user_id INTEGER REFERENCES users(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS comments (
        id SERIAL PRIMARY KEY,
        comment TEXT,
        blog_id INTEGER REFERENCES blogs(id)
    )
    """)

    db.commit()
    cur.close()
    db.close()

init_tables()

# ---------------- HTML ROUTES ----------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/register")
def register_page():
    return render_template("register.html")

@app.route("/login")
def login_page():
    return render_template("login.html")

@app.route("/create-blog")
def create_blog_page():
    return render_template("create_blog.html")

@app.route("/blogs-page")
def blogs_page():
    return render_template("blogs.html")

# ---------------- AUTH APIs ----------------
@app.route("/api/register", methods=["POST"])
def register():
    data = request.json
    db = get_db()
    cur = db.cursor()

    cur.execute(
        "INSERT INTO users (username, password) VALUES (%s, %s)",
        (data["username"], generate_password_hash(data["password"]))
    )

    db.commit()
    cur.close()
    db.close()
    return jsonify(msg="User Registered")

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    db = get_db()
    cur = db.cursor()

    cur.execute("SELECT id, password FROM users WHERE username=%s",
                (data["username"],))
    user = cur.fetchone()

    if not user or not check_password_hash(user[1], data["password"]):
        return jsonify(error="Invalid credentials"), 401

    token = jwt.encode(
        {
            "user_id": user[0],
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        },
        SECRET_KEY,
        algorithm="HS256"
    )

    return jsonify(token=token)

# ---------------- BLOG APIs ----------------
@app.route("/api/blogs", methods=["POST"])
def create_blog():
    auth = request.headers.get("Authorization")
    print("API HIT")
    print("AUTH:", auth)

    if not auth:
        return jsonify(error="Token missing"), 401

    token = auth.split(" ")[1]

    decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    user_id = decoded["user_id"]

    data = request.json
    print("DATA:", data)

    db = get_db()
    cur = db.cursor()

    cur.execute(
        "INSERT INTO blogs (title, content, user_id) VALUES (%s, %s, %s)",
        (data["title"], data["content"], user_id)
    )

    db.commit()
    cur.close()
    db.close()

    return jsonify(msg="Inserted")

@app.route("/api/blogs", methods=["GET"])
def get_blogs():
    db = get_db()
    cur = db.cursor()

    cur.execute("""
    SELECT blogs.id, title, content, username
    FROM blogs JOIN users ON blogs.user_id = users.id
    """)
    blogs = cur.fetchall()

    cur.close()
    db.close()

    return jsonify([
        {"id": b[0], "title": b[1], "content": b[2], "author": b[3]}
        for b in blogs
    ])

# ---------------- COMMENT API ----------------
@app.route("/api/comment", methods=["POST"])
def add_comment():
    data = request.json
    db = get_db()
    cur = db.cursor()

    cur.execute(
        "INSERT INTO comments (comment, blog_id) VALUES (%s, %s)",
        (data["comment"], data["blog_id"])
    )

    db.commit()
    cur.close()
    db.close()
    return jsonify(msg="Comment Added")
@app.route("/api/comments/<int:blog_id>", methods=["GET"])
def get_comments(blog_id):
    db = get_db()
    cur = db.cursor()

    cur.execute("""
    SELECT id, comment FROM comments WHERE blog_id=%s
    """, (blog_id,))

    comments = cur.fetchall()

    cur.close()
    db.close()

    return jsonify([
        {"id": c[0], "comment": c[1]} for c in comments
    ])

@app.route("/api/blogs/<int:blog_id>", methods=["DELETE"])
def delete_blog(blog_id):
    db = get_db()
    cur = db.cursor()

    # delete comments first
    cur.execute("DELETE FROM comments WHERE blog_id=%s", (blog_id,))
    # delete blog
    cur.execute("DELETE FROM blogs WHERE id=%s", (blog_id,))

    db.commit()
    cur.close()
    db.close()

    return jsonify(msg="Blog deleted")
@app.route("/api/comment/<int:comment_id>", methods=["DELETE"])
def delete_comment(comment_id):
    db = get_db()
    cur = db.cursor()

    cur.execute("DELETE FROM comments WHERE id=%s", (comment_id,))

    db.commit()
    cur.close()
    db.close()

    return jsonify(msg="Comment deleted")


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
