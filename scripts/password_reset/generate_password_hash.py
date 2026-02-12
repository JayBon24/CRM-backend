# -*- coding: utf-8 -*-
"""
生成密码哈希（需要Django环境）
使用方法: 在有Django环境的地方运行此脚本，然后复制输出的哈希值
"""
import hashlib

# 模拟Django的PBKDF2密码生成
# 注意：这只是一个示例，实际需要使用Django的make_password

raw_password = 'admin123456'
md5_hash = hashlib.md5(raw_password.encode('utf-8')).hexdigest()

print("=" * 60)
print("密码哈希生成")
print("=" * 60)
print(f"原始密码: {raw_password}")
print(f"MD5哈希: {md5_hash}")
print("\n注意: PBKDF2哈希需要使用Django的make_password生成")
print("请在有Django环境的地方执行以下代码:")
print("""
from django.contrib.auth.hashers import make_password
import hashlib

raw_password = 'admin123456'
md5_hash = hashlib.md5(raw_password.encode('utf-8')).hexdigest()
pbkdf2_hash = make_password(md5_hash)
print('PBKDF2哈希:', pbkdf2_hash)
""")


