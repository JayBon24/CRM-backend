# 腾讯云SMS配置指南

## 📱 配置步骤

### 1. 注册腾讯云账号
访问：https://cloud.tencent.com/

### 2. 开通短信服务
1. 登录腾讯云控制台
2. 搜索"短信"或访问：https://console.cloud.tencent.com/smsv2
3. 点击"开通短信服务"

### 3. 获取API密钥

#### 3.1 进入访问管理
- 控制台右上角 → 用户名 → 访问管理
- 或直接访问：https://console.cloud.tencent.com/cam/capi

#### 3.2 创建密钥
- 点击"新建密钥"
- 记录 `SecretId` 和 `SecretKey`（只显示一次，请妥善保管）

### 4. 创建短信应用

#### 4.1 进入应用管理
- 短信控制台 → 应用管理 → 创建应用
- 或访问：https://console.cloud.tencent.com/smsv2/app-manage

#### 4.2 创建应用
- 应用名称：如"法律智能系统"
- 应用简介：描述应用用途
- 创建后记录 `SDKAppID`

### 5. 创建签名

#### 5.1 进入签名管理
- 短信控制台 → 国内短信 → 签名管理
- 或访问：https://console.cloud.tencent.com/smsv2/csms-sign

#### 5.2 创建签名
- 签名类型：选择"网站"或"App"
- 签名用途：选择"自用"
- 签名内容：如"法律智能系统"（2-12个字）
- 上传证明材料（营业执照或网站备案截图）
- 提交审核（通常1-2小时）

### 6. 创建短信模板

#### 6.1 进入正文模板管理
- 短信控制台 → 国内短信 → 正文模板管理
- 或访问：https://console.cloud.tencent.com/smsv2/csms-template

#### 6.2 创建模板
**日程提醒模板示例：**
- 模板名称：日程提醒
- 短信类型：通知类
- 短信内容：
  ```
  【法律智能系统】您有一个日程提醒：{1}，时间：{2}，请及时处理。
  ```
- 提交审核（通常1-2小时）
- 审核通过后记录 `模板ID`

**其他常用模板：**

验证码模板：
```
【法律智能系统】您的验证码是：{1}，{2}分钟内有效，请勿泄露。
```

会议通知模板：
```
【法律智能系统】会议通知：{1}，时间：{2}，地点：{3}，请准时参加。
```

### 7. 配置项目

#### 7.1 安装SDK
```bash
pip install tencentcloud-sdk-python
```

#### 7.2 配置环境变量
在 `conf/env.py` 中配置：

```python
# 腾讯云SMS配置
TENCENT_SECRET_ID = 'your_tencent_secret_id'  # 替换为你的SecretId
TENCENT_SECRET_KEY = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'    # 替换为你的SecretKey
TENCENT_SMS_APP_ID = '1400xxxxxx'                          # 替换为你的SDKAppID
TENCENT_SMS_SIGN = '法律智能系统'                           # 替换为你的签名内容

# 短信模板ID
TENCENT_SMS_TEMPLATES = {
    'SCHEDULE_REMINDER': '123456',      # 日程提醒模板ID
    'VERIFICATION_CODE': '123457',      # 验证码模板ID
}
```

### 8. 测试发送

#### 8.1 使用测试脚本
```bash
python test_sms.py
```

#### 8.2 使用API接口
```bash
POST /api/customer/schedules/notification/sms/send/
{
  "phone": "13800138000",
  "template_code": "SCHEDULE_REMINDER",
  "params": {
    "title": "客户拜访",
    "time": "2025-12-26 15:00"
  }
}
```

## 💰 费用说明

### 免费额度
- 新用户赠送100条免费短信
- 每月赠送一定数量的免费短信（根据活动）

### 收费标准（国内短信）
- 验证码/通知类：0.045元/条
- 营销类：0.055元/条
- 按量计费，无最低消费

### 充值方式
- 短信控制台 → 套餐包管理 → 购买套餐包
- 建议：先购买小额套餐包测试

## 🔒 安全建议

### 1. 密钥安全
- ❌ 不要将密钥提交到Git仓库
- ✅ 使用环境变量或配置文件（加入.gitignore）
- ✅ 定期更换密钥

### 2. 访问控制
- 在腾讯云控制台设置IP白名单
- 限制API调用频率

### 3. 监控告警
- 设置短信发送量告警
- 监控异常调用

## 📝 模板参数说明

### 日程提醒模板
```python
params = {
    'title': '客户拜访',      # {1} 日程标题
    'time': '2025-12-26 15:00'  # {2} 日程时间
}
```

### 验证码模板
```python
params = {
    'code': '123456',    # {1} 验证码
    'minutes': '5'       # {2} 有效时间（分钟）
}
```

## 🐛 常见问题

### 1. 短信发送失败
**错误：InvalidParameterValue.IncorrectPhoneNumber**
- 原因：手机号格式错误
- 解决：确保手机号格式正确，国内手机号11位

**错误：FailedOperation.SignatureIncorrectOrUnapproved**
- 原因：签名未审核通过或签名内容错误
- 解决：检查签名审核状态，确保签名内容与配置一致

**错误：FailedOperation.TemplateIncorrectOrUnapproved**
- 原因：模板未审核通过或模板ID错误
- 解决：检查模板审核状态，确保模板ID正确

### 2. SDK导入失败
```bash
pip install --upgrade tencentcloud-sdk-python
```

### 3. 参数数量不匹配
- 确保传入的参数数量与模板中的变量数量一致
- 参数顺序要与模板中的{1}、{2}顺序对应

## 📚 参考文档

- 腾讯云短信官方文档：https://cloud.tencent.com/document/product/382
- Python SDK文档：https://cloud.tencent.com/document/sdk/Python
- API文档：https://cloud.tencent.com/document/product/382/52077

## 🆘 技术支持

如遇问题，可以：
1. 查看腾讯云控制台的发送记录和错误信息
2. 联系腾讯云技术支持
3. 查看项目日志文件
