-- 研报分析结果表
CREATE TABLE IF NOT EXISTS report_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER NOT NULL,                  -- 关联到reports表的id
    analyzer_type TEXT NOT NULL,                 -- 分析器类型（如'claude'或'deepseek'）
    completeness_score INTEGER NOT NULL,         -- 完整度评分
    evaluation TEXT NOT NULL,                    -- 总体评价
    one_line_summary TEXT,                       -- 一句话总结
    full_analysis TEXT NOT NULL,                 -- 完整分析文本
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE
);

-- 五步法各步骤分析结果表
CREATE TABLE IF NOT EXISTS step_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id INTEGER NOT NULL,                -- 关联到report_analysis表的id
    step_name TEXT NOT NULL,                     -- 步骤名称（信息/逻辑/超预期/催化剂/结论）
    found BOOLEAN NOT NULL,                      -- 是否找到
    description TEXT,                            -- 描述/评价
    step_score INTEGER NOT NULL,                 -- 步骤评分
    framework_summary TEXT,                      -- 框架梳理内容
    FOREIGN KEY (analysis_id) REFERENCES report_analysis(id) ON DELETE CASCADE
);

-- 改进建议表
CREATE TABLE IF NOT EXISTS improvement_suggestions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id INTEGER NOT NULL,                -- 关联到report_analysis表的id
    point TEXT NOT NULL,                         -- 待完善点
    suggestion TEXT NOT NULL,                    -- 具体建议
    FOREIGN KEY (analysis_id) REFERENCES report_analysis(id) ON DELETE CASCADE
); 