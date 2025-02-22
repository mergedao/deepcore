CREATE TABLE `app` (
  `id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'UUID',
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Name of the app',
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT 'Description of the app',
  `mode` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Mode of the app: function call, ReAct (default)',
  `icon` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Icon URL of the app',
  `status` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Status of the app: draft, active, inactive',
  `role_settings` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT 'Role settings for the agent',
  `welcome_message` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT 'Welcome message for the agent',
  `twitter_link` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Twitter link for the agent',
  `telegram_bot_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Telegram bot ID for the agent',
  `tool_prompt` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT 'Tool prompt for the agent',
  `max_loops` int DEFAULT 3 COMMENT 'Maximum number of loops the agent can perform',
  `is_deleted` tinyint(1) DEFAULT NULL COMMENT 'Logical deletion flag',
  `tenant_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Tenant ID',
  `update_time` datetime DEFAULT (now()) COMMENT 'Last update time',
  `create_time` datetime DEFAULT (now()) COMMENT 'Creation time',
  `model_json` JSON COMMENT 'Additional fields merged into a JSON column',
  `is_public` BOOLEAN DEFAULT FALSE COMMENT 'Whether the agent is public',
  `is_official` BOOLEAN DEFAULT FALSE COMMENT 'Whether the agent is official preset',
  `is_hot` BOOLEAN DEFAULT FALSE COMMENT 'Whether the agent is hot',
  `suggested_questions` JSON COMMENT 'List of suggested questions for the agent',
  `model_id` bigint DEFAULT NULL COMMENT 'ID of the associated model',
  `category_id` bigint DEFAULT NULL COMMENT 'ID of the category',
  `create_fee` DECIMAL(20,9) DEFAULT 0.000000000 COMMENT 'Fee for creating the agent (tips for creator)',
  `price` DECIMAL(20,9) DEFAULT 0.000000000 COMMENT 'Fee for using the agent',
  PRIMARY KEY (`id`),
  KEY `idx_tenant` (`tenant_id`),
  KEY `idx_model` (`model_id`),
  KEY `idx_category` (`category_id`),
  KEY `idx_public_official` (`is_public`, `is_official`),
  KEY `idx_hot` (`is_hot`),
  CONSTRAINT `fk_app_category` FOREIGN KEY (`category_id`) REFERENCES `categories` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE `file_storage` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT 'Auto-incrementing ID',
  `file_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Name of the file',
  `file_uuid` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'file UUID',
  `file_content` LONGBLOB NOT NULL COMMENT 'Content of the file',
  `size` bigint NOT NULL COMMENT 'Size of the file',
  `create_time` datetime DEFAULT (now()) COMMENT 'Creation time',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE `tools` (
  `id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'UUID',
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Name of the tool',
  `description` varchar(800) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Description of the tool',
  `type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Type of the tool: function or openAPI',
  `origin` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'API origin',
  `path` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'API path',
  `method` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'HTTP method',
  `parameters` JSON COMMENT 'API parameters including header, query, path, and body',
  `is_deleted` tinyint(1) DEFAULT NULL COMMENT 'Logical deletion flag',
  `tenant_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Tenant ID',
  `update_time` datetime DEFAULT (now()) COMMENT 'Last update time',
  `create_time` datetime DEFAULT (now()) COMMENT 'Creation time',
  `is_public` BOOLEAN DEFAULT FALSE COMMENT 'Whether the tool is public',
  `is_official` BOOLEAN DEFAULT FALSE COMMENT 'Whether the tool is official preset',
  `auth_config` JSON COMMENT 'Authentication configuration in JSON format',
  `is_stream` BOOLEAN DEFAULT FALSE COMMENT 'Whether the API returns a stream response',
  `output_format` JSON COMMENT 'JSON configuration for formatting API output',
  `category_id` bigint DEFAULT NULL COMMENT 'ID of the category',
  PRIMARY KEY (`id`),
  KEY `idx_tenant` (`tenant_id`),
  KEY `idx_public_official` (`is_public`, `is_official`),
  KEY `idx_type` (`type`),
  KEY `idx_category` (`category_id`),
  CONSTRAINT `fk_tool_category` FOREIGN KEY (`category_id`) REFERENCES `categories` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `users` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT 'Auto-incrementing ID',
  `username` varchar(120) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Username',
  `email` varchar(120) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Email address',
  `password` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Hashed password',
  `wallet_address` varchar(42) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Ethereum wallet address',
  `nonce` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Nonce for wallet signature',
  `tenant_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Tenant ID',
  `create_time` datetime DEFAULT (now()) COMMENT 'Registration time',
  `update_time` datetime DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update time',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_username` (`username`),
  UNIQUE KEY `uk_email` (`email`),
  UNIQUE KEY `uk_wallet_address` (`wallet_address`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `agent_tools` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT 'Auto-incrementing ID',
  `agent_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'UUID of the agent',
  `tool_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'UUID of the tool',
  `tenant_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Tenant ID',
  `create_time` datetime DEFAULT (now()) COMMENT 'Creation time',
  PRIMARY KEY (`id`),
  KEY `idx_agent_tool` (`agent_id`, `tool_id`),
  KEY `idx_tenant` (`tenant_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `models` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT 'Auto-incrementing ID',
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Name of the model',
  `endpoint` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'API endpoint of the model',
  `api_key` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'API key for the model',
  `is_official` BOOLEAN DEFAULT FALSE COMMENT 'Whether the model is official preset',
  `is_public` BOOLEAN DEFAULT FALSE COMMENT 'Whether the model is public',
  `tenant_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Tenant ID',
  `create_time` datetime DEFAULT (now()) COMMENT 'Creation time',
  `update_time` datetime DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update time',
  PRIMARY KEY (`id`),
  KEY `idx_tenant` (`tenant_id`),
  KEY `idx_public_official` (`is_public`, `is_official`),
  KEY `idx_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE `categories` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT 'Auto-incrementing ID',
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Name of the category',
  `type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Type of the category: agent or tool',
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT 'Description of the category',
  `tenant_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Tenant ID',
  `sort_order` int DEFAULT 0 COMMENT 'Sort order for display',
  `create_time` datetime DEFAULT (now()) COMMENT 'Creation time',
  `update_time` datetime DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update time',
  PRIMARY KEY (`id`),
  KEY `idx_tenant` (`tenant_id`),
  KEY `idx_type` (`type`),
  KEY `idx_sort` (`sort_order`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;



INSERT INTO `models` (`id`, `name`, `endpoint`, `api_key`, `is_official`, `is_public`, `tenant_id`, `create_time`, `update_time`)
VALUES (1, 'gpt-4o', 'https://api.openai.com/v1', 'gAAAAABnuCJ5-rriRjFbe-ESUfkI0cyurCUH8YEzRhUXA2fO3IV4v1SpKxqlYiwYJL9BlaLmce4JbxT0cXNlkzuVKmYN4odStY3jBay6VIKUz9Jdpd2sn_yok9rx7berIFyCZsxPlhpOwOx8M0PAGm9IhekJzZnXlpJPtaVQRwubksowGydi4pgThnBn62IqCpEENMvOxuyCwjZ9ga7kztlWkolUyjwruq1B4GBuWNb3RZKELDzY34qCcHYgz2y7dq0cW4jtD8vVJOWze6aZwMe_Iw6ERrOi7P46S9axjQNKRr4hPVaVCSQ=', 1, 1, NULL, '2025-02-17 05:21:38', '2025-02-21 06:58:04');

INSERT INTO `models` (`id`, `name`, `endpoint`, `api_key`, `is_official`, `is_public`, `tenant_id`, `create_time`, `update_time`)
VALUES (2, 'gpt-4o-mini', 'https://api.openai.com/v1', 'gAAAAABnuCJ5-rriRjFbe-ESUfkI0cyurCUH8YEzRhUXA2fO3IV4v1SpKxqlYiwYJL9BlaLmce4JbxT0cXNlkzuVKmYN4odStY3jBay6VIKUz9Jdpd2sn_yok9rx7berIFyCZsxPlhpOwOx8M0PAGm9IhekJzZnXlpJPtaVQRwubksowGydi4pgThnBn62IqCpEENMvOxuyCwjZ9ga7kztlWkolUyjwruq1B4GBuWNb3RZKELDzY34qCcHYgz2y7dq0cW4jtD8vVJOWze6aZwMe_Iw6ERrOi7P46S9axjQNKRr4hPVaVCSQ=', 1, 1, NULL, '2025-02-17 05:21:38', '2025-02-21 06:57:26');

INSERT INTO `models` (`id`, `name`, `endpoint`, `api_key`, `is_official`, `is_public`, `tenant_id`, `create_time`, `update_time`)
VALUES (3, 'o1', 'https://api.openai.com/v1', 'gAAAAABnuCJ5-rriRjFbe-ESUfkI0cyurCUH8YEzRhUXA2fO3IV4v1SpKxqlYiwYJL9BlaLmce4JbxT0cXNlkzuVKmYN4odStY3jBay6VIKUz9Jdpd2sn_yok9rx7berIFyCZsxPlhpOwOx8M0PAGm9IhekJzZnXlpJPtaVQRwubksowGydi4pgThnBn62IqCpEENMvOxuyCwjZ9ga7kztlWkolUyjwruq1B4GBuWNb3RZKELDzY34qCcHYgz2y7dq0cW4jtD8vVJOWze6aZwMe_Iw6ERrOi7P46S9axjQNKRr4hPVaVCSQ=', 1, 1, NULL, '2025-02-17 05:21:38', '2025-02-21 06:57:26');

INSERT INTO `models` (`id`, `name`, `endpoint`, `api_key`, `is_official`, `is_public`, `tenant_id`, `create_time`, `update_time`)
VALUES (4, 'o1-mini', 'https://api.openai.com/v1', 'gAAAAABnuCJ5-rriRjFbe-ESUfkI0cyurCUH8YEzRhUXA2fO3IV4v1SpKxqlYiwYJL9BlaLmce4JbxT0cXNlkzuVKmYN4odStY3jBay6VIKUz9Jdpd2sn_yok9rx7berIFyCZsxPlhpOwOx8M0PAGm9IhekJzZnXlpJPtaVQRwubksowGydi4pgThnBn62IqCpEENMvOxuyCwjZ9ga7kztlWkolUyjwruq1B4GBuWNb3RZKELDzY34qCcHYgz2y7dq0cW4jtD8vVJOWze6aZwMe_Iw6ERrOi7P46S9axjQNKRr4hPVaVCSQ=', 1, 1, NULL, '2025-02-17 05:21:38', '2025-02-21 06:57:26');

INSERT INTO `models` (`id`, `name`, `endpoint`, `api_key`, `is_official`, `is_public`, `tenant_id`, `create_time`, `update_time`)
VALUES (5, 'gpt-4-turbo', 'https://api.openai.com/v1', 'gAAAAABnuCJ5-rriRjFbe-ESUfkI0cyurCUH8YEzRhUXA2fO3IV4v1SpKxqlYiwYJL9BlaLmce4JbxT0cXNlkzuVKmYN4odStY3jBay6VIKUz9Jdpd2sn_yok9rx7berIFyCZsxPlhpOwOx8M0PAGm9IhekJzZnXlpJPtaVQRwubksowGydi4pgThnBn62IqCpEENMvOxuyCwjZ9ga7kztlWkolUyjwruq1B4GBuWNb3RZKELDzY34qCcHYgz2y7dq0cW4jtD8vVJOWze6aZwMe_Iw6ERrOi7P46S9axjQNKRr4hPVaVCSQ=', 1, 1, NULL, '2025-02-17 05:21:38', '2025-02-21 06:57:26');

INSERT INTO `models` (`id`, `name`, `endpoint`, `api_key`, `is_official`, `is_public`, `tenant_id`, `create_time`, `update_time`)
VALUES (6, 'gpt-4-0125-preview', 'https://api.openai.com/v1', 'gAAAAABnuCJ5-rriRjFbe-ESUfkI0cyurCUH8YEzRhUXA2fO3IV4v1SpKxqlYiwYJL9BlaLmce4JbxT0cXNlkzuVKmYN4odStY3jBay6VIKUz9Jdpd2sn_yok9rx7berIFyCZsxPlhpOwOx8M0PAGm9IhekJzZnXlpJPtaVQRwubksowGydi4pgThnBn62IqCpEENMvOxuyCwjZ9ga7kztlWkolUyjwruq1B4GBuWNb3RZKELDzY34qCcHYgz2y7dq0cW4jtD8vVJOWze6aZwMe_Iw6ERrOi7P46S9axjQNKRr4hPVaVCSQ=', 1, 1, NULL, '2025-02-17 05:21:38', '2025-02-21 06:57:26');


INSERT INTO `models` (`id`, `name`, `endpoint`, `api_key`, `is_official`, `is_public`, `tenant_id`, `create_time`, `update_time`)
VALUES (10, 'deepseek-v3', 'https://api.deepseek.com/v1', '2222', 1, 1, NULL, '2025-02-18 08:31:24', '2025-02-18 08:31:24');
INSERT INTO `models` (`id`, `name`, `endpoint`, `api_key`, `is_official`, `is_public`, `tenant_id`, `create_time`, `update_time`)
VALUES (11, 'deepseek-r1', 'https://api.deepseek.com/v1', '2222', 1, 1, NULL, '2025-02-18 08:31:56', '2025-02-18 08:31:56');

INSERT INTO `models` (`id`, `name`, `endpoint`, `api_key`, `is_official`, `is_public`, `tenant_id`, `create_time`, `update_time`)
VALUES (15, 'grok-2', 'https://api.x.ai/v1', 'gAAAAABnuDiedFNNh5n0LYIILo4kvO2KyzEbhQgYsg_Edt2f3vtvgmLGnusU-0IwbUL7J3H4pHlv-5OQ1oNN6Yj6N_lAhOY0_iwD1AdKxYiv9fTjhLLRMwS-f5mxieGvdLEIuki2lFPom9wzASGLgBggjfrTM0NEOq8JXOXJ0ziB9jhoNJhPJf15ToW-zTptHrdDQ0pCc6gi', 1, 1, NULL, '2025-02-17 05:21:38', '2025-02-21 06:57:26');

INSERT INTO `models` (`id`, `name`, `endpoint`, `api_key`, `is_official`, `is_public`, `tenant_id`, `create_time`, `update_time`)
VALUES (16, 'grok-2-latest', 'https://api.x.ai/v1', 'gAAAAABnuDiedFNNh5n0LYIILo4kvO2KyzEbhQgYsg_Edt2f3vtvgmLGnusU-0IwbUL7J3H4pHlv-5OQ1oNN6Yj6N_lAhOY0_iwD1AdKxYiv9fTjhLLRMwS-f5mxieGvdLEIuki2lFPom9wzASGLgBggjfrTM0NEOq8JXOXJ0ziB9jhoNJhPJf15ToW-zTptHrdDQ0pCc6gi', 1, 1, NULL, '2025-02-17 05:21:38', '2025-02-21 06:57:26');


-- ALTER TABLE `tools`
-- ADD COLUMN `tenant_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Tenant ID' AFTER `is_deleted`;
--
-- ALTER TABLE `users`
-- ADD COLUMN `tenant_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Tenant ID' AFTER `nonce`;
--
-- ALTER TABLE `app`
-- ADD COLUMN `model_json` JSON COMMENT 'Additional fields merged into a JSON column' AFTER `create_time`;
--
-- ALTER TABLE `app` MODIFY COLUMN `id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'UUID';
--
-- ALTER TABLE `tools` MODIFY COLUMN `app_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'UUID of the associated app';

-- Add create_fee and price columns to existing app table
-- ALTER TABLE `app`
-- ADD COLUMN `create_fee` DECIMAL(20,9) DEFAULT 0.000000000 COMMENT 'Fee for creating the agent (tips for creator)',
-- ADD COLUMN `price` DECIMAL(20,9) DEFAULT 0.000000000 COMMENT 'Fee for using the agent';
--
-- -- Update existing records to set default values
-- UPDATE `app` SET
--     `create_fee` = 0.000000000,
--     `price` = 0.000000000
-- WHERE `create_fee` IS NULL OR `price` IS NULL;
--
-- -- Add description column to existing tools table
-- ALTER TABLE `tools`
-- ADD COLUMN `description` varchar(800) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Description of the tool';
--
-- ALTER TABLE `models`
-- MODIFY COLUMN api_key VARCHAR(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'API key for the model';


-- ALTER TABLE `tools`
-- ADD COLUMN `is_stream` BOOLEAN DEFAULT FALSE COMMENT 'Whether the API returns a stream response',
-- ADD COLUMN `output_format` JSON COMMENT 'JSON configuration for formatting API output';


-- ALTER TABLE `app`
-- ADD COLUMN `category_id` bigint DEFAULT NULL COMMENT 'ID of the category',
-- ADD KEY `idx_category` (`category_id`),
-- ADD CONSTRAINT `fk_app_category` FOREIGN KEY (`category_id`) REFERENCES `categories` (`id`) ON DELETE SET NULL;
--
-- ALTER TABLE `tools`
-- ADD COLUMN `category_id` bigint DEFAULT NULL COMMENT 'ID of the category',
-- ADD KEY `idx_category` (`category_id`),
-- ADD CONSTRAINT `fk_tool_category` FOREIGN KEY (`category_id`) REFERENCES `categories` (`id`) ON DELETE SET NULL;

-- Insert default agent categories
INSERT INTO `categories` (`name`, `type`, `description`, `tenant_id`, `sort_order`, `create_time`, `update_time`) VALUES
('Programmer', 'agent', 'Programming assistant for code writing, review, and debugging', NULL, 10, NOW(), NOW()),
('Researcher', 'agent', 'Research assistant for conducting in-depth research and literature reviews', NULL, 20, NOW(), NOW()),
('Analyst', 'agent', 'Data analyst for analyzing data and generating reports', NULL, 30, NOW(), NOW()),
('Twitter', 'agent', 'Twitter assistant for social media management and content creation', NULL, 40, NOW(), NOW()),
('Network', 'agent', 'Network engineer for network configuration and troubleshooting', NULL, 50, NOW(), NOW()),
('Crypto News', 'agent', 'Cryptocurrency news assistant for latest market updates', NULL, 60, NOW(), NOW()),
('Graphics', 'agent', 'Graphics design assistant for image creation and editing', NULL, 70, NOW(), NOW()),
('Video', 'agent', 'Video production assistant for video editing and post-processing', NULL, 80, NOW(), NOW());

-- Insert default tool categories
INSERT INTO `categories` (`name`, `type`, `description`, `tenant_id`, `sort_order`, `create_time`, `update_time`) VALUES
('API Tools', 'tool', 'Tools for interacting with external services via APIs', NULL, 110, NOW(), NOW()),
('Data Processing', 'tool', 'Tools for data transformation and analysis', NULL, 120, NOW(), NOW()),
('File Operations', 'tool', 'Tools for file management and processing', NULL, 130, NOW(), NOW()),
('Image Processing', 'tool', 'Tools for image editing and generation', NULL, 140, NOW(), NOW()),
('Text Processing', 'tool', 'Tools for text analysis and transformation', NULL, 150, NOW(), NOW()),
('Code Generation', 'tool', 'Tools for automatic code generation', NULL, 160, NOW(), NOW()),
('Network Tools', 'tool', 'Tools for network diagnostics and management', NULL, 170, NOW(), NOW()),
('Security Tools', 'tool', 'Tools for security detection and protection', NULL, 180, NOW(), NOW());

-- Add hot field and index to app table
ALTER TABLE `app`
ADD COLUMN `is_hot` BOOLEAN DEFAULT FALSE COMMENT 'Whether the agent is hot',
ADD KEY `idx_hot` (`is_hot`);


