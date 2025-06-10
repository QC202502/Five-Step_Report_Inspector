import sqlite3
import json

def migrate(db_path='research_reports.db'):
    """
    创建推荐与用户个性化设置所需的表结构：
    - user_preferences: 存储各类用户偏好设置
    - reading_history: 存储用户的详细阅读历史
    - search_history: 存储用户的搜索历史
    """
    print("正在运行迁移 002: 添加推荐与个性化系统...")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 创建用户偏好设置表 (user_preferences)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            preference_type TEXT NOT NULL,
            preference_data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            UNIQUE (user_id, preference_type)
        )
        ''')
        print("- 'user_preferences' 表已创建或已存在。")

        # 创建阅读历史表 (reading_history)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS reading_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            report_id INTEGER NOT NULL,
            read_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            read_duration INTEGER DEFAULT 0,
            is_completed BOOLEAN DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (report_id) REFERENCES reports (id) ON DELETE CASCADE,
            UNIQUE (user_id, report_id)
        )
        ''')
        print("- 'reading_history' 表已创建或已存在。")
        
        # 创建搜索历史表 (search_history)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            search_query TEXT NOT NULL,
            search_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            result_count INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
        ''')
        print("- 'search_history' 表已创建或已存在。")

        # 为现有用户添加默认偏好设置
        print("- 正在为现有用户添加默认偏好设置...")
        cursor.execute("SELECT id FROM users")
        users = cursor.fetchall()
        
        default_prefs = {
            'recommendation': {
                'weight_score': 40, 'weight_time': 30, 'weight_industry': 30,
                'focused_industries': [], 'preferred_report_types': [],
                'followed_organizations': [], 'show_recommendations': True,
                'show_recommendation_modal': True, 'auto_mark_read': True
            },
            'reading': {
                'default_view': 'card', 'reports_per_page': 20, 'default_sort': 'date',
                'sort_desc': True, 'auto_expand_summary': True, 'auto_expand_analysis': False
            },
            'privacy': {
                'collect_reading_history': True, 'collect_search_history': True,
                'show_profile': True, 'show_reading_history': False
            },
            'notification':{
                'email': True, 'site': True, 'new_reports': True,
                'industry_reports': True, 'high_quality': True
            }
        }
        
        for user in users:
            user_id = user[0]
            for pref_type, pref_data in default_prefs.items():
                cursor.execute(
                    "INSERT OR IGNORE INTO user_preferences (user_id, preference_type, preference_data) VALUES (?, ?, ?)",
                    (user_id, pref_type, json.dumps(pref_data))
                )
        print("- 默认偏好设置添加完成。")

        conn.commit()
        print("迁移 002 完成。")

    except sqlite3.Error as e:
        print(f"迁移 002 失败: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    migrate() 