/**
 * 分类图标精选集（M1 · 需求一）
 *
 * 供「分类新增/编辑弹窗 - 图标精选网格选择面板」（`components/common/CategoryIconPicker.vue`）
 * 使用的唯一图标来源：扁平数组、不分组、不设 Tab，数量控制在 90–110 之间（需求口径「约 100 个」）。
 *
 * 硬性约束（后续维护者增删条目时必须遵守，已由 `categoryIcons.test.js` 单测双向锚定）：
 *
 * 1. 必须包含全部 15 个预设分类图标（源自 `backend/app/main.py` 的 `PRESET_CATEGORIES`）：
 *    mdi-food、mdi-bus、mdi-cart、mdi-gamepad、mdi-hospital-box、mdi-home、mdi-cellphone、
 *    mdi-briefcase、mdi-bag-suitcase、mdi-receipt-text、mdi-cash-minus、mdi-wallet、
 *    mdi-gift、mdi-finance、mdi-cash-plus
 * 2. 必须包含表单默认图标与全局回退图标：mdi-cash、mdi-circle
 * 3. 所有条目必须是 @mdi/font 7.x 中真实存在的合法 `mdi-*` 名
 *    （全量字体已在 `main.js` 引入，故存量非选集图标仍可正常渲染，见组件的「不在精选集」分支）
 * 4. 保持无重复项；新增条目时按下方场景分区归位，数量超出 110 需先精简
 *
 * 覆盖场景清单（餐饮 / 交通 / 购物 / 居住 / 日用 / 娱乐 / 医疗 / 教育 / 通讯 /
 * 人情 / 旅行 / 工资 / 理财 / 副业 / 退款 / 通用票据 / 通用）逐项在下方分区注释中体现。
 */
export const CATEGORY_ICONS = [
  // 餐饮
  'mdi-food',
  'mdi-food-variant',
  'mdi-food-apple',
  'mdi-bread-slice',
  'mdi-cake',
  'mdi-coffee',
  'mdi-cup-water',
  'mdi-silverware-fork-knife',
  'mdi-beer',
  // 交通
  'mdi-bus',
  'mdi-train',
  'mdi-subway-variant',
  'mdi-taxi',
  'mdi-car',
  'mdi-bicycle',
  'mdi-airplane',
  'mdi-fuel',
  'mdi-gas-station',
  // 购物
  'mdi-cart',
  'mdi-cart-plus',
  'mdi-shopping',
  'mdi-store',
  'mdi-tshirt-crew',
  'mdi-shoe-sneaker',
  'mdi-laptop',
  'mdi-camera',
  // 居住
  'mdi-home',
  'mdi-home-variant',
  'mdi-home-city',
  'mdi-key-variant',
  'mdi-lock',
  'mdi-lightbulb',
  'mdi-water',
  'mdi-washing-machine',
  // 日用
  'mdi-broom',
  'mdi-package',
  'mdi-package-variant-closed',
  'mdi-cash-register',
  'mdi-tag-multiple',
  // 娱乐
  'mdi-gamepad',
  'mdi-movie',
  'mdi-music',
  'mdi-headphones',
  'mdi-poker-chip',
  'mdi-soccer',
  'mdi-flower',
  'mdi-book-open',
  // 医疗
  'mdi-hospital-box',
  'mdi-hospital',
  'mdi-medical-bag',
  'mdi-pill',
  'mdi-stethoscope',
  'mdi-tooth',
  // 教育
  'mdi-school',
  'mdi-book',
  'mdi-pencil',
  'mdi-calculator',
  // 通讯
  'mdi-cellphone',
  'mdi-message-text',
  'mdi-email',
  'mdi-phone',
  'mdi-wifi',
  'mdi-web',
  // 人情
  'mdi-gift',
  'mdi-heart',
  'mdi-account-heart',
  'mdi-party-popper',
  'mdi-handshake',
  'mdi-account-group',
  // 旅行
  'mdi-bag-suitcase',
  'mdi-bag-suitcase-outline',
  'mdi-airplane-takeoff',
  'mdi-map-marker',
  'mdi-passport',
  'mdi-tent',
  // 工资 / 收入
  'mdi-wallet',
  'mdi-wallet-outline',
  'mdi-cash',
  'mdi-cash-plus',
  'mdi-cash-minus',
  'mdi-cash-multiple',
  'mdi-bank',
  'mdi-receipt',
  'mdi-receipt-text',
  // 理财
  'mdi-finance',
  'mdi-chart-line',
  'mdi-chart-bar',
  'mdi-piggy-bank',
  'mdi-percent',
  'mdi-cash-refund',
  'mdi-credit-card-outline',
  // 副业
  'mdi-briefcase',
  'mdi-briefcase-outline',
  'mdi-account-tie',
  'mdi-hammer-screwdriver',
  'mdi-printer',
  // 退款 / 冲正
  'mdi-bank-remove',
  'mdi-cash-remove',
  'mdi-repeat',
  // 通用票据 / 通用
  'mdi-circle',
  'mdi-circle-outline',
  'mdi-star',
  'mdi-star-outline',
  'mdi-help-circle-outline',
  'mdi-shield-outline',
  'mdi-label-outline',
  'mdi-text-box-outline',
  'mdi-invoice',
]
