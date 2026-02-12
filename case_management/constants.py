"""
案件管理常量配置
"""

# 固定目录模板配置
CASE_FOLDER_TEMPLATES = [
    {
        'folder_name': '案件文书',
        'folder_path': '/case_documents',
        'sort_order': 1,
        'description': '存放模板生成的各类法律文书'
    },
    {
        'folder_name': '正卷目录',
        'folder_path': '/main_volume',
        'sort_order': 2,
        'description': '存放案件正卷相关文档'
    },
    {
        'folder_name': '副卷目录',
        'folder_path': '/sub_volume',
        'sort_order': 3,
        'description': '存放案件副卷相关文档'
    },
    {
        'folder_name': '执行案内目录',
        'folder_path': '/execution_files',
        'sort_order': 4,
        'description': '存放执行阶段相关文档'
    },
    {
        'folder_name': '临时文件',
        'folder_path': '/temp_files',
        'sort_order': 5,
        'description': '存放临时性文件'
    }
]

# 文件上传配置
UPLOAD_CONFIG = {
    'MAX_FILE_SIZE': 50 * 1024 * 1024,  # 50MB
    'ALLOWED_EXTENSIONS': [
        '.docx', '.doc', '.pdf', '.txt',
        '.xlsx', '.xls', '.jpg', '.jpeg',
        '.png', '.zip', '.rar'
    ],
    'UPLOAD_BASE_PATH': 'uploads/cases',
}

# 文档类型映射
DOCUMENT_TYPE_MAPPING = {
    'template': '模板生成',
    'upload': '用户上传',
    'ai': 'AI生成',
    'parse': '解析源文件',
}

# 存储类型映射
STORAGE_TYPE_MAPPING = {
    'local': '本地存储',
    'oss': '阿里云OSS',
    'minio': 'MinIO',
}

