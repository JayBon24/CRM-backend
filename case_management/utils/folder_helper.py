"""
案件目录管理工具函数
"""
import os
import logging
from django.conf import settings

from ..constants import CASE_FOLDER_TEMPLATES

logger = logging.getLogger(__name__)


def create_case_folders(case_id):
    """
    为指定案件创建预设目录结构
    
    Args:
        case_id: 案件ID
        
    Returns:
        bool: 创建成功返回True
    """
    from ..models import CaseFolder, CaseManagement
    
    try:
        # 1. 在数据库中创建目录记录
        for template in CASE_FOLDER_TEMPLATES:
            folder, created = CaseFolder.objects.get_or_create(
                case_id=case_id,
                folder_path=template['folder_path'],
                is_deleted=False,
                defaults={
                    'folder_name': template['folder_name'],
                    'folder_type': 'fixed',
                    'sort_order': template['sort_order'],
                }
            )
            if created:
                logger.info(f"为案件 {case_id} 创建目录: {template['folder_name']}")
        
        # 2. 创建文件系统目录
        base_path = os.path.join(settings.MEDIA_ROOT, 'cases', str(case_id))
        for template in CASE_FOLDER_TEMPLATES:
            folder_path = os.path.join(base_path, template['folder_path'].strip('/'))
            os.makedirs(folder_path, exist_ok=True)
            logger.info(f"创建文件系统目录: {folder_path}")
            
        logger.info(f"案件 {case_id} 的目录结构初始化完成")
        return True
        
    except Exception as e:
        logger.error(f"创建案件目录失败 (case_id={case_id}): {str(e)}")
        raise


def get_case_document_tree(case_id):
    """
    获取案件文档树结构
    
    Args:
        case_id: 案件ID
        
    Returns:
        list: 文档树结构
    """
    from ..models import CaseFolder, CaseDocument
    
    # 获取所有目录
    folders = CaseFolder.objects.filter(
        case_id=case_id,
        is_deleted=False
    ).order_by('sort_order', 'id')
    
    # 获取所有文档（按 sort_order 升序排列）
    documents = CaseDocument.objects.filter(
        case_id=case_id,
        is_deleted=False
    ).select_related('template').order_by('sort_order', 'id')
    
    # 构建树形结构
    tree = []
    for folder in folders:
        folder_node = {
            'id': folder.id,
            'label': folder.folder_name,
            'path': folder.folder_path,
            'type': 'folder',
            'folder_type': folder.folder_type,
            'children': []
        }
        
        # 添加该目录下的文档
        folder_docs = documents.filter(folder_path=folder.folder_path)
        for doc in folder_docs:
            # 构建文档标签：确保 document_name 不包含扩展名，扩展名从 file_ext 获取
            # 如果 document_name 已经包含扩展名，需要移除以避免重复
            doc_name = doc.document_name or ""
            doc_ext = doc.file_ext or ""
            
            # 检查 document_name 是否已经包含扩展名（防止重复）
            doc_extensions = ['.docx', '.doc', '.xlsx', '.xls', '.pptx', '.ppt', '.pdf']
            for ext in doc_extensions:
                if doc_name.lower().endswith(ext):
                    # document_name 已经包含扩展名，移除它
                    doc_name = doc_name[:-len(ext)]
                    # 如果 file_ext 为空，使用检测到的扩展名
                    if not doc_ext:
                        doc_ext = ext
                    break
            
            # 组合标签：document_name + file_ext
            doc_label = f"{doc_name}{doc_ext}"
            
            doc_node = {
                'id': doc.id,  # 直接使用文档ID，不加doc_前缀
                'label': doc_label,
                'path': doc.file_url or '',  # 使用 file_url 获取完整URL
                'file_path': doc.file_path or '',  # 保留相对路径供参考
                'type': 'file',
                'document_id': doc.id,
                'file_size': doc.file_size,
                'document_type': doc.document_type,
                'version': doc.version,
                'print_count': doc.print_count,  # ✅ 打印数量
                'is_selected': getattr(doc, 'is_selected', False),  # ✅ 是否选中（新增字段）
                'sort_order': doc.sort_order,  # ✅ 排序序号
                'created_at': doc.create_datetime.strftime('%Y-%m-%d %H:%M:%S') if doc.create_datetime else None
            }
            folder_node['children'].append(doc_node)
        
        tree.append(folder_node)
    
    return tree


def get_folder_by_path(folder_path):
    """
    根据路径获取目录配置
    
    Args:
        folder_path: 目录路径
        
    Returns:
        dict: 目录配置信息，未找到返回None
    """
    for template in CASE_FOLDER_TEMPLATES:
        if template['folder_path'] == folder_path:
            return template
    return None


def validate_folder_path(folder_path):
    """
    验证目录路径是否有效
    
    Args:
        folder_path: 目录路径
        
    Returns:
        bool: 有效返回True
    """
    # 检查是否在预设目录中
    for template in CASE_FOLDER_TEMPLATES:
        if template['folder_path'] == folder_path:
            return True
    
    # TODO: 支持自定义目录验证
    return False


def get_case_file_path(case_id, folder_path, filename):
    """
    生成案件文件的完整存储路径
    
    Args:
        case_id: 案件ID
        folder_path: 目录路径
        filename: 文件名
        
    Returns:
        str: 完整文件路径
    """
    base_path = os.path.join(settings.MEDIA_ROOT, 'cases', str(case_id))
    folder_rel_path = folder_path.strip('/')
    full_path = os.path.join(base_path, folder_rel_path, filename)
    return full_path


def get_folder_display_name(folder_path):
    """
    根据路径获取目录显示名称
    
    Args:
        folder_path: 目录路径
        
    Returns:
        str: 目录显示名称
    """
    folder_config = get_folder_by_path(folder_path)
    if folder_config:
        return folder_config['folder_name']
    return folder_path


def save_uploaded_file(case_id, folder_path, file, document_name=None):
    """
    保存上传的文件并创建文档记录
    
    Args:
        case_id: 案件ID
        folder_path: 目录路径
        file: 上传的文件对象
        document_name: 文档显示名称（可选）
        
    Returns:
        CaseDocument: 创建的文档对象
    """
    from ..models import CaseDocument, CaseFolder
    import os
    from datetime import datetime
    
    try:
        # 生成文件名
        if not document_name:
            document_name = os.path.splitext(file.name)[0]
        
        # 获取文件扩展名
        file_ext = os.path.splitext(file.name)[1]
        
        # 生成唯一文件名（添加时间戳避免冲突）
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{document_name}_{timestamp}{file_ext}"
        
        # 构建文件保存路径
        base_path = os.path.join(settings.MEDIA_ROOT, 'cases', str(case_id))
        folder_rel_path = folder_path.strip('/')
        folder_full_path = os.path.join(base_path, folder_rel_path)
        
        # 确保目录存在
        os.makedirs(folder_full_path, exist_ok=True)
        
        # 保存文件
        file_full_path = os.path.join(folder_full_path, unique_filename)
        with open(file_full_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
        
        # 构建相对路径（用于数据库存储）
        file_relative_path = os.path.join('cases', str(case_id), folder_rel_path, unique_filename)
        
        # 查找关联的文件夹对象
        try:
            folder = CaseFolder.objects.get(
                case_id=case_id,
                folder_path=folder_path,
                is_deleted=False
            )
        except CaseFolder.DoesNotExist:
            folder = None
        
        # 创建文档记录
        document = CaseDocument.objects.create(
            case_id=case_id,
            folder=folder,
            folder_path=folder_path,
            document_name=document_name,
            document_type='upload',
            file_name=unique_filename,
            file_path=file_relative_path,
            file_size=file.size,
            file_ext=file_ext,
            storage_type='local',
            version=1
        )
        
        logger.info(f"文件上传成功: {file_relative_path}")
        return document
        
    except Exception as e:
        logger.error(f"保存上传文件失败: {str(e)}")
        raise

