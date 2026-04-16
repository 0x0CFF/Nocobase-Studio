import os
import pwd
import grp
import json
import shutil
import textwrap
import requests
from datetime import datetime
from flask import Flask, request, jsonify

def dify_workflows(project_name):
    url = "http://192.168.31.97:10080/v1/workflows/run"
    headers = {
        'Authorization': 'Bearer app-8xEKcjhEkgYD6wkNdLTbDiPl',
        'Content-Type': 'application/json',
    }
    data = {
        "inputs": {"projectName": project_name},
        "response_mode": "blocking",
        "user": "0x0CFF"
    }

    try:
        # 设置超时时间，避免一直等待
        response = requests.post(url, headers=headers, data=json.dumps(data), timeout=10)
        # print(f"状态码: {response.status_code}")
        # 解析 JSON
        data = json.loads(response.text)
        status = data['data']['status']     # 工作流状态
        if status == "succeeded":
            return data['data']['outputs']['text']
        else:
            print("请求错误！")
            return 0
    except requests.exceptions.Timeout:
        print("请求超时！服务可能没有响应")
        return 0
    except requests.exceptions.ConnectionError as e:
        print(f"连接错误: {e}")
        return 0
    except Exception as e:
        print(f"其他错误: {e}")
        return 0

# 创建文件夹（支持修改所有者、组、权限，需 root 权限）
# 示例： create_secured_dir("/tmp/my_app_data", 0o750, owner="www-data", group="www-data")
def create_secured_dir(path, mode=None, owner=None, group=None):
    # 1. 创建目录（先临时清除 umask 以获得精确权限）
    old_umask = os.umask(0)
    try:
        os.makedirs(path, mode=mode, exist_ok=False)
    finally:
        os.umask(old_umask)

    # 2. 修改所有者和组（如果需要）
    if owner or group:
        uid = pwd.getpwnam(owner).pw_uid if owner else -1
        gid = grp.getgrnam(group).gr_gid if group else -1
        os.chown(path, uid, gid)

    print(f"[创建完成] 目录 {path} 已创建，权限 {oct(mode)}，所有者 {owner}:{group}")

# 设置文件的所有者、所属组和权限
def set_file_owner_and_permission(filepath, mode=None, owner=None, group=None):
    """
    设置文件的所有者、所属组和权限

    参数:
        filepath: 文件路径
        owner: 用户名（可选，None表示不修改）
        group: 组名（可选，None表示不修改）
        mode: 权限模式（如0o644，可选，None表示不修改）

    返回:
        bool: 成功返回True，失败返回False
    """
    try:
        # 检查文件是否存在
        if not os.path.exists(filepath):
            print(f"[系统错误] 文件 {filepath} 不存在")
            return False

        # 设置所有者和组
        if owner is not None or group is not None:
            uid = -1
            gid = -1

            if owner is not None:
                uid = pwd.getpwnam(owner).pw_uid

            if group is not None:
                gid = grp.getgrnam(group).gr_gid

            os.chown(filepath, uid, gid)
            print(f"[系统信息] 已设置所有者: {owner or '不变'}:{group or '不变'}")

        # 设置权限
        if mode is not None:
            os.chmod(filepath, mode)
            print(f"[系统信息] 已设置权限: {oct(mode)}")

        return True

    except PermissionError:
        print(f"[系统错误] 权限不足，需要 root 权限才能更改所有者")
        return False
    except KeyError as e:
        print(f"[系统错误] 用户或组不存在 - {e}")
        return False
    except Exception as e:
        print(f"[系统错误] {e}")
        return False

# 创建 Markdown 文件（支持修改所有者、组、权限，需 root 权限）
def create_secured_file(path, content, mode, owner=None, group=None):
    # 1. 写入内容
    with open(path, 'w') as f:
        f.write(content)

    # 2. 设置权限
    os.chmod(path, mode)

    # 3. 设置所有者和用户组
    try:
        # 获取用户ID（UID）
        uid = pwd.getpwnam(owner).pw_uid
        # 获取组ID（GID）
        gid = grp.getgrnam(group).gr_gid
        # 修改所有者和组
        os.chown(path, uid, gid)
        print(f"[创建完成] 目录 {path}，权限 {oct(mode)}，所有者 {owner}:{group}")

    except PermissionError as e:
        print(f"[系统错误] 权限不足，无法修改文件所有者或组")
        print(f"[系统错误] 详细信息: {e}")
        print(f"[系统错误] 提示：需要 root 权限才能修改文件所有者")

    except KeyError as e:
        print(f"[系统错误] 用户或用户组不存在")
        print(f"[系统错误] 详细信息: {e}")

    except Exception as e:
        print(f"[系统错误] 未知错误: {e}")

##################################################################################################################################################

app = Flask(__name__)

# 预设的 API Key（建议从环境变量读取，不要硬编码）
# API_KEY = os.environ.get("FOLDER_API_KEY", "your-secret-key-here")
API_KEY = "NkJAb2wucXFJXUZnu2pTWQKVSKjTEyTR"

##################################################################################################################################################

@app.route('/create_project_folder', methods=['POST'])
def create_project_folder():
    # 校验 API Key
    provided_key = request.headers.get('X-API-Key')
    if not provided_key or provided_key != API_KEY:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    # 从前端获取数据
    data = request.get_json()
    created_at = data.get('createdAt')                                # 创建日期
    project_type = data.get('projectType')                            # 项目类型
    unit_name = data.get('unitName')                                  # 甲方单位
    name_array = data.get('nameArray')                                # 甲方负责人
    project_name = data.get('projectName')                            # 项目名称

    # 校验
    if not created_at:
        return jsonify({"status": "error", "message": "创建日期不能为空"}), 400
    if not project_type:
        return jsonify({"status": "error", "message": "项目类型不能为空"}), 400
    if not unit_name:
        return jsonify({"status": "error", "message": "甲方单位不能为空"}), 400
    if not name_array:
        return jsonify({"status": "error", "message": "甲方负责人不能为空"}), 400
    if not project_name:
        return jsonify({"status": "error", "message": "项目名称不能为空"}), 400

    # 处理数据
    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
    date_str = dt.strftime('%Y.%m.%d')

    # 声明项目文件夹
    base_path = "/mnt/Workspace/协作盘"
    project_path = rf"{base_path}/{date_str}_{project_type}-{unit_name}-{"、".join(name_array)}-{project_name}"

    # 获取当前时间
    now = datetime.now()
    current_time = now.strftime("%Y.%m.%d %H:%M")
    # 格式化 Markdown 文本
    markdown_content = textwrap.dedent(f"""\
    # {project_name}

    ## 基本信息

    **甲方单位：** {unit_name}
    **甲方负责人：** {"、".join(name_array)}
    **稿件截止日期：** {date_str}

    ## 项目概述

    ---
    *自动生成于 {current_time}*
    """)

    # 创建项目文件夹
    try:
        match project_type:
            case "高校大赛" | "演示美化":
                create_secured_dir(rf"{project_path}", 0o775, owner="BOARD_R5", group="PUBLIC")
                create_secured_dir(rf"{project_path}/00_合同文件", 0o770, owner="BUSINESS_R5", group="BUSINESS")
                create_secured_dir(rf"{project_path}/01_项目框架", 0o775, owner="BOARD_R5", group="PUBLIC")
                create_secured_dir(rf"{project_path}/02_演示工程", 0o775, owner="BOARD_R5", group="PUBLIC")
                create_secured_dir(rf"{project_path}/02_演示工程/01_参考文件", 0o775, owner="BOARD_R5", group="PUBLIC")
                create_secured_dir(rf"{project_path}/02_演示工程/02_甲方素材", 0o775, owner="BOARD_R5", group="PUBLIC")
                create_secured_dir(rf"{project_path}/02_演示工程/02_甲方素材/动图", 0o775, owner="BOARD_R5", group="PUBLIC")
                create_secured_dir(rf"{project_path}/02_演示工程/02_甲方素材/工程", 0o775, owner="BOARD_R5", group="PUBLIC")
                create_secured_dir(rf"{project_path}/02_演示工程/02_甲方素材/模型", 0o775, owner="BOARD_R5", group="PUBLIC")
                create_secured_dir(rf"{project_path}/02_演示工程/02_甲方素材/视频", 0o775, owner="BOARD_R5", group="PUBLIC")
                create_secured_dir(rf"{project_path}/02_演示工程/02_甲方素材/图标", 0o775, owner="BOARD_R5", group="PUBLIC")
                create_secured_dir(rf"{project_path}/02_演示工程/02_甲方素材/图片", 0o775, owner="BOARD_R5", group="PUBLIC")
                create_secured_dir(rf"{project_path}/02_演示工程/02_甲方素材/文档", 0o775, owner="BOARD_R5", group="PUBLIC")
                create_secured_dir(rf"{project_path}/02_演示工程/02_甲方素材/音乐", 0o775, owner="BOARD_R5", group="PUBLIC")
                create_secured_dir(rf"{project_path}/02_演示工程/02_甲方素材/音效", 0o775, owner="BOARD_R5", group="PUBLIC")
                create_secured_dir(rf"{project_path}/02_演示工程/02_甲方素材/字体", 0o775, owner="BOARD_R5", group="PUBLIC")
                create_secured_dir(rf"{project_path}/02_演示工程/02_甲方素材/其他", 0o775, owner="BOARD_R5", group="PUBLIC")
                create_secured_dir(rf"{project_path}/02_演示工程/03_乙方素材", 0o775, owner="BOARD_R5", group="PUBLIC")
                create_secured_dir(rf"{project_path}/02_演示工程/03_乙方素材/动图", 0o775, owner="BOARD_R5", group="PUBLIC")
                create_secured_dir(rf"{project_path}/02_演示工程/03_乙方素材/工程", 0o775, owner="BOARD_R5", group="PUBLIC")
                create_secured_dir(rf"{project_path}/02_演示工程/03_乙方素材/模型", 0o775, owner="BOARD_R5", group="PUBLIC")
                create_secured_dir(rf"{project_path}/02_演示工程/03_乙方素材/视频", 0o775, owner="BOARD_R5", group="PUBLIC")
                create_secured_dir(rf"{project_path}/02_演示工程/03_乙方素材/图标", 0o775, owner="BOARD_R5", group="PUBLIC")
                create_secured_dir(rf"{project_path}/02_演示工程/03_乙方素材/图片", 0o775, owner="BOARD_R5", group="PUBLIC")
                create_secured_dir(rf"{project_path}/02_演示工程/03_乙方素材/文档", 0o775, owner="BOARD_R5", group="PUBLIC")
                create_secured_dir(rf"{project_path}/02_演示工程/03_乙方素材/音乐", 0o775, owner="BOARD_R5", group="PUBLIC")
                create_secured_dir(rf"{project_path}/02_演示工程/03_乙方素材/音效", 0o775, owner="BOARD_R5", group="PUBLIC")
                create_secured_dir(rf"{project_path}/02_演示工程/03_乙方素材/字体", 0o775, owner="BOARD_R5", group="PUBLIC")
                create_secured_dir(rf"{project_path}/02_演示工程/03_乙方素材/其他", 0o775, owner="BOARD_R5", group="PUBLIC")
                create_secured_dir(rf"{project_path}/02_演示工程/04_风格定稿", 0o775, owner="BOARD_R5", group="PUBLIC")
                create_secured_dir(rf"{project_path}/02_演示工程/05_历史版本", 0o775, owner="BOARD_R5", group="PUBLIC")
                create_secured_dir(rf"{project_path}/02_演示工程/06_输出文件", 0o775, owner="BOARD_R5", group="PUBLIC")
                create_secured_dir(rf"{project_path}/02_演示工程/06_输出文件/PDF", 0o775, owner="BOARD_R5", group="PUBLIC")
                create_secured_dir(rf"{project_path}/02_演示工程/06_输出文件/演示", 0o775, owner="BOARD_R5", group="PUBLIC")
                create_secured_dir(rf"{project_path}/02_演示工程/06_输出文件/图片", 0o775, owner="BOARD_R5", group="PUBLIC")
                create_secured_dir(rf"{project_path}/02_演示工程/06_输出文件/长图", 0o775, owner="BOARD_R5", group="PUBLIC")
                create_secured_dir(rf"{project_path}/02_演示工程/06_输出文件/视频", 0o775, owner="BOARD_R5", group="PUBLIC")
                create_secured_dir(rf"{project_path}/02_演示工程/06_输出文件/字体", 0o775, owner="BOARD_R5", group="PUBLIC")
                create_secured_dir(rf"{project_path}/03_辅助工程", 0o775, owner="BOARD_R5", group="PUBLIC")
                create_secured_dir(rf"{project_path}/04_包装工程", 0o775, owner="BOARD_R5", group="PUBLIC")
                # 创建项目要求文档
                create_secured_file(rf"{project_path}/02_演示工程/02_甲方素材/项目要求.md", markdown_content, mode=0o775, owner="BOARD_R5", group="PUBLIC")
                # 复制幻灯片母稿
                pptx_file = rf"{project_path}/02_演示工程/V1.0_{project_name}.pptx"
                shutil.copy2("./Assets/空白母稿.pptx", pptx_file)
                print(f"[创建完成] 文件 {pptx_file} 已创建")
                set_file_owner_and_permission(pptx_file, 0o775, owner="BOARD_R5", group="PUBLIC")
            case "项目微课":
                create_secured_dir(rf"{project_path}", 0o775, owner="BOARD_R5", group="PUBLIC")
                create_secured_dir(rf"{project_path}/00_合同文件", 0o770, owner="BUSINESS_R5", group="BUSINESS")
                create_secured_dir(rf"{project_path}/01_项目框架", 0o775, owner="BOARD_R5", group="PUBLIC")
                create_secured_dir(rf"{project_path}/01_项目框架/01_甲方词稿", 0o775, owner="BOARD_R5", group="PUBLIC")
                create_secured_dir(rf"{project_path}/01_项目框架/02_逐句词稿", 0o775, owner="BOARD_R5", group="PUBLIC")
                create_secured_dir(rf"{project_path}/02_演示工程", 0o775, owner="BOARD_R5", group="PUBLIC")
                # 创建子项目文件夹
                create_secured_dir(rf"{project_path}/03_视频工程", 0o775, owner="BOARD_R5", group="PUBLIC")
                # 创建子项目文件夹
                create_secured_dir(rf"{project_path}/04_动画工程", 0o775, owner="BOARD_R5", group="PUBLIC")
                # 创建子项目文件夹
            case _:
                pass
        print(rf"[创建完成] {project_path}")
        return jsonify({"status": "success", "path": project_path}), 200
    except Exception as e:
        print(rf"[创建失败] {project_path}")
        return jsonify({"status": "error", "message": str(e)}), 500

##################################################################################################################################################

@app.route('/create_project_manuscript', methods=['POST'])
def create_project_manuscript():
    # 校验 API Key
    provided_key = request.headers.get('X-API-Key')
    if not provided_key or provided_key != API_KEY:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    # 从前端获取数据
    data = request.get_json()
    created_at = data.get('createdAt')                                # 创建日期
    project_type = data.get('projectType')                            # 项目类型
    unit_name = data.get('unitName')                                  # 甲方单位
    name_array = data.get('nameArray')                                # 甲方负责人
    project_name = data.get('projectName')                            # 项目名称
    generative_manuscript = data.get('generativeManuscript')          # 生成式文稿
    
    # 校验
    if not created_at:
        return jsonify({"status": "error", "message": "创建日期不能为空"}), 400
    if not project_type:
        return jsonify({"status": "error", "message": "项目类型不能为空"}), 400
    if not unit_name:
        return jsonify({"status": "error", "message": "甲方单位不能为空"}), 400
    if not name_array:
        return jsonify({"status": "error", "message": "甲方负责人不能为空"}), 400
    if not project_name:
        return jsonify({"status": "error", "message": "项目名称不能为空"}), 400
    if not generative_manuscript:
        return jsonify({"status": "error", "message": "生成式文稿选项不能为空"}), 400

    # 处理数据
    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
    date_str = dt.strftime('%Y.%m.%d')

    # 声明项目文件夹
    base_path = "/mnt/Workspace/协作盘"
    project_path = rf"{base_path}/{date_str}_{project_type}-{unit_name}-{"、".join(name_array)}-{project_name}"

    if generative_manuscript == "是":
        try:
            match project_type:
                case "演示美化":
                    markdown_content = dify_workflows(project_name)
                    if markdown_content != 0:
                        # 写入文档
                        create_secured_file(rf"{project_path}/02_演示工程/02_甲方素材/文档/{project_name}.md", markdown_content, mode=0o775, owner="BOARD_R5", group="PUBLIC")
                        print(rf"[创建完成] {project_path}/02_演示工程/02_甲方素材/文档/{project_name}.md")
                        return jsonify({"status": "success"}), 200
                    else:
                        print("[错误信息] 工作流执行失败")
                        return jsonify({"status": "success"}), 200
                case "高校大赛":
                    print(rf"[温馨提示] 暂无生成式文稿工作流")
                    return jsonify({"status": "success"}), 200
                case "高校微课":
                    print(rf"[温馨提示] 暂无生成式文稿工作流")
                    return jsonify({"status": "success"}), 200
                case _:
                    pass
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
    
##################################################################################################################################################

@app.route('/archive_project_folder', methods=['POST'])
def archive_project_folder():
    # 校验 API Key
    provided_key = request.headers.get('X-API-Key')
    if not provided_key or provided_key != API_KEY:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    # 从前端获取数据
    data = request.get_json()
    created_at = data.get('createdAt')                                # 创建日期
    project_type = data.get('projectType')                            # 项目类型
    unit_name = data.get('unitName')                                  # 甲方单位
    name_array = data.get('nameArray')                                # 甲方负责人
    project_name = data.get('projectName')                            # 项目名称
    
    # 校验
    if not created_at:
        return jsonify({"status": "error", "message": "创建日期不能为空"}), 400
    if not project_type:
        return jsonify({"status": "error", "message": "项目类型不能为空"}), 400
    if not unit_name:
        return jsonify({"status": "error", "message": "甲方单位不能为空"}), 400
    if not name_array:
        return jsonify({"status": "error", "message": "甲方负责人不能为空"}), 400
    if not project_name:
        return jsonify({"status": "error", "message": "项目名称不能为空"}), 400

    # 处理数据
    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
    date_str = dt.strftime('%Y.%m.%d')

    # 声明项目文件夹
    base_path = "/mnt/Workspace/协作盘"
    project_path = rf"{base_path}/{date_str}_{project_type}-{unit_name}-{"、".join(name_array)}-{project_name}"


    try:
        # TODO: 配置归档脚本
        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(rf"[创建失败] {project_path}")
        return jsonify({"status": "error", "message": str(e)}), 500

##################################################################################################################################################

from waitress import serve

if __name__ == '__main__':
    # 启动服务
    # app.run(host="0.0.0.0", port=6000, debug=True)
    serve(app, host="0.0.0.0", port=6000)