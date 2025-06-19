import sqlite3
import os

def migrate(db_path):
    """
    创建shared_reports表，用于存储分享记录
    """
    print("执行迁移: 创建shared_reports表...")
    
    # 连接数据库
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 创建shared_reports表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS shared_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        report_id INTEGER NOT NULL,
        share_token VARCHAR(64) NOT NULL UNIQUE,
        title VARCHAR(255),
        custom_message TEXT,
        expires_at DATETIME NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        view_count INTEGER DEFAULT 0,
        is_active BOOLEAN DEFAULT 1,
        share_type VARCHAR(20) DEFAULT 'link',
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (report_id) REFERENCES reports(id)
    )
    ''')
    
    # 创建索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_share_token ON shared_reports(share_token)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_report ON shared_reports(user_id, report_id)')
    
    # 提交更改
    conn.commit()
    conn.close()
    
    print("迁移完成: shared_reports表创建成功") 