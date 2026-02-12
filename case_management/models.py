"""
案例管理模型
"""
import os
from django.db import models
from dvadmin.system.models import Users
from dvadmin.utils.models import CoreModel, SoftDeleteModel


class CaseManagement(SoftDeleteModel):
    """案例管理模型"""
    STATUS_PUBLIC_POOL = "PUBLIC_POOL"
    STATUS_FOLLOW_UP = "FOLLOW_UP"
    STATUS_CASE = "CASE"
    STATUS_PAYMENT = "PAYMENT"
    STATUS_WON = "WON"
    STATUS_CHOICES = (
        (STATUS_PUBLIC_POOL, "公海"),
        (STATUS_FOLLOW_UP, "跟进"),
        (STATUS_CASE, "交案"),
        (STATUS_PAYMENT, "回款"),
        (STATUS_WON, "赢单"),
    )

    SALES_STAGE_PUBLIC = "PUBLIC_POOL"
    SALES_STAGE_BLANK = "BLANK"
    SALES_STAGE_MEETING = "MEETING"
    SALES_STAGE_CASE = "CASE"
    SALES_STAGE_PAYMENT = "PAYMENT"
    SALES_STAGE_WON = "WON"
    SALES_STAGE_CHOICES = (
        (SALES_STAGE_PUBLIC, "公海"),
        (SALES_STAGE_BLANK, "跟进-空白"),
        (SALES_STAGE_MEETING, "跟进-面谈"),
        (SALES_STAGE_CASE, "交案"),
        (SALES_STAGE_PAYMENT, "回款"),
        (SALES_STAGE_WON, "赢单"),
    )

    case_number = models.CharField(max_length=100, verbose_name="案例编号", help_text="案例编号")
    case_name = models.CharField(max_length=200, verbose_name="案例名称", help_text="案例名称")
    case_type = models.CharField(max_length=50, verbose_name="案例类型", help_text="案例类型")
    case_status = models.CharField(max_length=50, verbose_name="案例状态", help_text="案例状态", default="待处理")
    case_description = models.TextField(verbose_name="案例描述", help_text="案例描述", null=True, blank=True)
    case_date = models.DateField(verbose_name="案例日期", help_text="案例日期", null=True, blank=True)
    case_result = models.TextField(verbose_name="案例结果", help_text="案例结果", null=True, blank=True)
    case_notes = models.TextField(verbose_name="案例备注", help_text="案例备注", null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_FOLLOW_UP,
        verbose_name="案件状态",
        db_index=True,
    )
    sales_stage = models.CharField(
        max_length=20,
        choices=SALES_STAGE_CHOICES,
        default=SALES_STAGE_BLANK,
        verbose_name="销售阶段",
        db_index=True,
    )
    create_datetime = models.DateTimeField(
        auto_now_add=True,
        null=True,
        blank=True,
        help_text="创建时间",
        verbose_name="创建时间",
    )
    update_datetime = models.DateTimeField(
        auto_now=True,
        null=True,
        blank=True,
        help_text="更新时间",
        verbose_name="更新时间",
    )

    customer = models.ForeignKey(
        "customer_management.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cases",
        verbose_name="关联客户",
        help_text="关联客户",
        db_constraint=False,
    )
    owner_user = models.ForeignKey(
        Users,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="case_owner_users",
        verbose_name="经办人",
        help_text="经办人",
        db_constraint=False,
    )
    owner_user_name = models.CharField(
        max_length=150,
        verbose_name="经办人姓名",
        help_text="经办人姓名",
        null=True,
        blank=True,
    )
    handlers = models.ManyToManyField(
        Users,
        through="case_management.CaseHandler",
        through_fields=("case", "user"),
        related_name="handled_cases",
        blank=True,
        verbose_name="经办人列表",
    )
    contract = models.ForeignKey(
        "customer_management.Contract",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="case_relations",
        verbose_name="关联合同",
        help_text="关联合同",
        db_constraint=False,
    )
    
    # 添加缺失的字段
    draft_person = models.CharField(max_length=50, verbose_name="拟稿人", help_text="负责拟稿的律师", null=True, blank=True)
    defendant_name = models.CharField(max_length=200, verbose_name="被告名称", help_text="被告名称", null=True, blank=True)
    defendant_credit_code = models.CharField(max_length=100, verbose_name="被告统一社会信用代码", help_text="被告统一社会信用代码", null=True, blank=True)
    defendant_address = models.CharField(max_length=500, verbose_name="被告地址", help_text="被告地址", null=True, blank=True)
    defendant_legal_representative = models.CharField(max_length=100, verbose_name="被告法定代表人", help_text="被告法定代表人", null=True, blank=True)
    plaintiff_name = models.CharField(max_length=200, verbose_name="原告名称", help_text="原告名称", null=True, blank=True)
    plaintiff_credit_code = models.CharField(max_length=100, verbose_name="原告统一社会信用代码", help_text="原告统一社会信用代码", null=True, blank=True)
    plaintiff_address = models.CharField(max_length=500, verbose_name="原告地址", help_text="原告地址", null=True, blank=True)
    plaintiff_legal_representative = models.CharField(max_length=100, verbose_name="原告法定代表人", help_text="原告法定代表人", null=True, blank=True)
    contract_amount = models.DecimalField(max_digits=20, decimal_places=2, verbose_name="合同金额", help_text="合同金额", null=True, blank=True)
    lawyer_fee = models.DecimalField(max_digits=20, decimal_places=2, verbose_name="律师费", help_text="律师费", null=True, blank=True)
    litigation_request = models.TextField(verbose_name="诉讼请求", help_text="诉讼请求", null=True, blank=True)
    facts_and_reasons = models.TextField(verbose_name="事实与理由", help_text="事实与理由", null=True, blank=True)
    jurisdiction = models.CharField(max_length=200, verbose_name="管辖法院", help_text="管辖法院", null=True, blank=True)
    petitioner = models.CharField(max_length=100, verbose_name="申请人", help_text="申请人", null=True, blank=True)
    filing_date = models.DateField(verbose_name="立案日期", help_text="立案日期", null=True, blank=True)

    class Meta:
        db_table = "case_management"
        verbose_name = "案例管理"
        verbose_name_plural = "案例管理"
        ordering = ["-create_datetime"]


class CaseHandler(CoreModel):
    case = models.ForeignKey(
        CaseManagement,
        on_delete=models.CASCADE,
        related_name="case_handler_links",
        db_constraint=False,
        verbose_name="案件",
    )
    user = models.ForeignKey(
        Users,
        on_delete=models.CASCADE,
        related_name="case_handler_links",
        db_constraint=False,
        verbose_name="经办人",
    )
    is_primary = models.BooleanField(default=False, verbose_name="是否主经办人")
    sort = models.IntegerField(default=0, verbose_name="排序")

    class Meta:
        db_table = "case_handler"
        verbose_name = "案件经办人"
        verbose_name_plural = verbose_name
        unique_together = ("case", "user")
        ordering = ("sort", "id")

    def __str__(self):
        return f"{self.case_id}-{self.user_id}"


class CaseFolder(CoreModel, SoftDeleteModel):
    """案件目录模型"""
    case = models.ForeignKey(
        CaseManagement, 
        on_delete=models.CASCADE, 
        related_name='folders',
        verbose_name="关联案件",
        help_text="关联案件"
    )
    parent = models.ForeignKey(
        'self', 
        null=True, 
        blank=True, 
        on_delete=models.CASCADE,
        related_name='children',
        verbose_name="父目录",
        help_text="父目录ID，NULL表示根目录"
    )
    folder_name = models.CharField(
        max_length=100, 
        verbose_name="目录名称",
        help_text="目录名称（中文显示名）"
    )
    folder_path = models.CharField(
        max_length=500, 
        verbose_name="完整路径",
        help_text="完整路径（英文），如：/case_documents"
    )
    folder_type = models.CharField(
        max_length=50, 
        default='custom',
        choices=[
            ('fixed', '固定目录'),
            ('custom', '自定义目录')
        ],
        verbose_name="目录类型",
        help_text="目录类型：fixed-固定目录, custom-自定义目录"
    )
    sort_order = models.IntegerField(
        default=0, 
        verbose_name="排序序号",
        help_text="排序序号"
    )
    
    class Meta:
        db_table = "case_folder"
        verbose_name = "案件目录"
        verbose_name_plural = "案件目录"
        ordering = ['sort_order', 'id']
        unique_together = [['case', 'folder_path', 'is_deleted']]
        indexes = [
            models.Index(fields=['case', 'folder_path']),
            models.Index(fields=['parent']),
        ]
    
    def __str__(self):
        return f"{self.folder_name} ({self.folder_path})"


class CaseDocument(CoreModel, SoftDeleteModel):
    """案例文档模型（扩展版）"""
    case = models.ForeignKey(
        CaseManagement, 
        on_delete=models.CASCADE,
        related_name='documents',
        verbose_name="关联案例",
        help_text="关联案例"
    )
    folder = models.ForeignKey(
        CaseFolder,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name="所属目录",
        help_text="所属目录ID"
    )
    folder_path = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name="目录路径",
        help_text="目录路径（冗余字段，便于查询）"
    )
    
    # 文档信息
    document_name = models.CharField(
        max_length=200, 
        verbose_name="文档显示名称",
        help_text="文档显示名称"
    )
    document_type = models.CharField(
        max_length=50,
        choices=[
            ('template', '模板生成'),
            ('upload', '用户上传'),
            ('ai', 'AI生成'),
            ('parse', '解析源文件'),
        ],
        verbose_name="文档类型",
        help_text="文档类型：template-模板生成, upload-上传, ai-AI生成, parse-解析源文件"
    )
    document_content = models.TextField(
        verbose_name="文档内容", 
        null=True, 
        blank=True,
        help_text="文档内容"
    )
    
    # 文件信息
    file_name = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name="实际文件名",
        help_text="实际文件名（含扩展名）"
    )
    file_path = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name="文件存储相对路径",
        help_text="文件存储相对路径"
    )
    file_size = models.BigIntegerField(
        null=True, 
        blank=True,
        verbose_name="文件大小(字节)",
        help_text="文件大小（字节）"
    )
    file_ext = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name="文件扩展名",
        help_text="文件扩展名（如：.docx, .pdf）"
    )
    mime_type = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="MIME类型",
        help_text="MIME类型"
    )
    
    @property
    def file_url(self):
        """
        获取文件的访问 URL
        
        Returns:
            str: 文件的访问 URL，如 "/media/cases/50/case_documents/续封申请书.docx"
        """
        from django.conf import settings
        
        if not self.file_path:
            return None
        
        # 如果是相对路径，拼接 MEDIA_URL
        if not os.path.isabs(self.file_path):
            return f"{settings.MEDIA_URL}{self.file_path}".replace('\\', '/')
        
        # 如果是绝对路径（兼容旧数据），提取相对部分
        if self.file_path.startswith(settings.MEDIA_ROOT):
            relative_path = os.path.relpath(self.file_path, settings.MEDIA_ROOT)
            return f"{settings.MEDIA_URL}{relative_path}".replace('\\', '/')
        
        # 兼容旧的 media/... 格式
        if self.file_path.startswith('media/') or self.file_path.startswith('media\\'):
            relative_path = self.file_path[6:]  # 去掉 'media/' 或 'media\'
            return f"{settings.MEDIA_URL}{relative_path}".replace('\\', '/')
        
        # 默认返回文件路径
        return f"{settings.MEDIA_URL}{self.file_path}".replace('\\', '/')
    
    @property
    def full_file_path(self):
        """
        获取文件的完整物理路径
        
        Returns:
            str: 文件的完整物理路径
        """
        from django.conf import settings
        import os
        
        if not self.file_path:
            return None
        
        # 如果是绝对路径，直接返回
        if os.path.isabs(self.file_path):
            return self.file_path
        
        # 如果是相对路径，拼接 MEDIA_ROOT
        return os.path.join(settings.MEDIA_ROOT, self.file_path)
    
    # 模板相关
    template = models.ForeignKey(
        'DocumentTemplate',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name="关联模板",
        help_text="关联的模板ID（如果是模板生成）"
    )
    version = models.IntegerField(
        default=1,
        verbose_name="版本号",
        help_text="版本号（同一文档的不同版本）"
    )
    
    # 存储信息
    storage_type = models.CharField(
        max_length=20,
        default='local',
        choices=[
            ('local', '本地存储'),
            ('oss', '阿里云OSS'),
            ('minio', 'MinIO'),
        ],
        verbose_name="存储类型",
        help_text="存储类型：local-本地, oss-阿里云, minio等"
    )
    storage_url = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name="存储完整URL",
        help_text="存储完整URL（如果使用云存储）"
    )
    
    # 兼容旧字段（保留）
    document_path = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name="文档路径(旧)",
        help_text="文档路径(旧)"
    )
    document_size = models.IntegerField(
        default=0,
        verbose_name="文档大小(旧)",
        help_text="文档大小(旧)"
    )
    generation_method = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="生成方式",
        help_text="生成方式"
    )
    template_used = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name="使用的模板",
        help_text="使用的模板"
    )
    
    # ✅ 新增字段
    print_count = models.IntegerField(
        default=1,
        verbose_name="默认打印份数",
        help_text="该文档的默认打印份数（从模板继承）"
    )
    is_selected = models.BooleanField(
        default=False,
        verbose_name="是否选中",
        help_text="文档在批量打印中是否被选中"
    )
    sort_order = models.IntegerField(
        default=0,
        verbose_name="排序序号",
        help_text="排序序号，数值越小越靠前（从模板继承）",
        db_index=True
    )
    
    # WPS相关字段
    wps_file_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="WPS文件ID",
        help_text="WPS文件ID"
    )
    wps_edit_token = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name="WPS编辑令牌",
        help_text="WPS编辑令牌"
    )
    wps_edit_url = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name="WPS编辑URL",
        help_text="WPS编辑URL"
    )
    last_edit_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="最后编辑时间",
        help_text="最后编辑时间"
    )
    last_editor_id = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name="最后编辑人ID",
        help_text="最后编辑人ID"
    )
    wps_enabled = models.BooleanField(
        default=True,
        verbose_name="是否启用WPS编辑",
        help_text="是否启用WPS编辑"
    )
    
    class Meta:
        db_table = "case_document"
        verbose_name = "案例文档"
        verbose_name_plural = "案例文档"
        ordering = ['-create_datetime']
        indexes = [
            models.Index(fields=['case', 'folder_path']),
            models.Index(fields=['template']),
            models.Index(fields=['document_type']),
        ]
    
    def __str__(self):
        return f"{self.document_name}{self.file_ext or ''}"


class DocumentTemplate(CoreModel, SoftDeleteModel):
    """文档模板模型"""
    template_name = models.CharField(max_length=200, verbose_name="模板名称", help_text="模板名称")
    template_type = models.CharField(max_length=50, verbose_name="模板类型", help_text="模板类型")
    template_content = models.TextField(verbose_name="模板内容", help_text="模板内容", default="")
    template_description = models.TextField(verbose_name="模板描述", help_text="模板描述", null=True, blank=True)
    is_active = models.BooleanField(default=True, verbose_name="是否启用", help_text="是否启用")
    
    # 文件相关字段
    file_path = models.CharField(max_length=500, verbose_name="文件路径", help_text="文件路径（相对于MEDIA_ROOT的相对路径）", null=True, blank=True)
    file_size = models.IntegerField(verbose_name="文件大小", help_text="文件大小(字节)", default=0)
    placeholder_info = models.JSONField(verbose_name="占位符信息", help_text="占位符信息", null=True, blank=True)
    
    # ✅ 新增字段
    sort_order = models.IntegerField(
        default=0, 
        verbose_name="排序序号", 
        help_text="排序序号，数值越小越靠前",
        db_index=True
    )
    print_count = models.IntegerField(
        default=1, 
        verbose_name="默认打印份数", 
        help_text="该文书默认需要打印的份数（如3份、5份等）"
    )
    
    @property
    def full_file_path(self):
        """
        获取文件的完整物理路径
        
        支持新旧两种格式：
        - 新格式：相对路径（相对于 MEDIA_ROOT），如 "case_templates/起诉状.docx"
        - 旧格式：绝对路径（兼容旧数据）
        
        Returns:
            str: 文件的完整物理路径，如果文件不存在则返回 None
        """
        from django.conf import settings
        import os
        import logging
        import glob
        
        logger = logging.getLogger(__name__)
        
        if not self.file_path:
            logger.warning(f"[模板路径] 模板 {self.id} ({self.template_name}) 的 file_path 为空")
            return None
        
        logger.info(f"[模板路径] 模板 {self.id} ({self.template_name}) 的 file_path: {self.file_path}")
        
        # 新格式：相对路径（优先检查 media 目录）
        if not os.path.isabs(self.file_path):
            media_path = os.path.join(settings.MEDIA_ROOT, self.file_path)
            logger.info(f"[模板路径] 尝试路径1 (MEDIA_ROOT相对路径): {media_path}, 存在: {os.path.exists(media_path)}")
            if os.path.exists(media_path):
                return media_path
            
            # 尝试查找不带时间戳的文件名（如果原文件名包含时间戳）
            # 例如：财产保全申请书_1761181151.docx -> 财产保全申请书.docx
            base_name = os.path.basename(self.file_path)
            # 检查文件名是否包含下划线和数字后缀（可能是时间戳）
            if '_' in base_name:
                name_parts = base_name.rsplit('_', 1)
                if len(name_parts) == 2:
                    # 检查第二部分是否是纯数字（可能是时间戳）
                    potential_timestamp = name_parts[1].split('.')[0]  # 去除扩展名
                    if potential_timestamp.isdigit() and len(potential_timestamp) >= 10:  # 时间戳通常是10位或更多
                        # 尝试查找不带时间戳的版本
                        file_ext = os.path.splitext(base_name)[1]
                        simple_name = name_parts[0] + file_ext
                        simple_path = os.path.join(settings.MEDIA_ROOT, os.path.dirname(self.file_path), simple_name)
                        logger.info(f"[模板路径] 尝试路径1.1 (去除时间戳): {simple_path}, 存在: {os.path.exists(simple_path)}")
                        if os.path.exists(simple_path):
                            return simple_path
            
            # 尝试在 case_templates 目录下查找匹配的文件（文件名包含模板名称）
            if 'case_templates' in self.file_path:
                case_templates_dir = os.path.join(settings.MEDIA_ROOT, 'case_templates')
                if os.path.exists(case_templates_dir):
                    # 获取模板名称（去除扩展名）
                    template_base_name = os.path.splitext(self.template_name or base_name)[0]
                    # 如果模板名称包含时间戳，尝试去除时间戳后再匹配
                    if '_' in template_base_name:
                        name_parts = template_base_name.rsplit('_', 1)
                        if len(name_parts) == 2 and name_parts[1].isdigit() and len(name_parts[1]) >= 10:
                            template_base_name = name_parts[0]
                    
                    # 查找所有匹配的文件（支持多种扩展名）
                    patterns = [
                        os.path.join(case_templates_dir, f"{template_base_name}.docx"),
                        os.path.join(case_templates_dir, f"{template_base_name}*.docx"),
                        os.path.join(case_templates_dir, f"{template_base_name}.doc"),
                        os.path.join(case_templates_dir, f"{template_base_name}*.doc"),
                    ]
                    
                    for pattern in patterns:
                        matches = glob.glob(pattern)
                        if matches:
                            logger.info(f"[模板路径] 尝试路径1.2 (模糊匹配): 模式 {pattern} 找到 {len(matches)} 个匹配文件")
                            # 优先返回精确匹配的文件（不带时间戳的）
                            exact_matches = [m for m in matches if os.path.basename(m) == f"{template_base_name}.docx"]
                            if exact_matches:
                                return exact_matches[0]
                            # 否则返回第一个匹配的文件
                            return matches[0]
        
        # 旧格式：绝对路径
        if os.path.isabs(self.file_path):
            logger.info(f"[模板路径] 尝试路径2 (绝对路径): {self.file_path}, 存在: {os.path.exists(self.file_path)}")
            if os.path.exists(self.file_path):
                return self.file_path
        
        # 兼容旧路径：templates/case_templates/
        old_path = os.path.join(settings.BASE_DIR, 'templates', 'case_templates', 
                                os.path.basename(self.file_path))
        logger.info(f"[模板路径] 尝试路径3 (旧路径): {old_path}, 存在: {os.path.exists(old_path)}")
        if os.path.exists(old_path):
            return old_path
        
        # 如果都不存在，返回预期的 media 路径（让调用方处理文件不存在的情况）
        if not os.path.isabs(self.file_path):
            expected_path = os.path.join(settings.MEDIA_ROOT, self.file_path)
            logger.warning(f"[模板路径] 所有路径都不存在，返回预期路径: {expected_path}")
            return expected_path
        
        logger.warning(f"[模板路径] 所有路径都不存在，返回原始路径: {self.file_path}")
        return self.file_path
    
    @property
    def file_url(self):
        """
        获取文件的访问 URL
        
        Returns:
            str: 文件的访问 URL，如 "/media/case_templates/起诉状.docx"
        """
        from django.conf import settings
        import os
        
        if not self.file_path:
            return None
        
        # 如果是相对路径，直接拼接 MEDIA_URL
        if not os.path.isabs(self.file_path):
            return f"{settings.MEDIA_URL}{self.file_path}".replace('\\', '/')
        
        # 兼容旧数据：返回文件名
        filename = os.path.basename(self.file_path)
        return f"{settings.MEDIA_URL}case_templates/{filename}".replace('\\', '/')
    
    class Meta:
        db_table = "document_template"
        verbose_name = "文档模板"
        verbose_name_plural = "文档模板"
        ordering = ['sort_order', 'id']  # ✅ 默认按排序序号排序


class SearchSuggestion(CoreModel):
    """搜索建议模型"""
    question = models.CharField(max_length=500, verbose_name="常见问题", help_text="常见问题")
    category = models.CharField(max_length=100, verbose_name="问题分类", help_text="问题分类", default="general")
    keywords = models.CharField(max_length=200, verbose_name="关键词", help_text="关键词", null=True, blank=True)
    sort_order = models.IntegerField(default=0, verbose_name="排序", help_text="排序")
    is_active = models.BooleanField(default=True, verbose_name="是否启用", help_text="是否启用")
    
    class Meta:
        db_table = "search_suggestion"
        verbose_name = "搜索建议"
        verbose_name_plural = "搜索建议"
        ordering = ['sort_order', 'id']


class RegulationSearchHistory(CoreModel):
    """法规搜索历史模型"""
    user_id = models.IntegerField(verbose_name="用户ID", help_text="用户ID", null=True, blank=True)
    search_query = models.TextField(verbose_name="搜索关键词", help_text="搜索关键词")
    search_filters = models.JSONField(verbose_name="搜索筛选条件", help_text="搜索筛选条件", null=True, blank=True)
    search_results_count = models.IntegerField(verbose_name="搜索结果数量", help_text="搜索结果数量", default=0)
    search_time = models.FloatField(verbose_name="搜索耗时(秒)", help_text="搜索耗时(秒)", default=0.0)
    ip_address = models.GenericIPAddressField(verbose_name="IP地址", help_text="IP地址", null=True, blank=True)
    user_agent = models.TextField(verbose_name="用户代理", help_text="用户代理", null=True, blank=True)
    search_type = models.CharField(max_length=50, verbose_name="搜索类型", help_text="搜索类型", default="regulation")
    
    class Meta:
        db_table = "regulation_search_history"
        verbose_name = "法规搜索历史"
        verbose_name_plural = "法规搜索历史"
        ordering = ['-create_datetime']


class RegulationSearchResult(CoreModel):
    """法规搜索结果模型"""
    search_history = models.ForeignKey(RegulationSearchHistory, on_delete=models.CASCADE, verbose_name="搜索历史", help_text="关联的搜索历史")
    title = models.CharField(max_length=500, verbose_name="法规标题", help_text="法规标题")
    content = models.TextField(verbose_name="法规内容", help_text="法规内容")
    article_number = models.CharField(max_length=100, verbose_name="条文编号", help_text="条文编号", null=True, blank=True)
    law_type = models.CharField(max_length=100, verbose_name="法规类型", help_text="法规类型", null=True, blank=True)
    effective_date = models.CharField(max_length=50, verbose_name="生效日期", help_text="生效日期", null=True, blank=True)
    department = models.CharField(max_length=200, verbose_name="发布部门", help_text="发布部门", null=True, blank=True)
    relevance_score = models.FloatField(verbose_name="相关度分数", help_text="相关度分数", default=0.0)
    sort_order = models.IntegerField(verbose_name="排序顺序", help_text="排序顺序", default=0)
    
    class Meta:
        db_table = "regulation_search_result"
        verbose_name = "法规搜索结果"
        verbose_name_plural = "法规搜索结果"
        ordering = ['sort_order', 'relevance_score']


class RegulationConversation(CoreModel):
    """法规检索对话会话模型"""
    user_id = models.IntegerField(verbose_name="用户ID", help_text="用户ID", null=True, blank=True, default=0)
    title = models.CharField(max_length=200, verbose_name="对话标题", help_text="对话标题", default="新对话")
    message_count = models.IntegerField(verbose_name="消息数量", help_text="消息数量", default=0)
    last_message_time = models.DateTimeField(verbose_name="最后消息时间", help_text="最后消息时间", null=True, blank=True)
    is_pinned = models.BooleanField(verbose_name="是否置顶", help_text="是否置顶", default=False)
    ip_address = models.GenericIPAddressField(verbose_name="IP地址", help_text="IP地址", null=True, blank=True)
    category = models.CharField(max_length=50, verbose_name="问题分类", help_text="问题分类(question/similar-case/regulation)", default="question", null=True, blank=True)
    
    class Meta:
        db_table = "regulation_conversation"
        verbose_name = "法规检索对话"
        verbose_name_plural = "法规检索对话"
        ordering = ['-is_pinned', '-last_message_time', '-create_datetime']
    
    def __str__(self):
        return f"{self.title} ({self.message_count}条消息)"


class RegulationMessage(CoreModel):
    """法规检索对话消息模型"""
    conversation = models.ForeignKey(
        RegulationConversation, 
        on_delete=models.CASCADE, 
        related_name='messages',
        verbose_name="对话会话", 
        help_text="所属对话会话"
    )
    role = models.CharField(
        max_length=20, 
        verbose_name="角色", 
        help_text="消息角色(user/assistant)",
        choices=[('user', '用户'), ('assistant', 'AI助手')]
    )
    content = models.TextField(verbose_name="消息内容", help_text="消息内容")
    query = models.TextField(verbose_name="查询内容", help_text="用户查询内容", null=True, blank=True)
    filters = models.JSONField(verbose_name="筛选条件", help_text="筛选条件", null=True, blank=True)
    response_time = models.FloatField(verbose_name="响应时间(秒)", help_text="AI响应时间", null=True, blank=True)
    related_regulations = models.JSONField(verbose_name="相关法规", help_text="相关法规列表", null=True, blank=True)
    
    class Meta:
        db_table = "regulation_message"
        verbose_name = "法规检索消息"
        verbose_name_plural = "法规检索消息"
        ordering = ['create_datetime']
    
    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."


class WPSEditRecord(CoreModel):
    """WPS编辑记录模型"""
    document = models.ForeignKey(
        CaseDocument,
        on_delete=models.CASCADE,
        related_name='wps_edit_records',
        verbose_name="文档",
        help_text="关联文档"
    )
    user_id = models.BigIntegerField(
        verbose_name="用户ID",
        help_text="用户ID"
    )
    user_name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="用户名",
        help_text="用户名"
    )
    file_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="WPS文件ID",
        help_text="WPS文件ID"
    )
    edit_token = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name="编辑令牌",
        help_text="编辑令牌"
    )
    edit_mode = models.CharField(
        max_length=20,
        default='edit',
        choices=[
            ('view', '预览'),
            ('edit', '编辑')
        ],
        verbose_name="编辑模式",
        help_text="编辑模式：view-预览, edit-编辑"
    )
    start_time = models.DateTimeField(
        auto_now_add=True,
        verbose_name="开始编辑时间",
        help_text="开始编辑时间"
    )
    end_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="结束编辑时间",
        help_text="结束编辑时间"
    )
    save_count = models.IntegerField(
        default=0,
        verbose_name="保存次数",
        help_text="保存次数"
    )
    status = models.CharField(
        max_length=20,
        default='editing',
        choices=[
            ('editing', '编辑中'),
            ('completed', '已完成'),
            ('cancelled', '已取消')
        ],
        verbose_name="状态",
        help_text="状态：editing-编辑中, completed-已完成, cancelled-已取消"
    )
    ip_address = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="IP地址",
        help_text="IP地址"
    )
    user_agent = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name="用户代理",
        help_text="用户代理"
    )
    
    class Meta:
        db_table = "wps_edit_record"
        verbose_name = "WPS编辑记录"
        verbose_name_plural = "WPS编辑记录"
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['document', 'status']),
            models.Index(fields=['user_id']),
            models.Index(fields=['start_time']),
        ]
    
    def __str__(self):
        return f"{self.document.document_name} - {self.user_name or self.user_id} - {self.status}"


class WPSCallbackLog(CoreModel):
    """WPS回调日志模型"""
    document = models.ForeignKey(
        CaseDocument,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='wps_callback_logs',
        verbose_name="文档",
        help_text="关联文档"
    )
    file_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="WPS文件ID",
        help_text="WPS文件ID"
    )
    event_type = models.CharField(
        max_length=50,
        verbose_name="事件类型",
        help_text="事件类型"
    )
    event_data = models.JSONField(
        null=True,
        blank=True,
        verbose_name="事件数据",
        help_text="事件数据"
    )
    callback_data = models.TextField(
        null=True,
        blank=True,
        verbose_name="回调原始数据",
        help_text="回调原始数据"
    )
    status = models.CharField(
        max_length=20,
        default='success',
        choices=[
            ('success', '成功'),
            ('failed', '失败')
        ],
        verbose_name="处理状态",
        help_text="处理状态：success-成功, failed-失败"
    )
    error_message = models.TextField(
        null=True,
        blank=True,
        verbose_name="错误信息",
        help_text="错误信息"
    )
    
    class Meta:
        db_table = "wps_callback_log"
        verbose_name = "WPS回调日志"
        verbose_name_plural = "WPS回调日志"
        ordering = ['-create_datetime']
        indexes = [
            models.Index(fields=['document']),
            models.Index(fields=['event_type']),
            models.Index(fields=['create_datetime']),
        ]
    
    def __str__(self):
        return f"{self.event_type} - {self.status} - {self.create_datetime}"
