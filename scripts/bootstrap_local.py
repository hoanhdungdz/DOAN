"""Provision only the isolated MySQL instance started for this project (port 3307)."""

from pathlib import Path
import secrets
import MySQLdb

base = Path(__file__).resolve().parents[1]
env_path = base / "be" / ".env"
if env_path.exists():
    raise SystemExit("be/.env already exists; refusing to replace configuration.")
db = MySQLdb.connect(host="127.0.0.1", port=3307, user="root", passwd="")
root_password = secrets.token_hex(32)
app_password = secrets.token_hex(32)
with db.cursor() as c:
    c.execute("CREATE DATABASE tech_retail CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    c.execute("CREATE USER 'tech_retail'@'localhost' IDENTIFIED BY %s", (app_password,))
    c.execute("GRANT ALL PRIVILEGES ON tech_retail.* TO 'tech_retail'@'localhost'")
    c.execute("GRANT ALL PRIVILEGES ON test_tech_retail.* TO 'tech_retail'@'localhost'")
    c.execute("ALTER USER 'root'@'localhost' IDENTIFIED BY %s", (root_password,))
runtime = base / ".runtime"
runtime.mkdir(exist_ok=True)
(runtime / "mysql-root.cnf").write_text(
    "[client]\nhost=127.0.0.1\nport=3307\nuser=root\npassword=" + root_password + "\n",
    encoding="utf-8",
)
template = (base / "be" / ".env.example").read_text(encoding="utf-8")
template = (
    template.replace("CHANGE_ME_FOR_LOCAL_DEVELOPMENT", secrets.token_hex(48))
    .replace("YOUR_DB_USER", "tech_retail")
    .replace("YOUR_DB_PASSWORD", app_password)
    .replace("DB_PORT=3306", "DB_PORT=3307")
)
env_path.write_text(template, encoding="utf-8")
print("Isolated MySQL configured on 127.0.0.1:3307. Secrets saved only in ignored local files.")
