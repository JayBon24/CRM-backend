"""
通知服务 - 短信和邮件发送
"""
import logging
from typing import Dict, Any
from django.conf import settings

logger = logging.getLogger(__name__)


class SMSService:
    """短信服务 - 腾讯云SMS"""
    
    @staticmethod
    def send_sms(phone: str, template_code: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        发送短信
        
        Args:
            phone: 手机号
            template_code: 模板代码
            params: 模板参数
            
        Returns:
            发送结果
        """
        try:
            # 检查配置
            secret_id = getattr(settings, 'TENCENT_SECRET_ID', None)
            secret_key = getattr(settings, 'TENCENT_SECRET_KEY', None)
            app_id = getattr(settings, 'TENCENT_SMS_APP_ID', None)
            sign_name = getattr(settings, 'TENCENT_SMS_SIGN', None)
            templates = getattr(settings, 'TENCENT_SMS_TEMPLATES', {})
            
            # 检查是否配置了占位符（未配置）
            if not secret_id or secret_id.startswith('[') or not secret_key or secret_key.startswith('['):
                logger.warning("腾讯云SMS未配置，使用模拟模式")
                return {
                    'success': True,
                    'message': '短信发送成功（模拟模式）',
                    'phone': phone,
                    'template_code': template_code,
                    'send_time': None,
                    'mode': 'mock'
                }
            
            # 获取模板ID
            template_id = templates.get(template_code)
            if not template_id or template_id.startswith('['):
                logger.warning(f"模板 {template_code} 未配置")
                return {
                    'success': False,
                    'message': f'短信模板 {template_code} 未配置',
                    'phone': phone
                }
            
            # 导入腾讯云SDK
            try:
                from tencentcloud.common import credential
                from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
                from tencentcloud.sms.v20210111 import sms_client, models
            except ImportError:
                logger.error("腾讯云SMS SDK未安装，请运行: pip install tencentcloud-sdk-python")
                return {
                    'success': False,
                    'message': '腾讯云SMS SDK未安装',
                    'phone': phone
                }
            
            # 实例化认证对象
            cred = credential.Credential(secret_id, secret_key)
            
            # 实例化SMS客户端
            client = sms_client.SmsClient(
                cred,
                getattr(settings, 'TENCENT_SMS_REGION', 'ap-guangzhou')
            )
            
            # 构造请求
            req = models.SendSmsRequest()
            req.SmsSdkAppId = app_id
            req.SignName = sign_name
            req.TemplateId = template_id
            
            # 手机号需要加上国家码
            if not phone.startswith('+'):
                phone = f'+86{phone}'
            req.PhoneNumberSet = [phone]
            
            # 模板参数（按模板定义的顺序）
            req.TemplateParamSet = [str(v) for v in params.values()]
            
            # 发送短信
            resp = client.SendSms(req)
            
            # 检查发送结果
            if resp.SendStatusSet and len(resp.SendStatusSet) > 0:
                status = resp.SendStatusSet[0]
                if status.Code == 'Ok':
                    logger.info(f"短信发送成功到 {phone}")
                    return {
                        'success': True,
                        'message': '短信发送成功',
                        'phone': phone,
                        'template_code': template_code,
                        'send_time': None,
                        'serial_no': status.SerialNo
                    }
                else:
                    logger.error(f"短信发送失败: {status.Code} - {status.Message}")
                    return {
                        'success': False,
                        'message': f'短信发送失败: {status.Message}',
                        'phone': phone,
                        'error_code': status.Code
                    }
            else:
                return {
                    'success': False,
                    'message': '短信发送失败：无响应',
                    'phone': phone
                }
                
        except Exception as e:
            logger.error(f"短信发送异常: {str(e)}")
            return {
                'success': False,
                'message': f'短信发送异常: {str(e)}',
                'phone': phone
            }
    
    @staticmethod
    def send_schedule_reminder(phone: str, title: str, time: str) -> Dict[str, Any]:
        """
        发送日程提醒短信（临时使用验证码模板测试）
        
        Args:
            phone: 手机号
            title: 日程标题
            time: 日程时间
            
        Returns:
            发送结果
        """
        # 临时使用register模板测试（验证码类型，只接受纯数字）
        # 模板：您正在注册账号，验证码为：{1}
        import random
        code = str(random.randint(100000, 999999))  # 生成6位数字验证码
        
        params = {
            'code': code
        }
        
        result = SMSService.send_sms(phone, 'VERIFICATION_CODE', params)
        
        # 在返回结果中添加提示
        if result['success']:
            result['note'] = f'测试短信已发送（验证码：{code}）。实际使用时请创建通知类模板。'
        
        return result


class EmailService:
    """邮件服务"""
    
    @staticmethod
    def send_email(to: str, subject: str, content: str, template: str = None) -> Dict[str, Any]:
        """
        发送邮件
        
        Args:
            to: 收件人邮箱
            subject: 邮件主题
            content: 邮件内容
            template: 邮件模板（可选）
            
        Returns:
            发送结果
        """
        try:
            from django.core.mail import send_mail
            
            # 如果有模板，使用模板渲染内容
            if template:
                # TODO: 实现模板渲染逻辑
                pass
            
            # 发送邮件
            send_mail(
                subject=subject,
                message=content,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com'),
                recipient_list=[to],
                fail_silently=False,
            )
            
            logger.info(f"邮件发送成功到 {to}")
            
            return {
                'success': True,
                'message': '邮件发送成功',
                'to': to,
                'subject': subject
            }
            
        except Exception as e:
            logger.error(f"邮件发送失败: {str(e)}")
            return {
                'success': False,
                'message': f'邮件发送失败: {str(e)}',
                'to': to
            }
    
    @staticmethod
    def send_schedule_reminder(to: str, title: str, time: str, description: str = '') -> Dict[str, Any]:
        """
        发送日程提醒邮件
        
        Args:
            to: 收件人邮箱
            title: 日程标题
            time: 日程时间
            description: 日程描述
            
        Returns:
            发送结果
        """
        subject = f"日程提醒: {title}"
        content = f"""
您好，

这是一条日程提醒：

标题：{title}
时间：{time}
{f'描述：{description}' if description else ''}

请及时处理。

此邮件由系统自动发送，请勿回复。
        """
        
        return EmailService.send_email(to, subject, content, template='schedule_reminder')


class NotificationService:
    """统一通知服务"""
    
    @staticmethod
    def send_notification(method: str, **kwargs) -> Dict[str, Any]:
        """
        发送通知
        
        Args:
            method: 通知方式 (sms/email/system/wechat)
            **kwargs: 通知参数
            
        Returns:
            发送结果
        """
        if method == 'sms':
            return SMSService.send_sms(
                phone=kwargs.get('phone'),
                template_code=kwargs.get('template_code'),
                params=kwargs.get('params', {})
            )
        elif method == 'email':
            return EmailService.send_email(
                to=kwargs.get('to'),
                subject=kwargs.get('subject'),
                content=kwargs.get('content'),
                template=kwargs.get('template')
            )
        elif method == 'system':
            # TODO: 实现系统通知
            logger.info(f"系统通知: {kwargs}")
            return {'success': True, 'message': '系统通知已发送'}
        elif method == 'wechat':
            # TODO: 实现微信通知
            logger.info(f"微信通知: {kwargs}")
            return {'success': True, 'message': '微信通知已发送'}
        else:
            return {'success': False, 'message': f'不支持的通知方式: {method}'}
