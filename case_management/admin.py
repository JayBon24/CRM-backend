"""
案例管理后台管理
"""
from django.contrib import admin
from .models import CaseManagement, CaseDocument, DocumentTemplate


@admin.register(CaseManagement)
class CaseManagementAdmin(admin.ModelAdmin):
    """案例管理后台"""
    list_display = ['case_number', 'case_name', 'case_type', 'status', 'draft_person', 'created_at']
    list_filter = ['case_type', 'status', 'created_at']
    search_fields = ['case_number', 'case_name', 'defendant_name', 'plaintiff_name']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']


@admin.register(CaseDocument)
class CaseDocumentAdmin(admin.ModelAdmin):
    """案例文档后台"""
    list_display = ['document_name', 'case', 'document_type', 'generation_method', 'created_at']
    list_filter = ['document_type', 'generation_method', 'created_at']
    search_fields = ['document_name', 'case__case_number']
    readonly_fields = ['created_at']


@admin.register(DocumentTemplate)
class DocumentTemplateAdmin(admin.ModelAdmin):
    """文档模板后台"""
    list_display = ['template_name', 'template_type', 'is_active', 'created_at']
    list_filter = ['template_type', 'is_active', 'created_at']
    search_fields = ['template_name', 'description']
    readonly_fields = ['created_at', 'updated_at']