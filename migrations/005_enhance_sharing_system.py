import sqlite3
import os

def migrate(db_path):
    """
    增强分享功能，添加分享统计和社交分享支持
    """
    print("执行迁移: 增强分享功能...")
    
    # 连接数据库
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 检查shared_links表是否已存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='shared_links'")
    if cursor.fetchone():
        print("- shared_links表已存在，添加额外字段...")
        
        # 检查user_id字段是否存在
        cursor.execute("PRAGMA table_info(shared_links)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # 如果user_id字段不存在，添加它
        if 'user_id' not in columns:
            cursor.execute('''
            ALTER TABLE shared_links ADD COLUMN user_id INTEGER REFERENCES users(id)
            ''')
            print("  - 添加user_id字段")
        
        # 如果share_type字段不存在，添加它
        if 'share_type' not in columns:
            cursor.execute('''
            ALTER TABLE shared_links ADD COLUMN share_type TEXT DEFAULT 'link'
            ''')
            print("  - 添加share_type字段")
            
        # 如果view_count字段不存在，添加它
        if 'view_count' not in columns:
            cursor.execute('''
            ALTER TABLE shared_links ADD COLUMN view_count INTEGER DEFAULT 0
            ''')
            print("  - 添加view_count字段")
            
        # 如果custom_message字段不存在，添加它
        if 'custom_message' not in columns:
            cursor.execute('''
            ALTER TABLE shared_links ADD COLUMN custom_message TEXT
            ''')
            print("  - 添加custom_message字段")
            
        # 如果share_title字段不存在，添加它
        if 'share_title' not in columns:
            cursor.execute('''
            ALTER TABLE shared_links ADD COLUMN share_title TEXT
            ''')
            print("  - 添加share_title字段")
    else:
        # 创建完整的shared_links表
        print("- 创建shared_links表...")
        cursor.execute('''
        CREATE TABLE shared_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            report_id INTEGER NOT NULL,
            token TEXT NOT NULL UNIQUE,
            share_type TEXT DEFAULT 'link',
            share_title TEXT,
            custom_message TEXT,
            view_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (report_id) REFERENCES reports(id)
        )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_shared_links_token ON shared_links(token)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_shared_links_user ON shared_links(user_id)')
    
    # 创建share_views表，用于记录分享链接的访问情况
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS share_views (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        shared_link_id INTEGER NOT NULL,
        viewer_ip TEXT,
        user_agent TEXT,
        referer TEXT,
        view_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (shared_link_id) REFERENCES shared_links(id)
    )
    ''')
    print("- 创建share_views表")
    
    # 提交更改
    conn.commit()
    conn.close()
    
    print("迁移完成: 分享功能增强成功")

if __name__ == "__main__":
    db_path = 'research_reports.db'
    if os.path.exists(db_path):
        migrate(db_path)
    else:
        print(f"错误: 数据库文件 {db_path} 不存在")
        exit(1) 