-- 修复MySQL字符集以支持emoji字符
-- 问题：content字段使用utf8字符集，不支持4字节UTF-8字符（如emoji：📦）
-- 解决：将表和字段的字符集改为utf8mb4

-- 修改 regulation_message 表
ALTER TABLE regulation_message CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 修改 regulation_conversation 表
ALTER TABLE regulation_conversation CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 验证字符集是否修改成功
SELECT 
    TABLE_NAME,
    TABLE_COLLATION
FROM 
    information_schema.TABLES
WHERE 
    TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME IN ('regulation_message', 'regulation_conversation');

-- 查看具体列的字符集
SELECT 
    TABLE_NAME,
    COLUMN_NAME,
    CHARACTER_SET_NAME,
    COLLATION_NAME
FROM 
    information_schema.COLUMNS
WHERE 
    TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME IN ('regulation_message', 'regulation_conversation')
    AND COLUMN_NAME IN ('content', 'title');

