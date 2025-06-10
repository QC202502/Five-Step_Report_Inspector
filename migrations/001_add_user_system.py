import sqlite3
import hashlib
import secrets

def migrate(db_path='research_reports.db'):
    """
    创建用户系统所需的核心表结构：
    - users: 存储用户信息和凭证
    - user_profiles: 存储用户的个人资料
    - sessions: 存储用户会话
    并创建一个默认的管理员账户。
    """
    print("正在运行迁移 001: 添加用户系统...")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 创建用户表 (users)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            is_admin BOOLEAN DEFAULT 0
        )
        ''')
        print("- 'users' 表已创建或已存在。")

        # 创建用户资料表 (user_profiles)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            display_name TEXT,
            bio TEXT,
            avatar_url TEXT,
            preferred_industries TEXT DEFAULT '',
            notification_settings TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
        ''')
        print("- 'user_profiles' 表已创建或已存在。")

        # 创建会话表 (sessions)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            session_token TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            ip_address TEXT,
            user_agent TEXT,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
        ''')
        print("- 'sessions' 表已创建或已存在。")

        # 创建默认管理员账户（如果不存在）
        cursor.execute('SELECT COUNT(*) FROM users WHERE username = "admin"')
        if cursor.fetchone()[0] == 0:
            salt = secrets.token_hex(16)
            password = "admin123"
            password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
            
            cursor.execute('''
            INSERT INTO users (username, email, password_hash, salt, is_admin)
            VALUES (?, ?, ?, ?, ?)
            ''', ("admin", "admin@example.com", password_hash, salt, 1))
            
            user_id = cursor.lastrowid
            
            cursor.execute('''
            INSERT INTO user_profiles (user_id, display_name, bio)
            VALUES (?, ?, ?)
            ''', (user_id, "系统管理员", "默认管理员账户"))
            
            print("- 创建了默认管理员账户 (username: admin, password: admin123)。")
        else:
            print("- 管理员账户已存在，跳过创建。")
        
        conn.commit()
        print("迁移 001 完成。")

    except sqlite3.Error as e:
        print(f"迁移 001 失败: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    migrate() 