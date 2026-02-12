from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from dvadmin.system.models import Users, LoginLog
import hashlib


class MiniappLoginTestCase(APITestCase):
    """小程序登录接口测试"""
    
    def setUp(self):
        """测试前准备：创建测试用户"""
        self.client = APIClient()
        self.login_url = '/api/miniapp/login/'
        
        # 设置默认的 HTTP_USER_AGENT，避免测试报错
        self.client.defaults['HTTP_USER_AGENT'] = 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) MiniApp Test'
        
        # 创建测试用户（密码会自动MD5加密）
        self.test_user = Users.objects.create(
            username='testuser',
            mobile='13800138000',
            email='test@example.com',
            name='测试用户',
            is_active=True,
            user_type=1  # 前台用户
        )
        # 设置密码（会自动MD5加密）
        self.test_user.set_password('123456')
        self.test_user.save()
        
        # 创建被锁定的用户
        self.locked_user = Users.objects.create(
            username='lockeduser',
            mobile='13800138001',
            name='锁定用户',
            is_active=False  # 账号被锁定
        )
        self.locked_user.set_password('123456')
        self.locked_user.save()
    
    def test_login_with_username_success(self):
        """测试用户名登录成功"""
        data = {
            'username': 'testuser',
            'password': hashlib.md5('123456'.encode()).hexdigest()
        }
        response = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 2000)
        self.assertIn('access', response.data['data'])
        self.assertIn('refresh', response.data['data'])
        self.assertEqual(response.data['data']['username'], 'testuser')
        
        # 验证登录日志
        login_log = LoginLog.objects.filter(username='testuser').first()
        self.assertIsNotNone(login_log)
        self.assertEqual(login_log.login_type, 3)  # 小程序登录
    
    def test_login_with_mobile_success(self):
        """测试手机号登录成功"""
        data = {
            'username': '13800138000',  # 使用手机号
            'password': hashlib.md5('123456'.encode()).hexdigest()
        }
        response = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 2000)
        self.assertEqual(response.data['data']['username'], 'testuser')
    
    def test_login_with_email_not_supported(self):
        """测试邮箱登录不支持（小程序专用）"""
        data = {
            'username': 'test@example.com',  # 使用邮箱
            'password': hashlib.md5('123456'.encode()).hexdigest()
        }
        response = self.client.post(self.login_url, data, format='json')
        
        # 小程序登录不支持邮箱
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('账号不存在', response.data['msg'])
    
    def test_login_with_wrong_password(self):
        """测试密码错误"""
        data = {
            'username': 'testuser',
            'password': hashlib.md5('wrongpassword'.encode()).hexdigest()
        }
        response = self.client.post(self.login_url, data, format='json')
        
        # Django REST framework JWT 返回 200 但 code 不是 2000
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.data.get('code'), 2000)
        self.assertIn('账号/密码错误', str(response.data.get('msg', '')))
    
    def test_login_with_nonexistent_user(self):
        """测试用户不存在"""
        data = {
            'username': 'nonexistent',
            'password': hashlib.md5('123456'.encode()).hexdigest()
        }
        response = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('账号不存在', response.data['msg'])
    
    def test_login_with_locked_account(self):
        """测试账号被锁定"""
        data = {
            'username': 'lockeduser',
            'password': hashlib.md5('123456'.encode()).hexdigest()
        }
        response = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('账号已被锁定', response.data['msg'])
    
    def test_login_without_username(self):
        """测试缺少用户名参数"""
        data = {
            'password': hashlib.md5('123456'.encode()).hexdigest()
        }
        response = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_login_without_password(self):
        """测试缺少密码参数"""
        data = {
            'username': 'testuser'
        }
        response = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_login_error_count_increment(self):
        """测试登录失败次数累加"""
        data = {
            'username': 'testuser',
            'password': hashlib.md5('wrongpassword'.encode()).hexdigest()
        }
        
        # 第一次失败
        response = self.client.post(self.login_url, data, format='json')
        self.test_user.refresh_from_db()
        self.assertEqual(self.test_user.login_error_count, 1)
        
        # 第二次失败
        response = self.client.post(self.login_url, data, format='json')
        self.test_user.refresh_from_db()
        self.assertEqual(self.test_user.login_error_count, 2)
    
    def test_login_error_count_reset_on_success(self):
        """测试登录成功后错误次数重置"""
        # 先设置错误次数
        self.test_user.login_error_count = 3
        self.test_user.save()
        
        # 成功登录
        data = {
            'username': 'testuser',
            'password': hashlib.md5('123456'.encode()).hexdigest()
        }
        response = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.test_user.refresh_from_db()
        self.assertEqual(self.test_user.login_error_count, 0)
    
    def test_login_lock_after_5_failures(self):
        """测试5次失败后账号被锁定"""
        data = {
            'username': 'testuser',
            'password': hashlib.md5('wrongpassword'.encode()).hexdigest()
        }
        
        # 连续失败5次
        for i in range(5):
            response = self.client.post(self.login_url, data, format='json')
        
        # 验证账号被锁定
        self.test_user.refresh_from_db()
        self.assertFalse(self.test_user.is_active)
        self.assertIn('账号已被锁定', response.data['msg'])
    
    def test_response_data_structure(self):
        """测试返回数据结构"""
        data = {
            'username': 'testuser',
            'password': hashlib.md5('123456'.encode()).hexdigest()
        }
        response = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.data['data']
        
        # 验证必要字段存在
        self.assertIn('access', response_data)
        self.assertIn('refresh', response_data)
        self.assertIn('username', response_data)
        self.assertIn('name', response_data)
        self.assertIn('userId', response_data)
        self.assertIn('user_type', response_data)
    
    def test_different_user_types_can_login(self):
        """测试不同用户类型都可以登录"""
        # 创建后台用户
        backend_user = Users.objects.create(
            username='backenduser',
            name='后台用户',
            is_active=True,
            user_type=0  # 后台用户
        )
        backend_user.set_password('123456')
        backend_user.save()
        
        data = {
            'username': 'backenduser',
            'password': hashlib.md5('123456'.encode()).hexdigest()
        }
        response = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['user_type'], 0)
    
    def tearDown(self):
        """测试后清理"""
        Users.objects.all().delete()
        LoginLog.objects.all().delete()


class BackendLoginNotAffectedTestCase(APITestCase):
    """验证后台登录不受影响的测试"""
    
    def setUp(self):
        """测试前准备"""
        self.client = APIClient()
        self.backend_login_url = '/admin-api/login/'
        self.frontend_login_url = '/api/login/'
        
        # 设置默认的 HTTP_USER_AGENT
        self.client.defaults['HTTP_USER_AGENT'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124'
        
        # 创建测试用户
        self.test_user = Users.objects.create(
            username='adminuser',
            name='管理员',
            is_active=True,
            user_type=0
        )
        self.test_user.set_password('admin123')
        self.test_user.save()
    
    def test_backend_login_still_works(self):
        """测试后台登录仍然正常工作"""
        data = {
            'username': 'adminuser',
            'password': hashlib.md5('admin123'.encode()).hexdigest()
        }
        response = self.client.post(self.backend_login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 2000)
        
        # 验证登录类型为普通登录
        login_log = LoginLog.objects.filter(username='adminuser').first()
        self.assertIsNotNone(login_log)
        self.assertEqual(login_log.login_type, 1)  # 普通登录
    
    def test_frontend_login_still_works(self):
        """测试前端登录仍然正常工作"""
        data = {
            'username': 'adminuser',
            'password': hashlib.md5('admin123'.encode()).hexdigest()
        }
        response = self.client.post(self.frontend_login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 2000)
        
        # 验证登录类型为普通登录
        login_log = LoginLog.objects.filter(username='adminuser').first()
        self.assertIsNotNone(login_log)
        self.assertEqual(login_log.login_type, 1)  # 普通登录
    
    def tearDown(self):
        """测试后清理"""
        Users.objects.all().delete()
        LoginLog.objects.all().delete()
