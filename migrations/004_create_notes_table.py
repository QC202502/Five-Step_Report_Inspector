import sqlite3

def migrate(db_path='research_reports.db'):
    """
    创建 report_notes 表来存储用户的笔记。
    """
    print("正在运行迁移：创建 report_notes 表...")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 创建 report_notes 表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS report_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            report_id INTEGER NOT NULL,
            note_content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (report_id) REFERENCES reports (id) ON DELETE CASCADE
        )
        ''')
        
        # 为 updated_at 创建触发器，以便在更新时自动更新时间戳
        cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS update_report_notes_updated_at
        AFTER UPDATE ON report_notes
        FOR EACH ROW
        BEGIN
            UPDATE report_notes SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
        END;
        ''')

        print("'report_notes' 表已成功创建或已存在。")
        conn.commit()

    except sqlite3.Error as e:
        print(f"数据库迁移失败: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    migrate() 