/*
 Navicat Premium Data Transfer

 Source Server         : 本地Mysql8
 Source Server Type    : MySQL
 Source Server Version : 80043 (8.0.43)
 Source Host           : 192.168.3.7:3308
 Source Schema         : law-smart-link

 Target Server Type    : MySQL
 Target Server Version : 80043 (8.0.43)
 File Encoding         : 65001

 Date: 28/10/2025 15:27:17
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for case_management
-- ----------------------------
DROP TABLE IF EXISTS `case_management`;
CREATE TABLE `case_management`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `case_number` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `case_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `case_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `case_description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL,
  `is_deleted` tinyint(1) NOT NULL,
  `case_date` date NULL DEFAULT NULL,
  `case_notes` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL,
  `case_result` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL,
  `case_status` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `contract_amount` decimal(20, 2) NULL DEFAULT NULL,
  `defendant_address` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `defendant_credit_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `defendant_legal_representative` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `defendant_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `draft_person` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `facts_and_reasons` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL,
  `filing_date` date NULL DEFAULT NULL,
  `jurisdiction` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `lawyer_fee` decimal(20, 2) NULL DEFAULT NULL,
  `litigation_request` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL,
  `petitioner` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `plaintiff_address` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `plaintiff_credit_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `plaintiff_legal_representative` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `plaintiff_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `case_management_is_deleted_5cbac7b8`(`is_deleted` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 10 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = DYNAMIC;

SET FOREIGN_KEY_CHECKS = 1;
