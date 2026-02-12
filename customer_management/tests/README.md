# 小程序接口单元测试说明

## 测试文件

- `test_miniapp_apis.py` - 小程序 Tab1 和 Tab5 接口的完整单元测试

## 运行测试

### 运行所有测试

```bash
cd lsl/lsl-backend
python manage.py test customer_management.tests.test_miniapp_apis
```

### 运行特定测试类

```bash
# 运行 Tab1「客户」模块测试
python manage.py test customer_management.tests.test_miniapp_apis.ClientAPITestCase

# 运行 Tab5「我的」模块测试
python manage.py test customer_management.tests.test_miniapp_apis.MineAPITestCase

# 运行审批流程测试
python manage.py test customer_management.tests.test_miniapp_apis.ApprovalFlowTestCase
```

### 运行特定测试方法

```bash
# 运行获取客户列表测试
python manage.py test customer_management.tests.test_miniapp_apis.ClientAPITestCase.test_get_client_list_success

# 运行权限测试
python manage.py test customer_management.tests.test_miniapp_apis.ClientAPITestCase.test_apply_client_permission_denied_hq
```

### 运行测试并显示详细输出

```bash
python manage.py test customer_management.tests.test_miniapp_apis --verbosity=2
```

## 测试覆盖范围

### Tab1「客户」模块（15个测试用例）

1. ✅ `test_get_client_list_success` - 获取客户列表成功
2. ✅ `test_get_client_list_with_filters` - 带筛选条件的列表查询
3. ✅ `test_get_client_list_data_scope_sales` - SALES角色数据范围
4. ✅ `test_get_client_list_data_scope_team` - TEAM角色数据范围
5. ✅ `test_get_client_list_data_scope_branch` - BRANCH角色数据范围
6. ✅ `test_get_client_list_data_scope_hq` - HQ角色数据范围
7. ✅ `test_get_client_list_unauthorized` - 未授权访问
8. ✅ `test_get_client_detail_success` - 获取客户详情成功
9. ✅ `test_get_client_detail_permission_denied` - 权限不足
10. ✅ `test_create_client_success` - 创建客户成功
11. ✅ `test_update_client_success` - 更新客户成功
12. ✅ `test_update_client_permission_denied` - 更新权限不足
13. ✅ `test_apply_client_success` - 申领客户成功
14. ✅ `test_apply_client_permission_denied_hq` - HQ角色不能申领
15. ✅ `test_apply_client_permission_denied_branch` - BRANCH角色不能申领
16. ✅ `test_apply_client_not_public_pool` - 只能申领公海客户
17. ✅ `test_assign_client_success` - 分配客户成功
18. ✅ `test_assign_client_permission_denied` - 分配权限不足
19. ✅ `test_assign_client_to_hq_denied` - 不能分配给HQ角色
20. ✅ `test_approve_client_apply_success` - 审批客户申领成功

### Tab5「我的」模块（12个测试用例）

1. ✅ `test_get_mine_profile_success` - 获取个人资料成功
2. ✅ `test_get_mine_profile_hq` - HQ角色个人资料
3. ✅ `test_update_mine_profile_success` - 更新个人资料成功
4. ✅ `test_submit_feedback_success` - 提交反馈成功
5. ✅ `test_get_feedback_list_success` - 获取反馈列表成功
6. ✅ `test_get_approval_list_success` - 获取审批任务列表成功
7. ✅ `test_get_approval_list_permission_denied` - 审批列表权限不足
8. ✅ `test_approve_task_success` - 审批任务成功
9. ✅ `test_approve_task_reject` - 审批任务驳回
10. ✅ `test_approve_task_reject_without_reason` - 驳回时未填写原因
11. ✅ `test_approve_task_permission_denied` - 审批权限不足
12. ✅ `test_get_reminder_preference_success` - 获取提醒偏好成功
13. ✅ `test_set_reminder_preference_success` - 设置提醒偏好成功
14. ✅ `test_set_reminder_preference_invalid_value` - 设置提醒偏好无效值

### 审批流程测试（1个测试用例）

1. ✅ `test_approval_chain_flow` - 审批链流转测试

## 测试数据准备

测试会在 `setUp` 方法中自动创建：

- **部门结构**：总所 → 北京分所 → 销售一组
- **测试用户**：
  - `hq_user` - 总所管理员（HQ角色）
  - `branch_user` - 分所管理员（BRANCH角色）
  - `team_user` - 团队管理员（TEAM角色）
  - `sales_user` - 销售员（SALES角色）
  - `sales_user2` - 销售员2（SALES角色）
- **测试客户**：
  - `public_pool_client` - 公海客户
  - `sales_client` - 销售员的客户
  - `sales_user2_client` - 销售员2的客户

## 注意事项

1. **测试数据库**：Django 会自动使用测试数据库，不会影响生产数据
2. **数据隔离**：每个测试方法运行前会重置数据库
3. **JWT Token**：测试中使用 `AccessToken.for_user()` 生成 Token，无需实际登录
4. **权限测试**：测试覆盖了所有角色的权限控制
5. **数据范围测试**：测试验证了不同角色的数据范围过滤

## 常见问题

### 测试失败：数据库连接错误

确保测试数据库配置正确，Django 会使用 `settings.DATABASES['default']` 配置。

### 测试失败：导入错误

确保所有依赖已安装：
```bash
pip install -r requirements.txt
```

### 测试失败：权限错误

检查测试用户的 `role_level` 是否正确设置。

## 测试输出示例

```
Creating test database for alias 'default'...
System check identified no issues (0 silenced).
.......................

Ran 27 tests in 2.345s

OK
Destroying test database for alias 'default'...
```
