"""
组织架构模型 - 总部/分所/团队
与 Dept（部门）分离，避免混淆
"""
from django.db import models
from dvadmin.utils.models import CoreModel


class Headquarters(CoreModel):
    """总部表"""
    
    name = models.CharField(
        max_length=100,
        verbose_name="总部名称",
        help_text="总部名称"
    )
    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="总部编码",
        help_text="总部编码"
    )
    address = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name="地址",
        help_text="地址"
    )
    contact_person = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="负责人",
        help_text="负责人"
    )
    contact_phone = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="联系电话",
        help_text="联系电话"
    )
    status = models.BooleanField(
        default=True,
        verbose_name="状态",
        help_text="状态：True-启用，False-停用"
    )
    sort = models.IntegerField(
        default=0,
        verbose_name="排序",
        help_text="排序"
    )
    
    class Meta:
        db_table = "organization_headquarters"
        verbose_name = "总部"
        verbose_name_plural = "总部"
        ordering = ['sort', 'id']
    
    def __str__(self):
        return self.name


class Branch(CoreModel):
    """分所表"""
    
    headquarters = models.ForeignKey(
        to=Headquarters,
        on_delete=models.CASCADE,
        related_name="branches",
        verbose_name="所属总部",
        help_text="所属总部",
        db_constraint=False
    )
    name = models.CharField(
        max_length=100,
        verbose_name="分所名称",
        help_text="分所名称"
    )
    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="分所编码",
        help_text="分所编码"
    )
    address = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name="地址",
        help_text="地址"
    )
    contact_person = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="负责人",
        help_text="负责人"
    )
    contact_phone = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="联系电话",
        help_text="联系电话"
    )
    status = models.BooleanField(
        default=True,
        verbose_name="状态",
        help_text="状态：True-启用，False-停用"
    )
    sort = models.IntegerField(
        default=0,
        verbose_name="排序",
        help_text="排序"
    )
    
    class Meta:
        db_table = "organization_branch"
        verbose_name = "分所"
        verbose_name_plural = "分所"
        ordering = ['sort', 'id']
        indexes = [
            models.Index(fields=['headquarters', 'status']),
        ]
    
    def __str__(self):
        return f"{self.headquarters.name} - {self.name}"


class Team(CoreModel):
    """团队表"""
    
    branch = models.ForeignKey(
        to=Branch,
        on_delete=models.CASCADE,
        related_name="teams",
        verbose_name="所属分所",
        help_text="所属分所",
        db_constraint=False
    )
    name = models.CharField(
        max_length=100,
        verbose_name="团队名称",
        help_text="团队名称"
    )
    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="团队编码",
        help_text="团队编码"
    )
    leader = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="团队负责人",
        help_text="团队负责人"
    )
    contact_phone = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="联系电话",
        help_text="联系电话"
    )
    status = models.BooleanField(
        default=True,
        verbose_name="状态",
        help_text="状态：True-启用，False-停用"
    )
    sort = models.IntegerField(
        default=0,
        verbose_name="排序",
        help_text="排序"
    )
    
    class Meta:
        db_table = "organization_team"
        verbose_name = "团队"
        verbose_name_plural = "团队"
        ordering = ['sort', 'id']
        indexes = [
            models.Index(fields=['branch', 'status']),
        ]
    
    def __str__(self):
        return f"{self.branch.name} - {self.name}"
    
    @property
    def headquarters(self):
        """获取所属总部"""
        return self.branch.headquarters
    
    @property
    def headquarters_id(self):
        """获取总部ID"""
        return self.branch.headquarters_id
