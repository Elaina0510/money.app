<template>
  <AppDialog :model-value="modelValue" max-width="480" @update:model-value="$emit('update:modelValue', $event)">
    <!--
      v1.4.4 M3（REQ-006 / D5）三段式钳高：卡片 `.mapping-card` 整体 ≤90vh，内部三段——
      ① 标题区固定不滚、② `.mapping-body` 唯一纵向滚动段、③ 底部操作区固定恒见。
      `rounded="xl"` 系被 global.scss 压至弹层 20px 的**遗留属性**（ui-design 审查裁定：
      不移除、也不依赖其圆角值）；`pa-4` 保留。
    -->
    <v-card class="mapping-card pa-4" rounded="xl">
      <!-- ① 标题区：原 v-card-title + 格式/记录数 caption，原样移出平铺层，固定不滚 -->
      <div>
        <v-card-title class="text-h6 pa-0 mb-2">CSV 导入映射</v-card-title>

        <div class="text-caption text-grey mb-4">
          格式：{{ formatLabel }} · 共 {{ previewData?.row_count || 0 }} 条记录
        </div>
      </div>

      <!--
        ② 中段：现有全部映射内容（区块一/二 + 分类映射 + 标签映射 + 未映射计数 + 缺项清单）
        整体搬入，是卡片内**唯一**纵向滚动段。`tabindex="0"` = 键盘可聚焦滚动容器
        （ui-design 十四章，2026-09-28 审查轮补口径）；除此之外本容器不加任何样式类。
      -->
      <div class="mapping-body" tabindex="0">
        <!--
          ── 区块一「来源与列」（v1.4.3-boot3 设计 §4.2.1）──────────────────────────
          v-if 绑 previewData?.columns：SQL 弹窗复用同组件时响应里本来就没有该字段
          → 整块隐藏，观感与 v1.4.3 一致（设计 §4.3 红线）。字段名逐字取 §1.2.5 冻结契约。
        -->
        <div v-if="previewData?.columns" class="mb-4">
          <div class="text-subtitle-2 font-weight-bold mb-2">来源与列</div>
          <!-- D29：container 由 M6 落地，M1 期缺席属合法 → 仅 xlsx 时追加一行 caption -->
          <div v-if="previewData?.container === 'xlsx'" class="text-caption text-grey mb-1">Excel 工作表</div>
          <div v-if="encodingText" class="text-caption text-grey mb-1">{{ encodingText }}</div>
          <div v-if="ignoredHeaderRows > 0" class="text-caption text-grey mb-1">
            已忽略 {{ ignoredHeaderRows }} 行账单说明文字
          </div>
          <div v-for="warning in (previewData?.warnings || [])" :key="warning" class="text-caption text-warning mb-1">
            {{ warning }}
          </div>

          <!-- 列角色表：初值取后端建议 columns[].role；用户改动不回写 previewData -->
          <div v-for="col in previewData.columns" :key="col.index" class="mb-2">
            <div class="d-flex align-center">
              <span class="text-body-2 mr-2 column-name">{{ columnHeader(col) }}</span>
              <v-icon size="small" class="mr-2">mdi-arrow-right</v-icon>
              <v-select
                class="flex-grow-1"
                :model-value="columnRoles[col.index] ?? null"
                transition="fab-transition"
                :items="roleOptions"
                item-title="label"
                item-value="value"
                density="compact"
                hide-details
                variant="outlined"
                @update:model-value="setColumnRole(col.index, $event)"
              />
            </div>
            <div class="text-caption text-grey column-sample">样例：{{ col.sample || '—' }}</div>
          </div>

          <!-- 样例行：表头行 + sample_rows 前 5 行；窄屏横向滚动，数字等宽 -->
          <div class="text-caption text-grey mb-1">样例行</div>
          <div class="sample-scroll mb-1">
            <table v-if="sampleRows.length > 0" class="sample-table">
              <thead>
                <tr>
                  <th v-for="(h, i) in (previewData?.headers || [])" :key="`head-${i}`">{{ headerText(h, i) }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, ri) in sampleRows" :key="`row-${ri}`">
                  <td v-for="(cell, ci) in row" :key="`cell-${ri}-${ci}`" class="text-no-wrap">{{ cell || '—' }}</td>
                </tr>
              </tbody>
            </table>
            <div v-else class="text-caption text-grey">无数据行</div>
          </div>
        </div>

        <!--
          ── 区块二「收支与默认分类」：同一 v-if 绑 previewData?.columns，
          SQL 复用路径整块隐藏（收支由后端按既有语义推导，请求体不新增字段）。
        -->
        <div v-if="previewData?.columns" class="mb-4">
          <div class="text-subtitle-2 font-weight-bold mb-2">收支与默认分类</div>
          <div class="text-caption text-grey mb-2">{{ typeSourceCaption }}</div>
          <v-radio-group
            :model-value="typeSource"
            density="compact"
            hide-details
            @update:model-value="setTypeSource($event)"
          >
            <v-radio
              v-for="opt in typeSourceOptions"
              :key="opt.value"
              :value="opt.value"
              :label="opt.label"
              color="primary"
            />
          </v-radio-group>
          <div v-if="typeSourceHint" class="text-caption text-warning mb-2">{{ typeSourceHint }}</div>

          <!-- v1.4.4（后端 V3）：分类链尾恒有兜底（映射→归入→自动匹配→「其他」）→
               「账单归入」自本版本起是**可选项**：不计入 missingRequired，不选即交给后端。 -->
          <div v-if="showFallbackCategory" class="mt-2">
            <div class="d-flex align-center">
              <span class="text-body-2 mr-2" style="min-width: 80px">账单归入</span>
              <v-select
                class="flex-grow-1"
                :model-value="fallbackCategoryId"
                transition="fab-transition"
                :items="fallbackCategoryOptions"
                item-title="label"
                item-value="value"
                placeholder="请选择分类"
                density="compact"
                hide-details
                variant="outlined"
                @update:model-value="setFallbackCategory($event)"
              />
            </div>
            <div class="text-caption text-grey mt-1">不选时自动匹配，匹配不到归入其他</div>
          </div>
        </div>

        <!-- Category Mapping -->
        <div class="mb-4">
          <div class="text-subtitle-2 font-weight-bold mb-2">分类映射</div>
          <!-- v1.4.4（后端 V3）：跳过不再等于丢行——后端分类链恒有兜底，未命中的行自动匹配、
               仍匹配不到即挂「其他」。选项文案不改（用例 10.5 逐字锁），语义在此说明。 -->
          <div v-if="hasColumns" class="text-caption text-grey mb-2">
            自动匹配到的已替你选好；留「跳过」即交给后端自动匹配，匹配不到归入其他
          </div>
          <div v-for="catName in (previewData?.categories_in_file || [])" :key="catName" class="mb-2">
            <div class="d-flex align-center">
              <span class="text-body-2 mr-2" style="min-width: 80px">{{ catName }}</span>
              <v-icon size="small" class="mr-2">mdi-arrow-right</v-icon>
              <v-select
                :model-value="getCategoryMapping(catName)"
                transition="fab-transition"
                :items="categoryOptions"
                item-title="label"
                item-value="value"
                density="compact"
                hide-details
                variant="outlined"
                @update:model-value="setCategoryMapping(catName, $event)"
              />
            </div>
            <!--
              v1.4.4 M3（REQ-007 / D10）：选「+ 新建分类」→ 该行**下方**内联名称输入，
              预填文件内原分类名；不改名即按预填值建类（载荷不带 name，见 handleConfirm）。
              报错走行下 `text-caption text-error`（弹窗内可见、不依赖 toast，§4.3）。
              元素口径登记：本文件的既有红线（boot3 用例 M4-9「模板内 Vuetify 标签集合封闭」）
              把 `v-*` 标签锁死为七件套 → 名称输入以**原生 `<input>`** 承载、观感由下方
              scoped 样式对齐 dialog 内 compact 控件（引 `v-text-field` 会让那条既有断言变红）。
            -->
            <div v-if="isCreateRow(catName)" class="create-name-row mt-1">
              <input
                v-model="categoryMapping[catName].name"
                class="create-name-input"
                type="text"
                :placeholder="catName"
                :aria-label="`新建分类名称（原分类：${catName}）`"
                @input="markCreateNameTouched(catName)"
              />
              <div v-if="createNameErrors[catName]" class="text-caption text-error mt-1">
                {{ createNameErrors[catName] }}
              </div>
            </div>
          </div>
        </div>

        <!-- Tag Mapping -->
        <div v-if="(previewData?.tags_in_file || []).length > 0" class="mb-4">
          <div class="text-subtitle-2 font-weight-bold mb-2">标签映射</div>
          <div v-for="tagName in (previewData?.tags_in_file || [])" :key="tagName" class="mb-2">
            <div class="d-flex align-center">
              <span class="text-body-2 mr-2" style="min-width: 80px">{{ tagName }}</span>
              <v-icon size="small" class="mr-2">mdi-arrow-right</v-icon>
              <v-select
                :model-value="getTagMapping(tagName)"
                transition="fab-transition"
                :items="tagOptions"
                item-title="label"
                item-value="value"
                density="compact"
                hide-details
                variant="outlined"
                @update:model-value="setTagMapping(tagName, $event)"
              />
            </div>
          </div>
        </div>

        <!-- Unmapped count -->
        <div class="text-caption text-grey mb-4">
          <span v-if="unmappedCount > 0" class="text-error">
            未映射：{{ unmappedCount }} 项
          </span>
          <span v-else class="text-success">全部已映射</span>
        </div>

        <!--
          缺项清单：确认按钮禁用时在按钮上方给出中文原因（不新增 toast，设计 U3/§4.2.2）。
          v1.4.4 M3：这里**只**列必需列缺项——新建分类重名报错改在**行下**就地展示（§4.3），
          两者共用同一个禁用条件（见 missingRequiredCount）。
        -->
        <div v-if="missingRequired.length > 0" class="mb-4">
          <div v-for="item in missingRequired" :key="item" class="text-caption text-error">
            {{ item }}
          </div>
        </div>
      </div>

      <!--
        ③ 底部操作区：**在 `.mapping-body` 之外**（故不参与滚动、固定恒见，REQ-006 验收），
        位置与两钮语义不变；`:disabled` 表达式逐字保留（boot3 §4.2 禁用条件并列口径），
        M3 的新建名重名报错经 missingRequiredCount 计入同一条件（不新增第四个数）。
      -->
      <div class="d-flex justify-end ga-2">
        <v-btn variant="text" @click="$emit('update:modelValue', false)">取消</v-btn>
        <v-btn
          color="primary"
          variant="tonal"
          :disabled="unmappedCount > 0 || missingRequiredCount > 0"
          @click="handleConfirm"
        >
          确认导入
        </v-btn>
      </div>
    </v-card>
  </AppDialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import AppDialog from './AppDialog.vue'

const props = defineProps({
  modelValue: Boolean,
  previewData: Object,
  categories: Array,
})

const emit = defineEmits(['update:modelValue', 'confirm'])

// ── 契约常量（字段名/取值逐字取设计 §1.2.5 与 §3.2，禁止实现期自造）──────────
// D18 的六值方言封闭集；SQL 预览的 sqlite_binary / text_sql 不在集内 → 落兜底「未知格式」
const FORMAT_LABELS = {
  native: '本系统格式',
  cashew: 'Cashew 格式',
  cashew_template: 'Cashew 模板',
  alipay: '支付宝账单',
  wechat: '微信账单',
  custom: '手动映射',
}

// D3 的六个列角色（同为封闭集）+「不导入」（值为 null）
const ROLE_LABELS = {
  amount: '金额',
  type: '收/支',
  category: '分类',
  tag: '标签',
  consume_time: '时间',
  note: '备注',
}
const roleOptions = [{ label: '不导入', value: null }].concat(
  Object.keys(ROLE_LABELS).map((role) => ({ label: ROLE_LABELS[role], value: role }))
)

// D10 的 type_source 四态
const TYPE_SOURCE_OPTIONS = [
  { value: 'column', label: '按收/支列' },
  { value: 'sign', label: '按金额正负' },
  { value: 'all_expense', label: '全部支出' },
  { value: 'all_income', label: '全部收入' },
]
// 区块二顶部的口径说明（§3.5）：随选项切换而变。column 一栏写死「不回落」口径（D10）
const TYPE_SOURCE_CAPTIONS = {
  column: '按「收/支」列的值逐行判定；该行不可判时跳过，不回落为按金额正负',
  sign: '金额负数记为支出、正数记为收入，0 记为支出',
  all_expense: '整表一律记为支出',
  all_income: '整表一律记为收入',
}

const categoryMapping = ref({})
const tagMapping = ref({})

// v1.4.3-boot3：列索引 → 用户手选的列角色（初值取后端建议，改动不回写 previewData）
const columnRoles = ref({})
const typeSource = ref(null)
const fallbackCategoryId = ref(null)
const typeSourceHint = ref('')

const formatLabel = computed(() => {
  return FORMAT_LABELS[props.previewData?.format] || '未知格式'
})

const hasColumns = computed(() => Array.isArray(props.previewData?.columns))

const ignoredHeaderRows = computed(() => Number(props.previewData?.header_row_index) || 0)

// encoding 在 xlsx 通道按设计取字符串 "xlsx"（该通道无字符编码可言）→ 不重复展示
const encodingText = computed(() => {
  const encoding = props.previewData?.encoding
  if (!encoding || encoding === 'xlsx') return ''
  return `文件编码：${encoding}`
})

const sampleRows = computed(() => (props.previewData?.sample_rows || []).slice(0, 5))

// 角色 → 列索引：v1.4.4 V2 起 **`note` 可来自多列**（微信 `交易对方` + `商品`、
// 支付宝 `交易对方` + `商品说明`），收成**升序 int 数组**；其余角色沿用「先列独占」
// （两列选同一非 note 角色时前端不阻止、不报错，载荷取靠前列，与后端 D3 同口径，
// 设计 §4.3）。单列 note 仍发 `int`——后端 `_indexes()` 两型通吃（D18 向后兼容）。
const roleColumns = computed(() => {
  const map = {}
  const noteIndexes = []
  for (const col of (props.previewData?.columns || [])) {
    // 已手选（含「不导入」= null）一律以手选为准；仅未初始化的列才退回后端建议 role
    const chosen = col.index in columnRoles.value
    const role = chosen ? columnRoles.value[col.index] : (col.role ?? null)
    if (!role) continue
    if (role === 'note') {
      noteIndexes.push(col.index)
      continue
    }
    if (map[role] === undefined) map[role] = col.index
  }
  if (noteIndexes.length > 0) {
    map.note = noteIndexes.length > 1 ? [...noteIndexes].sort((a, b) => a - b) : noteIndexes[0]
  }
  return map
})

const typeSourceOptions = computed(() =>
  TYPE_SOURCE_OPTIONS.filter((opt) => opt.value !== 'column' || roleColumns.value.type !== undefined)
)

const typeSourceCaption = computed(() => TYPE_SOURCE_CAPTIONS[typeSource.value] || '')

// v1.4.4（后端 V3）：文件内无分类列时「账单归入」**仍出现**，但自此是**可选项**
// （见下方 missingRequired：不再计入禁用条件）；有分类列则整行不渲染
const showFallbackCategory = computed(() => hasColumns.value && roleColumns.value.category === undefined)

const fallbackCategoryOptions = computed(() =>
  (props.categories || []).map((cat) => ({ label: cat.name, value: cat.id }))
)

// 缺项明细（§4.2.2）：与 unmappedCount 并列作为禁用条件。
// v1.4.4 摘掉「未识别到分类列：请选择账单归入」那一条——后端分类链尾恒有「其他」兜底、
// `category_unresolved` 恒 0，必选已无依据（用户裁定 V3），故只剩两个必需列。
const missingRequired = computed(() => {
  if (!hasColumns.value) return []
  const items = []
  if (roleColumns.value.amount === undefined) items.push('缺少「金额」列：请为某一列指定金额角色')
  if (roleColumns.value.consume_time === undefined) items.push('缺少「时间」列：请为某一列指定时间角色')
  return items
})

// ── v1.4.4 M3（REQ-007 / D10）：新建分类自定义名的行内状态与实时校验 ──────────────
// 状态形状：`categoryMapping[catName] = { action: 'create', name, _touched }`——
// `name` 在选「+ 新建分类」时**预填文件内原分类名**，`_touched` 是**纯本地**标记，
// 两者都不直接出网（见 `handleConfirm`：编辑过且去空白后非空才带 `name`）。
function isCreateRow(catName) {
  return categoryMapping.value[catName]?.action === 'create'
}

function markCreateNameTouched(catName) {
  const item = categoryMapping.value[catName]
  if (!item || item.action !== 'create') return
  item._touched = true
}

function trimmedCreateName(value) {
  return String(value ?? '').trim()
}

// 校验三态（§4.3，实时、弹窗内可见、不依赖 toast）：
//   ① 去空白后为空 → 视为未改名：不报错、不发 `name`、按预填值建类；
//   ② 与本批其他新建名重复（两侧去空白、大小写精确比较）→「与本次新建的其他分类重名」；
//   ③ 与 `props.categories` 现有可见分类名重复 →「分类「X」已存在，请换一个名称」。
// ②③ 计入禁用条件 →「确认导入」置灰（见下方 missingRequiredCount）。
const createNameErrors = computed(() => {
  const errors = {}
  const rows = []
  for (const catName of (props.previewData?.categories_in_file || [])) {
    const item = categoryMapping.value[catName]
    if (!item || item.action !== 'create' || !item._touched) continue
    const name = trimmedCreateName(item.name)
    if (!name) continue
    rows.push({ catName, name })
  }
  rows.forEach((row, index) => {
    if (rows.some((other, i) => i !== index && other.name === row.name)) {
      errors[row.catName] = '与本次新建的其他分类重名'
      return
    }
    if ((props.categories || []).some((cat) => cat.name === row.name)) {
      errors[row.catName] = `分类「${row.name}」已存在，请换一个名称`
    }
  })
  return errors
})

// 禁用条件计数（§4.2「并列」口径 + M3 §4.3「报错计入禁用条件」）：
// = 必需列缺项 + 新建名重名报错。名字沿用 `missingRequiredCount`，是为保住模板里既有的
// 逐字断言 `:disabled="unmappedCount > 0 || missingRequiredCount > 0"`（boot3 用例 M4-9，
// 本批不触碰该测试文件）。缺项清单本身仍只渲染 `missingRequired`（列缺项），
// 新建名报错在**该行下方**就地展示，不在底部重复一份。
const missingRequiredCount = computed(
  () => missingRequired.value.length + Object.keys(createNameErrors.value).length
)

const categoryOptions = computed(() => {
  const options = [{ label: '— 跳过 —', value: null }]
  for (const cat of (props.categories || [])) {
    // v1.4.3 M8：分类收支共用，label 去掉「(支出/收入)」后缀
    options.push({ label: cat.name, value: cat.id })
  }
  options.push({ label: '+ 新建分类', value: 'create' })
  return options
})

const tagOptions = computed(() => {
  const options = [{ label: '— 跳过 —', value: null }]
  for (const cat of (props.categories || [])) {
    options.push({ label: `新建于「${cat.name}」`, value: cat.id })
  }
  return options
})

const unmappedCount = computed(() => {
  let count = 0
  for (const catName of (props.previewData?.categories_in_file || [])) {
    const mapping = categoryMapping.value[catName]
    if (!mapping || (!mapping.target_id && mapping.action !== 'create')) {
      count++
    }
  }
  return count
})

// 空列名（支付宝表头尾随逗号，设计 §1.2.6）显示为「第 N 列（空列名）」
function headerText(header, index) {
  const text = header == null ? '' : String(header)
  if (text.trim() === '') return `第 ${Number(index) + 1} 列（空列名）`
  return text
}

function columnHeader(col) {
  return headerText(col?.header, col?.index ?? 0)
}

function setColumnRole(index, role) {
  columnRoles.value[index] = role ?? null
  // §3.2：收支列被改成「不导入」→ 回落为按金额正负，并在卡片内提示（不弹 toast）
  if (typeSource.value === 'column' && roleColumns.value.type === undefined) {
    typeSource.value = 'sign'
    typeSourceHint.value = '「收/支」列已改为不导入，收支判定已回落为按金额正负'
  }
}

function setTypeSource(value) {
  if (value == null) return
  typeSource.value = value
  typeSourceHint.value = ''
}

function setFallbackCategory(value) {
  fallbackCategoryId.value = value ?? null
}

function getCategoryMapping(catName) {
  const m = categoryMapping.value[catName]
  if (!m) return null
  if (m.action === 'create') return 'create'
  return m.target_id
}

function setCategoryMapping(catName, value) {
  if (value === null) {
    delete categoryMapping.value[catName]
  } else if (value === 'create') {
    // M8：新建分类不再携带 type（服务端写占位值）
    // v1.4.4 M3（§4.1/§4.2）：同时预填**文件内原分类名**给行下输入框，并置本地 `_touched`
    // 为 false——载荷仍由 `handleConfirm` 决定，未编辑时与旧版逐字一致（D10）。
    categoryMapping.value[catName] = { action: 'create', name: catName, _touched: false }
  } else {
    categoryMapping.value[catName] = { action: 'map', target_id: value }
  }
}

function getTagMapping(tagName) {
  const m = tagMapping.value[tagName]
  if (!m) return null
  if (m.action === 'create') return m.category_id
  return m.target_id || null
}

function setTagMapping(tagName, value) {
  if (value === null) {
    delete tagMapping.value[tagName]
  } else {
    // value is a category_id, use action='create' to create tag under that category
    tagMapping.value[tagName] = { action: 'create', category_id: value }
  }
}

// v1.4.4 M3（REQ-007 / D10）：出网载荷在此**统一裁剪**——
//   ① `_touched` 是纯本地标记，永不发往后端；
//   ② `name` 只在「用户编辑过行下输入框」且「去空白后非空」时才带上；
//   ③ 未编辑（或清空）→ 该 key 仍为 `{ action: 'create' }`，与旧版载荷**逐字一致**
//      （回归锚：boot3 用例 10.5 `toEqual({ action: 'create' })` 且 not.toHaveProperty('type')）；
//   ④ `map` 行原样透传，`fallback_category` / SQL 路径的请求体键集不受影响（§4.4）。
// `name` 发**用户原输入**（含首尾空白）——清洗与「空即回退文件内原分类名」是服务层的职责。
function buildCategoryMappingPayload() {
  const payload = {}
  for (const [catName, item] of Object.entries(categoryMapping.value)) {
    if (!item || item.action !== 'create') {
      payload[catName] = { ...item }
      continue
    }
    if (item._touched && trimmedCreateName(item.name)) {
      payload[catName] = { action: 'create', name: item.name }
    } else {
      payload[catName] = { action: 'create' }
    }
  }
  return payload
}

function handleConfirm() {
  const payload = {
    category_mapping: buildCategoryMappingPayload(),
    tag_mapping: { ...tagMapping.value },
  }
  // 区块隐藏（SQL 弹窗复用）时三字段整体不写入 → SQL 请求体一字不变（§4.4）。
  // `columns.note` 两列及以上时为**升序 int 数组**、单列仍是 int（V2 / D18）；
  // `fallback_category` 自此**只在用户真选了才发**（V3 降级为可选项，不选即交给后端兜底）。
  if (hasColumns.value) {
    payload.columns = { ...roleColumns.value }
    payload.type_source = typeSource.value
    if (showFallbackCategory.value && fallbackCategoryId.value != null) {
      payload.fallback_category = { action: 'map', target_id: fallbackCategoryId.value }
    }
  }
  emit('confirm', payload)
}

// 列角色与收支口径初值：与下方既有同名预映射 watch 并列，各自负责一段（§4.5 零改动）
watch(() => props.previewData, (data) => {
  const roles = {}
  for (const col of (data?.columns || [])) {
    roles[col.index] = col.role ?? null
  }
  columnRoles.value = roles
  typeSource.value = data?.suggested_type_source ?? null
  // 初值口径自检：建议为 column 但表内无收支列 → 直接按 sign 呈现（不给无效选项）
  if (typeSource.value === 'column' && !Object.values(roles).includes('type')) {
    typeSource.value = 'sign'
  }
  fallbackCategoryId.value = null
  typeSourceHint.value = ''
}, { immediate: true })

// 区块三的初值（v1.4.4）：**首选**后端 `categories_suggested`——它就是落库层
// `_match_category_auto` 的同一份结果（同名 / 双向包含 / 同义词三档），前端照抄即
// 「预览所见 == 导入所得」。建议 id 不在可见分类里（如被用户同名副本遮蔽的预设行）
// 即不预选，退回既有的「按 name 命中即映射」；两者都落空 → 留「— 跳过 —」，
// 由后端链尾的「自动匹配 → 其他」兜底（不再丢行）。
watch(() => props.previewData, (data) => {
  if (!data) return
  const cats = props.categories || []
  const suggested = data.categories_suggested || {}
  for (const catName of (data.categories_in_file || [])) {
    const suggestedId = suggested[catName]
    if (suggestedId != null && cats.some((c) => c.id === suggestedId)) {
      categoryMapping.value[catName] = { action: 'map', target_id: suggestedId }
      continue
    }
    const match = cats.find((c) => c.name === catName)
    if (match) {
      categoryMapping.value[catName] = { action: 'map', target_id: match.id }
    }
  }
}, { immediate: true })
</script>

<style scoped>
/*
  ── v1.4.4 M3（REQ-006 / D5）三段式钳高：设计 §4.1 定值，逐字落地 ──────────────
  卡片自身 ≤90vh（不动 AppDialog 壳，展开动画零影响）；头/尾固定，中段唯一滚动。
  内容短于 90vh 时卡片随内容收缩（v-card 无 height，max-height 天然不留白）。
*/
.mapping-card {
  display: flex;
  flex-direction: column;
  max-height: 90vh;
}

/* 唯一纵向滚动段：min-height: 0 是 flex 子项能真正收缩的前提；横向不引入滚动条 */
.mapping-body {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
}

/*
  新建分类的自定义名输入（§4.2）：原生 <input>（口径见模板注释），
  观感对齐同排 compact / outlined 的 v-select——1px 描边、4px 圆角、14px 字号。
  不写 `outline: none`：焦点环由 global.scss 的 `*:focus-visible` 统一供给。
*/
.create-name-row {
  /* 向右缩进到下拉那一列附近（80px 名 + 右箭头），不改上方行结构 */
  padding-left: 96px;
}

.create-name-input {
  width: 100%;
  max-width: 260px;
  padding: 6px 12px;
  font: inherit;
  font-size: 14px;
  line-height: 1.25;
  color: rgb(var(--v-theme-on-surface));
  background: transparent;
  border: 1px solid rgba(var(--v-theme-on-surface), 0.28);
  border-radius: 4px;
}

.create-name-input::placeholder {
  color: rgba(var(--v-theme-on-surface-variant), 0.6);
}

/* 列名与样例值同属信息展示：单行截断，避免长表头/长单号把角色下拉挤出可视区 */
.column-name {
  min-width: 96px;
  max-width: 45%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.column-sample {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 样例行表格：列数可达 17（Cashew 全量导出）→ 窄弹窗内横向滚动，单元格不折行 */
.sample-scroll {
  overflow-x: auto;
}

.sample-table {
  border-collapse: collapse;
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}

.sample-table th,
.sample-table td {
  padding: 2px 8px 2px 0;
  text-align: left;
  white-space: nowrap;
}

.sample-table th {
  color: rgba(var(--v-theme-on-surface-variant), 0.7);
  font-weight: 600;
}

.sample-table td {
  border-top: 1px solid rgba(var(--v-theme-on-surface), 0.12);
}
</style>
