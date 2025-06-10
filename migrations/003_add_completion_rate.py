import sqlite3

def migrate(db_path='research_reports.db'):
    """
    为 reading_history 表添加 completion_rate 字段。
    """
    print("正在运行迁移：为 reading_history 添加 completion_rate 字段...")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 检查字段是否已存在
        cursor.execute("PRAGMA table_info(reading_history)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'completion_rate' not in columns:
            # 如果字段不存在，则添加
            cursor.execute('''
            ALTER TABLE reading_history 
            ADD COLUMN completion_rate REAL DEFAULT 0.0
            ''')
            print("成功为 'reading_history' 表添加 'completion_rate' 字段。")
        else:
            print("'completion_rate' 字段已存在于 'reading_history' 表中，跳过迁移。")

        conn.commit()
    except sqlite3.Error as e:
        print(f"数据库迁移失败: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    # 直接运行此脚本即可执行迁移
    migrate() 