-- ============================================
-- 更新案件关联关系 SQL 脚本
-- 说明：为现有案件数据补齐 customer_id, owner_user_id, contract_id 关联
-- 为现有合同数据补齐 case_id 关联
-- ============================================

-- 注意：此脚本仅供参考，实际执行时建议使用 Python 管理命令：
-- python manage.py update_case_relations

-- 1. 更新案件关联客户（示例：为前10个案件关联客户）
-- 优先关联状态为 CASE/PAYMENT/WON 的客户
UPDATE case_management cm
INNER JOIN (
    SELECT 
        cm.id as case_id,
        c.id as customer_id
    FROM case_management cm
    CROSS JOIN customer_management_customer c
    WHERE cm.customer_id IS NULL
        AND c.is_deleted = 0
        AND c.status IN ('CASE', 'PAYMENT', 'WON')
    LIMIT 10
) AS mapping ON cm.id = mapping.case_id
SET cm.customer_id = mapping.customer_id
WHERE cm.customer_id IS NULL;

-- 2. 更新案件关联经办人（从关联客户获取）
UPDATE case_management cm
INNER JOIN customer_management_customer c ON cm.customer_id = c.id
SET 
    cm.owner_user_id = c.owner_user_id,
    cm.owner_user_name = c.owner_user_name
WHERE cm.owner_user_id IS NULL
    AND c.owner_user_id IS NOT NULL;

-- 3. 更新案件关联合同（从关联客户获取已确认的合同）
UPDATE case_management cm
INNER JOIN customer_management_customer c ON cm.customer_id = c.id
INNER JOIN customer_management_contract ct ON ct.customer_id = c.id
SET cm.contract_id = ct.id
WHERE cm.contract_id IS NULL
    AND ct.status = 'confirmed'
    AND ct.id = (
        SELECT id FROM customer_management_contract
        WHERE customer_id = c.id AND status = 'confirmed'
        ORDER BY create_datetime DESC
        LIMIT 1
    );

-- 4. 更新合同关联案件（从关联客户获取案件）
UPDATE customer_management_contract ct
INNER JOIN customer_management_customer c ON ct.customer_id = c.id
INNER JOIN case_management cm ON cm.customer_id = c.id
SET ct.case_id = cm.id
WHERE ct.case_id IS NULL
    AND ct.status = 'confirmed'
    AND cm.id = (
        SELECT id FROM case_management
        WHERE customer_id = c.id
        ORDER BY create_datetime DESC
        LIMIT 1
    );

-- 5. 验证更新结果
SELECT 
    '案件关联统计' AS type,
    COUNT(*) AS total,
    SUM(CASE WHEN customer_id IS NOT NULL THEN 1 ELSE 0 END) AS with_customer,
    SUM(CASE WHEN owner_user_id IS NOT NULL THEN 1 ELSE 0 END) AS with_owner,
    SUM(CASE WHEN contract_id IS NOT NULL THEN 1 ELSE 0 END) AS with_contract
FROM case_management
WHERE is_deleted = 0;

SELECT 
    '合同关联统计' AS type,
    COUNT(*) AS total,
    SUM(CASE WHEN case_id IS NOT NULL THEN 1 ELSE 0 END) AS with_case
FROM customer_management_contract;
