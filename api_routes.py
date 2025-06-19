import os
import time
import uuid
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, session, current_app
import logging

from database import get_db_connection

# 配置日志
logger = logging.getLogger(__name__)

# 创建API蓝图
api = Blueprint('api', __name__)

# API路由 - 笔记系统
@api.route('/report/<int:report_id>/notes', methods=['GET', 'POST'])
def report_notes(report_id):
    """获取或添加研报笔记"""
    if request.method == 'GET':
        # 获取笔记
        try:
            if 'user' not in session:
                return jsonify({'success': False, 'message': '未登录，无法获取笔记'}), 401

            user_id = session['user']['id']
            
            # 从数据库获取笔记
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, user_id, report_id, content, created_at, updated_at
                FROM user_notes
                WHERE user_id = ? AND report_id = ?
                ORDER BY created_at DESC
            ''', (user_id, report_id))
            
            notes = []
            for row in cursor.fetchall():
                notes.append({
                    'id': row[0],
                    'user_id': row[1],
                    'report_id': row[2],
                    'content': row[3],
                    'created_at': row[4],
                    'updated_at': row[5]
                })
            
            conn.close()
            
            return jsonify({'success': True, 'notes': notes})
            
        except Exception as e:
            logger.error(f"获取笔记时出错: {str(e)}")
            return jsonify({'success': False, 'message': '获取笔记失败'}), 500
            
    elif request.method == 'POST':
        # 添加笔记
        try:
            if 'user' not in session:
                return jsonify({'success': False, 'message': '未登录，无法添加笔记'}), 401
            
            data = request.get_json()
            if not data or 'content' not in data:
                return jsonify({'success': False, 'message': '缺少必要参数'}), 400
            
            user_id = session['user']['id']
            content = data['content']
            
            # 检查内容长度
            if len(content) < 1:
                return jsonify({'success': False, 'message': '笔记内容不能为空'}), 400
                
            if len(content) > 1000:
                return jsonify({'success': False, 'message': '笔记内容不能超过1000字符'}), 400
            
            # 添加到数据库
            conn = get_db_connection()
            cursor = conn.cursor()
            
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute('''
                INSERT INTO user_notes (user_id, report_id, content, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, report_id, content, now, now))
            
            conn.commit()
            note_id = cursor.lastrowid
            conn.close()
            
            return jsonify({'success': True, 'note_id': note_id})
            
        except Exception as e:
            logger.error(f"添加笔记时出错: {str(e)}")
            return jsonify({'success': False, 'message': '添加笔记失败'}), 500

@api.route('/notes/<int:note_id>', methods=['PUT', 'DELETE'])
def manage_note(note_id):
    """更新或删除笔记"""
    if 'user' not in session:
        return jsonify({'success': False, 'message': '未登录，无法操作笔记'}), 401
    
    user_id = session['user']['id']
    
    # 验证笔记归属
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT user_id FROM user_notes WHERE id = ?', (note_id,))
    note = cursor.fetchone()
    
    if not note:
        conn.close()
        return jsonify({'success': False, 'message': '笔记不存在'}), 404
        
    if note[0] != user_id:
        conn.close()
        return jsonify({'success': False, 'message': '无权操作此笔记'}), 403
    
    if request.method == 'PUT':
        # 更新笔记
        try:
            data = request.get_json()
            if not data or 'content' not in data:
                conn.close()
                return jsonify({'success': False, 'message': '缺少必要参数'}), 400
            
            content = data['content']
            
            # 检查内容长度
            if len(content) < 1:
                conn.close()
                return jsonify({'success': False, 'message': '笔记内容不能为空'}), 400
                
            if len(content) > 1000:
                conn.close()
                return jsonify({'success': False, 'message': '笔记内容不能超过1000字符'}), 400
            
            # 更新笔记
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute('''
                UPDATE user_notes
                SET content = ?, updated_at = ?
                WHERE id = ?
            ''', (content, now, note_id))
            
            conn.commit()
            conn.close()
            
            return jsonify({'success': True})
            
        except Exception as e:
            logger.error(f"更新笔记时出错: {str(e)}")
            conn.close()
            return jsonify({'success': False, 'message': '更新笔记失败'}), 500
            
    elif request.method == 'DELETE':
        # 删除笔记
        try:
            cursor.execute('DELETE FROM user_notes WHERE id = ?', (note_id,))
            
            conn.commit()
            conn.close()
            
            return jsonify({'success': True})
            
        except Exception as e:
            logger.error(f"删除笔记时出错: {str(e)}")
            conn.close()
            return jsonify({'success': False, 'message': '删除笔记失败'}), 500

@api.route('/report/<int:report_id>/mark_read', methods=['POST'])
def mark_read(report_id):
    """标记研报为已读"""
    if 'user' not in session:
        return jsonify({'success': False, 'message': '未登录，无法标记已读'}), 401
        
    user_id = session['user']['id']
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查是否已存在记录
        cursor.execute('SELECT id FROM user_read_records WHERE user_id = ? AND report_id = ?', 
                      (user_id, report_id))
                      
        if cursor.fetchone():
            # 更新已读时间
            cursor.execute('''
                UPDATE user_read_records
                SET read_at = ?
                WHERE user_id = ? AND report_id = ?
            ''', (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), user_id, report_id))
        else:
            # 插入新记录
            cursor.execute('''
                INSERT INTO user_read_records (user_id, report_id, read_at)
                VALUES (?, ?, ?)
            ''', (user_id, report_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"标记已读时出错: {str(e)}")
        return jsonify({'success': False, 'message': '标记已读失败'}), 500

@api.route('/report/<int:report_id>/share/link', methods=['POST'])
def create_share_link(report_id):
    """创建分享链接"""
    if 'user' not in session:
        return jsonify({'success': False, 'message': '未登录，无法创建分享'}), 401
        
    user_id = session['user']['id']
    
    try:
        data = request.get_json() or {}
        title = data.get('title', '')
        message = data.get('message', '')
        expires_days = data.get('expires_days', 30)  # 默认30天
        
        # 验证参数
        if expires_days < 1 or expires_days > 365:
            return jsonify({'success': False, 'message': '有效期必须在1-365天内'}), 400
            
        if len(title) > 100:
            return jsonify({'success': False, 'message': '标题不能超过100字符'}), 400
            
        if len(message) > 500:
            return jsonify({'success': False, 'message': '消息不能超过500字符'}), 400
        
        # 生成分享ID
        share_id = str(uuid.uuid4()).replace('-', '')[:16]
        
        # 计算过期时间
        expires_at = (datetime.now() + timedelta(days=expires_days)).strftime('%Y-%m-%d %H:%M:%S')
        
        # 保存到数据库
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO shared_reports (
                share_id, user_id, report_id, title, message, 
                created_at, expires_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            share_id, user_id, report_id, title, message, 
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'), expires_at
        ))
        
        conn.commit()
        conn.close()
        
        # 生成分享URL
        share_url = f"{request.host_url.rstrip('/')}/shared/{share_id}"
        
        return jsonify({'success': True, 'share_id': share_id, 'share_url': share_url})
        
    except Exception as e:
        logger.error(f"创建分享链接时出错: {str(e)}")
        return jsonify({'success': False, 'message': '创建分享链接失败'}), 500

@api.route('/report/<int:report_id>/share/image', methods=['POST'])
def create_share_image(report_id):
    """创建分享图片"""
    if 'user' not in session:
        return jsonify({'success': False, 'message': '未登录，无法创建分享图片'}), 401
        
    user_id = session['user']['id']
    
    try:
        data = request.get_json() or {}
        title = data.get('title', '')
        
        # 验证参数
        if len(title) > 100:
            return jsonify({'success': False, 'message': '标题不能超过100字符'}), 400
        
        # 获取研报数据
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM reports WHERE id = ?", (report_id,))
        report = cursor.fetchone()
        conn.close()
        
        if not report:
            return jsonify({'success': False, 'message': '研报不存在'}), 404
        
        # 生成唯一文件名
        img_filename = f"report_{report_id}_analysis_{time.time()}.png"
        img_path = os.path.join(current_app.static_folder, 'share_images', img_filename)
        
        # 确保目录存在
        os.makedirs(os.path.dirname(img_path), exist_ok=True)
        
        # 在这里实现图片生成逻辑
        # 这里使用简单的示例，实际应用中可能需要使用第三方库如Pillow或wkhtmltoimage
        
        # 为了示例，创建一个空图片文件
        with open(img_path, 'w') as f:
            f.write('')
        
        # 生成分享图片URL
        image_url = f"{request.host_url.rstrip('/')}/static/share_images/{img_filename}"
        
        # 记录分享图片
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO report_share_images (
                user_id, report_id, image_path, title, created_at
            ) VALUES (?, ?, ?, ?, ?)
        ''', (
            user_id, report_id, img_filename, title,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'image_url': image_url})
        
    except Exception as e:
        logger.error(f"创建分享图片时出错: {str(e)}")
        return jsonify({'success': False, 'message': '创建分享图片失败'}), 500

@api.route('/report/<int:report_id>/generate_video_script', methods=['POST'])
def generate_video_script_api(report_id):
    """生成视频脚本API"""
    try:
        # 获取研报数据
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM reports WHERE id = ?", (report_id,))
        report = cursor.fetchone()
        conn.close()
        
        if not report:
            return jsonify({'success': False, 'message': '研报不存在'}), 404
        
        # 从已有分析结果生成脚本
        title = report['title']
        
        # 提取关键信息
        script_parts = []
        
        # 添加开场白
        script_parts.append(f"大家好，今天我们来分析一份由{report['org']}发布的研究报告：《{title}》。")
        
        # 添加评级和行业
        if report['rating']:
            script_parts.append(f"这份报告给出了{report['rating']}评级。")
        if report['industry']:
            script_parts.append(f"关于{report['industry']}行业。")
        
        # 获取分析结果
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取一句话总结
        cursor.execute("SELECT one_line_summary FROM report_full_analysis WHERE report_id = ?", (report_id,))
        summary = cursor.fetchone()
        if summary and summary[0]:
            script_parts.append(f"\n核心观点：{summary[0]}")
        
        # 获取各步骤分析
        cursor.execute("""
            SELECT step_name, found, framework_summary 
            FROM analysis_results 
            WHERE report_id = ? 
            ORDER BY CASE 
                WHEN step_name = '信息' THEN 1
                WHEN step_name = '逻辑' THEN 2
                WHEN step_name = '超预期' THEN 3
                WHEN step_name = '催化剂' THEN 4
                WHEN step_name = '结论' THEN 5
                ELSE 6
            END
        """, (report_id,))
        
        steps = cursor.fetchall()
        conn.close()
        
        step_intros = {
            '信息': "首先，关于信息维度",
            '逻辑': "在逻辑分析方面",
            '超预期': "关于超预期因素",
            '催化剂': "重要的催化剂包括",
            '结论': "最后，报告的结论是"
        }
        
        for step in steps:
            step_name, found, framework_summary = step
            if found and step_name in step_intros:
                script_parts.append(f"\n{step_intros[step_name]}：")
                if framework_summary:
                    script_parts.append(framework_summary)
        
        # 添加结语
        script_parts.append("\n以上就是今天的分析，感谢收看！")
        
        # 拼接脚本
        script = "\n".join(script_parts)
        
        # 保存到数据库
        conn = get_db_connection()
        cursor = conn.cursor()
        
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 检查是否已存在
        cursor.execute('SELECT id FROM video_scripts WHERE report_id = ?', (report_id,))
        existing = cursor.fetchone()
        
        if existing:
            # 更新现有脚本
            cursor.execute('''
                UPDATE video_scripts 
                SET script_text = ?, updated_at = ?
                WHERE report_id = ?
            ''', (script, now, report_id))
        else:
            # 创建新脚本
            cursor.execute('''
                INSERT INTO video_scripts (report_id, title, script_text, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (report_id, f"{title}视频脚本", script, now, now))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True, 
            'script': script,
            'title': title
        })
        
    except Exception as e:
        logger.error(f"生成视频脚本时出错: {str(e)}")
        return jsonify({'success': False, 'message': '生成视频脚本失败'}), 500 