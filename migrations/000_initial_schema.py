import sqlite3

def migrate(db_path='research_reports.db'):
    """
    创建数据库的初始核心表结构：
    - reports: 存储研报基本信息
    - analysis_results: 存储五步法各步骤的分析结果
    - report_full_analysis: 存储完整的分析文本和一句话总结
    """
    print("正在运行迁移 000: 创建初始数据库结构...")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 创建研报表 (reports)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            link TEXT UNIQUE NOT NULL,
            abstract TEXT,
            content_preview TEXT,
            full_content TEXT,
            industry TEXT,
            rating TEXT,
            org TEXT,
            date TEXT,
            analysis_method TEXT,
            completeness_score INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        ''')
        print("- 'reports' 表已创建或已存在。")

        # 创建分析结果表 (analysis_results)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS analysis_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER NOT NULL,
            step_name TEXT NOT NULL,
            found INTEGER NOT NULL,
            keywords TEXT,
            evidence TEXT,
            description TEXT,
            framework_summary TEXT,
            improvement_suggestions TEXT,
            step_score INTEGER,
            FOREIGN KEY (report_id) REFERENCES reports (id) ON DELETE CASCADE,
            UNIQUE (report_id, step_name)
        )
        ''')
        print("- 'analysis_results' 表已创建或已存在。")

        # 创建报告完整分析表 (report_full_analysis)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS report_full_analysis (
            report_id INTEGER PRIMARY KEY,
            full_analysis_text TEXT,
            one_line_summary TEXT,
            FOREIGN KEY (report_id) REFERENCES reports (id) ON DELETE CASCADE
        )
        ''')
        print("- 'report_full_analysis' 表已创建或已存在。")
        
        conn.commit()
        print("迁移 000 完成。")

    except sqlite3.Error as e:
        print(f"迁移 000 失败: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    migrate() 