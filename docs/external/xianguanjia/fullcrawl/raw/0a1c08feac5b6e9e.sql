/*
 Navicat Premium Data Transfer

 Source Server         : xym-tidb
 Source Server Type    : MySQL
 Source Server Version : 50725 (5.7.25-TiDB-v6.5.2)
 Source Host           : 39.108.130.231:4000
 Source Schema         : xym_biz

 Target Server Type    : MySQL
 Target Server Version : 50725 (5.7.25-TiDB-v6.5.2)
 File Encoding         : 65001

 Date: 17/10/2024 14:08:26
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for prd_error_tip
-- ----------------------------
DROP TABLE IF EXISTS `prd_error_tip`;
CREATE TABLE `prd_error_tip`  (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `err_code` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
  `err_sub_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
  `err_msg` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
  `content` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
  `status` tinyint(4) NOT NULL,
  `create_time` int(11) NOT NULL,
  `update_time` int(11) NOT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 30002 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_bin ROW_FORMAT = Compact;

-- ----------------------------
-- Records of prd_error_tip
-- ----------------------------
INSERT INTO `prd_error_tip` VALUES (1, 'TOP_ITEM_BIZCHECK_FAIL', '', '商品业务模式校验失败', '该宝贝是在闲鱼APP发布，闲管家暂不支持编辑，请前往APP编辑', 1, 1686559188, 1686559188);
INSERT INTO `prd_error_tip` VALUES (2, 'TOP_ITEM_ADD_FAIL', 'PLAYBOY_ERRORCODE_REACHED_PUBLISH_COUNT_LIMIT', 'PLAYBOY_ERRORCODE_REACHED_PUBLISH_COUNT_LIMIT:用户发布商品数已达到上限;', '闲鱼店铺已达发品上限，你可以删除处理中的数据，回到商品列表编辑现有商品或下架其他商品。', 1, 1686559188, 1686559188);
INSERT INTO `prd_error_tip` VALUES (3, 'TOP_ITEM_EDIT_FAIL', 'USER_PROTOCOL_VALID_ERROR', 'USER_PROTOCOL_VALID_ERROR:亲，小闲鱼有点忙，请稍后重试哦;', '此商品类目不正确，你可以删除处理中的数据，回到商品列表点击【编辑】按钮，更改为其他分类', 1, 1686559188, 1686559188);
INSERT INTO `prd_error_tip` VALUES (4, 'TOP_ITEM_EDIT_FAIL', 'DIVISION_ERROR_DIVISION_ID', 'DIVISION_ERROR_DIVISION_ID:根据地区id找不到对应的省、市、区，或者不是叶子节点行政单位;', '该商品发货地异常，请反馈客服处理', 1, 1686559188, 1686559188);
INSERT INTO `prd_error_tip` VALUES (5, 'TOP_ITEM_BIZ_OFFLINE', '', '此业务已下线，不支持发布', '此业务已下线，你可以删除处理中的数据，回到商品列表创建新的商品', 1, 1686559188, 1686559188);
INSERT INTO `prd_error_tip` VALUES (6, 'TOP_ITEM_EDIT_FAIL', 'USER_RIGHTS_PROTOCOL_MUST_SIGN', 'USER_RIGHTS_PROTOCOL_MUST_SIGN:当前商品必须签署“七天无理由协议”;', '此商品没有开启“7天无理由”服务，你可以删除处理中的数据，回到商品列表点击【编辑】按钮，在详情页中启用“7天无理由”服务', 1, 1686559188, 1686559188);
INSERT INTO `prd_error_tip` VALUES (7, 'TOP_ITEM_EDIT_FAIL', 'IDLE_SERVICE_NOT_OPEN', 'IDLE_SERVICE_NOT_OPEN:服务暂未开通;', '此商品有服务未开启，你可以删除处理中的数据，回到商品列表点击【编辑】按钮，在详情页中启用对应的服务', 1, 1686559188, 1686559188);
INSERT INTO `prd_error_tip` VALUES (8, 'TOP_BOOK_PARAM_NULL', '', '图书参数信息不全', '图书信息填写不正确。你可以删除处理中的数据，回到商品列表点击【编辑】按钮，在详情页中正确填写“图书信息”', 1, 1686559188, 1686559188);
INSERT INTO `prd_error_tip` VALUES (9, 'TOP_ITEM_ADD_FAIL', 'PLAYBOY_ERRORCODE_ITEM_SKU_PROPERTY_VALUE_SET_SIZE_ILLETAL', 'PLAYBOY_ERRORCODE_ITEM_SKU_PROPERTY_VALUE_SET_SIZE_ILLETAL:Sku属性项项应该包含2-20个属性值;', '属性项不符合2-20个，你可以删除处理中的数据，回到商品列表点击【编辑】按钮，在详情页中正确填写属性值', 1, 1686559188, 1686559188);
INSERT INTO `prd_error_tip` VALUES (10, 'TOP_ITEM_EDIT_FAIL', 'SKU_PRICE_ILLEGAL', 'SKU_PRICE_ILLEGAL:宝贝价格必须在0元与1亿元之间;', '价格不在0~1亿范围内，你可以删除处理中的数据，回到商品列表点击【编辑】按钮，在详情页中正确填写价格', 1, 1686559188, 1686559188);
INSERT INTO `prd_error_tip` VALUES (11, 'TOP_ITEM_EDIT_FAIL', 'USER_ERROR_USER_WAS_FORBIDDEN2', 'USER_ERROR_USER_WAS_FORBIDDEN2:用户被处罚限制发布;', '当前店铺被处罚无法发布商品，请前往闲鱼APP我的-设置-安全中心查看违规信息', 1, 1686559188, 1686559188);
INSERT INTO `prd_error_tip` VALUES (12, 'TOP_ITEM_ADD_FAIL', 'BOOK_BARCODE_NOT_NULL', 'BOOK_BARCODE_NOT_NULL:图书类宝贝需使用标题右侧的“扫一扫”，扫描图书条形码后发布;', 'ISBN码不合法，你可以删除处理中的数据，回到商品列表点击【编辑】按钮，在编辑页修改为正确的13位数字的ISBN码', 1, 1686559188, 1686559188);
INSERT INTO `prd_error_tip` VALUES (13, 'TOP_SPGUARANTEE_LIMIT', '', '服务标签不支持非优品商品', '此业务已下线，你可以删除处理中的数据，回到商品列表创建新的商品', 1, 1686559188, 1686559188);
INSERT INTO `prd_error_tip` VALUES (14, 'TOP_ITEM_ADD_FAIL', 'KFC_ERROR_PTZLZZZR_CONDITION', 'KFC_ERROR_PTZLZZZR_CONDITION:请核实发布商品是否属于闲鱼禁止发布的类目或需要资质准入，如您已上传特许资质，可点击右上方发布按钮。;', '闲鱼禁止发布奶粉、医疗器械、酒类、香烟、电池、党政机关、涉及歧视、陪伴类等商品，你可以删除处理中的数据，回到商品列表点击【编辑】按钮检查标题或描述是否包含这些违规词', 1, 1686559188, 1686559188);
INSERT INTO `prd_error_tip` VALUES (15, 'TOP_ITEM_EDIT_FAIL', 'ITEM_NOT_FOUND', 'ITEM_NOT_FOUND:找不到该商品;', '该宝贝可能涉及违规已被闲鱼删除，请重新发布合规的宝贝', 1, 1686559188, 1686559188);
INSERT INTO `prd_error_tip` VALUES (16, 'TOP_ITEM_EDIT_FAIL', 'USER_RIGHTS_PROTOCOL_CANNOT_SIGN_C2S2C', 'USER_RIGHTS_PROTOCOL_CANNOT_SIGN_C2S2C:“描述不符包邮退协议”不可以和验货宝协议同时签署;', '验货宝商品开启了描述不符包邮退服务，你可以删除处理中的数据，回到商品列表，点击【编辑】按钮，关闭描述不符包邮退的服务就可以正常发布了', 1, 1686559188, 1686559188);
INSERT INTO `prd_error_tip` VALUES (17, 'TOP_ITEM_ADD_FAIL', 'QUANTITY_ITEM_CAT_TOO_LARGE_NEW', 'QUANTITY_ITEM_CAT_TOO_LARGE_NEW:您发布的宝贝(包括一口价、帖子、拍卖、鱼塘活动)数量超过50个，请您及时调整您的宝贝数量，再上传宝贝哦;', '闲鱼店铺已达发品上限，你可以删除处理中的数据，回到商品列表编辑现有商品或下架其他商品。', 1, 1686559188, 1686559188);
INSERT INTO `prd_error_tip` VALUES (18, 'TOP_ITEM_ADD_FAIL', 'QUERY_ITEM_CAT_FAILED', 'QUERY_ITEM_CAT_FAILED:发布失败，请稍后重试吧!;', '类目错误或下架了，你可以删除处理中的数据，回到商品列表点击【编辑】按钮，更改为其他分类', 1, 1686559188, 1686559188);
INSERT INTO `prd_error_tip` VALUES (19, 'TOP_ITEM_EDIT_FAIL', 'PLAYBOY_ERRORCODE_PLEASE_UPDATE_APP_VERSION', 'PLAYBOY_ERRORCODE_PLEASE_UPDATE_APP_VERSION:您的闲鱼app版本太旧，请升级到最新版!;', '你可以在手机应用市场将闲鱼APP更新至最新版', 1, 1686559188, 1686559188);
INSERT INTO `prd_error_tip` VALUES (20, 'TOP_ITEM_ADD_FAIL', 'KFC_ERROR_PUBLISH_FORBIDDEN', 'KFC_ERROR_PUBLISH_FORBIDDEN:请勿发布需资质准入或属于闲鱼违规类的商品信息，请重新核实再发布。;', '闲鱼禁止发布奶粉、医疗器械、酒类、香烟、电池、党政机关、涉及歧视、陪伴类等商品，你可以删除处理中的数据，回到商品列表点击【编辑】按钮检查标题或描述是否包含这些违规词', 1, 1686559188, 1686559188);
INSERT INTO `prd_error_tip` VALUES (21, 'TOP_SELLER_NOTALLOW_ACCESS', '', '卖家未通过闲鱼招商,请联系闲鱼运营', '如果没有对接过招商你可联系行业闲鱼运营；如果已经通过招商则重新授权闲鱼号', 1, 1686559188, 1686559188);
INSERT INTO `prd_error_tip` VALUES (22, 'TOP_ITEM_EDIT_FAIL', 'KFC_ERROR_VIRTUAL_TITLE', 'KFC_ERROR_VIRTUAL_TITLE:请勿发布充值卡券、虚拟游戏等高风险商品的交易信息，请重新核实再发布。;', '请勿发布包含“卡券、虚拟游戏”类内容的商品，你可以删除处理中的数据，回到商品列表，点击【编辑】按钮，将商品详情更改为合规的内容', 1, 1686559188, 1686559188);
INSERT INTO `prd_error_tip` VALUES (23, 'TOP_ITEM_EDIT_FAIL', 'ITEM_CAN_NOT_PUBLISH', 'ITEM_CAN_NOT_PUBLISH:亲，您不能发布多库存宝贝哦;', '非鱼小铺卖家不能发布多库存宝贝，你可以删除处理中的数据，回到商品列表，编辑宝贝为单库存就可以正常发布了', 1, 1686559188, 1686559188);
INSERT INTO `prd_error_tip` VALUES (24, 'TOP_ISVBIZ_NOTALLOW_ACCESS', '', '服务商业务未准入,请联系闲鱼运营', '闲鱼优品已下线，你可以删除处理中的数据，回到商品列表，创建新商品或更改商品类型为“普通商品”', 1, 1686559188, 1686559188);
INSERT INTO `prd_error_tip` VALUES (25, 'TOP_ITEM_EDIT_FAIL', 'BOOK_PUBLISH_FREQUENTLY', 'BOOK_PUBLISH_FREQUENTLY:图书试运营期间每月最多发布15本;', '图书发布数量已达上限，你可以删除处理中的数据，回到商品列表点击编辑旧商品或下架旧商品创建新商品', 1, 1686559188, 1686559188);
INSERT INTO `prd_error_tip` VALUES (26, 'TOP_ITEM_EDIT_FAIL', 'IC_OPTIMISTIC_LOCKING_CONFLICT', 'IC_OPTIMISTIC_LOCKING_CONFLICT:系统错误，请重试;', '系统繁忙，请稍后重试', 1, 1686559188, 1686559188);
INSERT INTO `prd_error_tip` VALUES (27, 'TOP_ITEM_ADD_FAIL', 'SKU_QUANTITY_ILLEGAL', 'SKU_QUANTITY_ILLEGAL:宝贝库存数量必须在0与1万之间;', '库存数量没有在规定范围内，你可以删除处理中的数据，回到商品列表点击【编辑】按钮重新设置库存', 1, 1686559188, 1686559188);
INSERT INTO `prd_error_tip` VALUES (28, 'TOP_ITEM_EDIT_FAIL', 'IC_CHECKSTEP_ITME_NOT_IN_SKU_PRICE', 'IC_CHECKSTEP_ITME_NOT_IN_SKU_PRICE:一口价必须与有库存的宝贝规格价格一致;', '商品的价格不在sku价格内，你可以删除处理中的数据，回到商品列表点击【编辑】按钮重新设置价格', 1, 1686559188, 1686559188);
INSERT INTO `prd_error_tip` VALUES (29, 'isp.top-remote-connection-timeout', '', '远程服务调用超时', '系统繁忙，请稍后重试', 1, 1686559188, 1686559188);
INSERT INTO `prd_error_tip` VALUES (30, 'accesscontrol.limited-by-api-access-count', '', 'This ban will last for 1 more seconds', '系统繁忙，请稍后重试', 1, 1686559188, 1686559188);
INSERT INTO `prd_error_tip` VALUES (31, 'TOP_ITEM_ADD_FAIL', 'QUALIFICATION_NOT_SUPPORT_CATE', 'QUALIFICATION_NOT_SUPPORT_CATE:您没有发布该类商品的资质！;', '发布该品类宝贝需上传相关资质，你可以前往闲鱼APP-我的-认证招商-经营资质进行上传', 1, 1686559188, 1686559188);
INSERT INTO `prd_error_tip` VALUES (32, 'TOP_ITEM_ADD_FAIL', 'ITEM_PROPOSE_CHECK_ERROR', 'ITEM_PROPOSE_CHECK_ERROR:尊敬的用户，平台禁售酒水、婴幼儿奶粉、保健品等需要资质准入的预包装食品，感谢您的理解与支持。;', '闲鱼禁止发布奶粉、医疗器械、酒类、香烟、电池、党政机关、涉及歧视、陪伴类等商品，你可以删除处理中的数据，回到商品列表点击【编辑】按钮检查标题或描述是否包含这些违规词', 1, 1686559188, 1686559188);
INSERT INTO `prd_error_tip` VALUES (33, 'TOP_ITEM_ADD_FAIL', 'ERR_RULE_TITLE_SECURITY_CHAR_LIMITATION', 'ERR_RULE_TITLE_SECURITY_CHAR_LIMITATION:标题/卖点/短标题禁止使用半角符号“ <> ” 符号，但可以使用全角符号“ ＜＞”;', '标题/卖点/短标题输入不规范，你可以删除处理中的数据，回到商品列表点击【编辑】按钮，重新修改标题或描述', 1, 1686559188, 1686559188);
INSERT INTO `prd_error_tip` VALUES (34, 'TOP_ITEM_EDIT_FAIL', 'FORBIDDEN_QUANTITY_ZERO_ERROR', 'FORBIDDEN_QUANTITY_ZERO_ERROR:上架的数量必须大于0;', '你可以删除处理中的数据，回到商品列表点击【编辑】按钮，重新设置库存', 1, 1686559188, 1686559188);
INSERT INTO `prd_error_tip` VALUES (35, 'TOP_ITEM_ADD_FAIL', 'IC_CHECKSTEP_USERDEFINED_SKU_ERROR', 'IC_CHECKSTEP_USERDEFINED_SKU_ERROR:自定义销售属性不能含有特殊字符;', 'SKU的属性或者属性值禁止使用特殊符号，你可以删除处理中的数据，回到商品列表点击【编辑】按钮重新修改规格属性或属性值', 1, 1686559188, 1686559188);
INSERT INTO `prd_error_tip` VALUES (36, 'TOP_ITEM_ADD_FAIL', 'USER_NEED_XIANYU_REAL_VERIFY', 'USER_NEED_XIANYU_REAL_VERIFY:用户未通过闲鱼实名认证;', '请前往闲鱼APP-我的-设置-账号与安全进行实名认证', 1, 1686559188, 1686559188);
INSERT INTO `prd_error_tip` VALUES (37, 'TOP_ITEM_ADD_FAIL', 'C2S2C_DATA_MISSED', 'C2S2C_DATA_MISSED:请补充必填属性：品牌;', '宝贝没有选择品牌属性，你可以删除处理中的数据，回到商品列表点击【编辑】按钮，勾选品牌属性就可以重新发布了', 1, 1686559188, 1686559188);
INSERT INTO `prd_error_tip` VALUES (38, 'TOP_IMAGE_NOT_FOUND', '', '找不到传入的某些图片', '图片上传失败，请重新上传，你可以删除处理中的数据，回到商品列表点击【编辑】按钮重新上传图片', 1, 1686559188, 1686559188);
INSERT INTO `prd_error_tip` VALUES (39, 'TOP_ITEM_EDIT_FAIL', 'F_INVENTORY_05_16_010', 'F_INVENTORY_05_16_010:保存库存失败: [对不起，系统繁忙，请稍候再试], [请检查更新的商品库存是否已生效，若未生效，请稍后重试].;', '系统繁忙，请稍后重试', 1, 1686559188, 1686559188);
INSERT INTO `prd_error_tip` VALUES (40, 'TOP_ITEM_EDIT_FAIL', 'no_writing_check', 'no_writing_check:你的商品正在参加卡券频道秒杀活动,不允许价格编辑,库存减少;', '参加活动的商品不允许编辑价格和库存，将处理中的数据删除即可，不影响原商品', 1, 1686559188, 1686559188);
INSERT INTO `prd_error_tip` VALUES (41, 'TOP_ITEM_ADD_FAIL', 'ITEM_PROPOSE_CHECK_ERROR', 'ITEM_PROPOSE_CHECK_ERROR:亲爱的用户，您发布的内容存在违规风险，请做好自检自查，避免违规。;', '闲鱼禁止发布奶粉、医疗器械、酒类、香烟、电池、党政机关、涉及歧视、陪伴类等商品，你可以删除处理中的数据，回到商品列表点击【编辑】按钮检查标题或描述是否包含这些违规词', 1, 1686559188, 1686559188);
INSERT INTO `prd_error_tip` VALUES (42, 'TOP_ITEM_ADD_FAIL', 'ITEM_PROPOSE_CHECK_ERROR', 'ITEM_PROPOSE_CHECK_ERROR:亲，为了他人的生命与健康，请严格遵守国家相关规定，不要发布及宣传药品、医疗器械类相关商品，以免触犯平台规则，感谢您的理解与支持。;', '闲鱼禁止发布奶粉、医疗器械、酒类、香烟、电池、党政机关、涉及歧视、陪伴类等商品，你可以删除处理中的数据，回到商品列表点击【编辑】按钮检查标题或描述是否包含这些违规词', 1, 1686559188, 1686559188);
INSERT INTO `prd_error_tip` VALUES (43, 'TOP_ITEM_ADD_FAIL', 'PLAYBOY_ERRORCODE_ITEM_SKU_PROPERTY_KEY_NAME_LENGTH_ILLEGAL', 'PLAYBOY_ERRORCODE_ITEM_SKU_PROPERTY_KEY_NAME_LENGTH_ILLEGAL:属性名称应该是2-4个字符;', '属性名称至少包含一个汉字或2个英文字母，你可以删除处理中的数据，回到商品列表点击【编辑】重新编辑属性名称', 1, 1686559188, 1686559188);
INSERT INTO `prd_error_tip` VALUES (44, 'TOP_ITEM_EDIT_FAIL', 'C2S2C_DATA_MISSED', 'C2S2C_DATA_MISSED:请补充必填属性;', '商品详情有必填项未填，你可以删除处理中的数据，回到商品列表点击【编辑】补全所有必填项', 1, 1686559188, 1686559188);
INSERT INTO `prd_error_tip` VALUES (45, 'TOP_ITEM_ADD_FAIL', 'ITEM_PROPOSE_CHECK_ERROR', 'ITEM_PROPOSE_CHECK_ERROR:未成年人请勿发布虚拟网络游戏及其相关的服务类商品，请重新核实后再发布！;', '未成年人无法发布虚拟游戏类商品，你可以删除处理中的数据，回到商品列表点击重新发布其他合规内容', 1, 1686559188, 1686559188);
INSERT INTO `prd_error_tip` VALUES (46, 'TOP_ITEM_ADD_FAIL', 'FAIL_BIZ_ITEM_EDIT_TITLE_HAS_EMOJI', 'FAIL_BIZ_ITEM_EDIT_TITLE_HAS_EMOJI:亲,您的标题里面有表情,现在我们还不支持哦;', '商品标题含有表情包，你可以删除处理中的数据，回到商品列表点击【编辑】按钮修改商品标题使其不包含表情', 1, 1686559188, 1686559188);
INSERT INTO `prd_error_tip` VALUES (47, 'retry', 'retry', '自定义需要重试的错误。', '系统繁忙，请稍后重试', 1, 1686559188, 1686559188);
INSERT INTO `prd_error_tip` VALUES (48, 'TOP_ITEM_ADD_FAIL', 'STRONG_VALID_VERIFY_INFO', 'STRONG_VALID_VERIFY_INFO:用户未通过认证;', '自7月27号（明天）开始，没有签订支付宝收款协议的闲鱼号，将无法在闲管家发布商品，请各位商家及时自查。自查方法：闲鱼APP已发布的商品详情页或者APP发布成功后会有提示\n签订流程请点击链接查看：https://goofish.pro/learn?article_id=443263609565893&type=3', 1, 1691740550, 1691740550);
INSERT INTO `prd_error_tip` VALUES (49, 'TOP_ITEM_EDIT_FAIL', 'STRONG_VALID_VERIFY_INFO', 'STRONG_VALID_VERIFY_INFO:用户未通过认证;', '自7月27号（明天）开始，没有签订支付宝收款协议的闲鱼号，将无法在闲管家发布商品，请各位商家及时自查。自查方法：闲鱼APP已发布的商品详情页或者APP发布成功后会有提示\n签订流程请点击链接查看：https://goofish.pro/learn?article_id=443263609565893&type=3', 1, 1691740550, 1691740550);

SET FOREIGN_KEY_CHECKS = 1;
