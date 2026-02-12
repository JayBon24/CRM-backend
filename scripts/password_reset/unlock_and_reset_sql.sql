-- 解锁superadmin账号
UPDATE lsl_system_users 
SET is_active = 1, 
    login_error_count = 0
WHERE username = 'superadmin';

-- 查看当前状态
SELECT id, username, is_active, login_error_count, LEFT(password, 50) as password_preview
FROM lsl_system_users 
WHERE username = 'superadmin';


