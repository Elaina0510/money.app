<template>
  <div class="settings-about-page">
    <!-- 页头：返回箭头 + 标题（与其他设置系二级页同款结构） -->
    <div class="d-flex align-center mb-3">
      <v-btn icon variant="text" size="small" class="mr-2" @click="$router.back()">
        <v-icon>mdi-arrow-left</v-icon>
      </v-btn>
      <div class="flex-grow-1">
        <p class="text-body-1 font-weight-medium mb-0">关于</p>
        <p class="text-caption text-grey mb-0">版本与应用介绍</p>
      </div>
    </div>

    <!--
      四个区块（设计 §5.2 / 任务 §3.1–3.5）：卡壳统一挂全局 .page-card，
      区块内节奏挂全局 .section-block / .section-title——本页不新增任何样式体系，
      深浅主题由 --v-theme-* 语义色自动跟随（不写死色值）。
      文案全部本地静态：无网址、无外链、无安装运维指引（REQ-009 验收）。
    -->

    <!-- 区块一 · 应用卡：版本号只读接口，页面内零硬编码版本字面量 -->
    <div class="page-card">
      <div class="section-block">
        <div class="section-title text-caption text-grey font-weight-medium">应用</div>
        <div class="d-flex align-center mb-2">
          <v-avatar size="36" class="entry-avatar mr-2">
            <v-icon color="primary" size="20">mdi-cash-register</v-icon>
          </v-avatar>
          <div>
            <div class="text-body-1 font-weight-medium">Money App · 个人记账</div>
            <!-- 版本取不到（接口失败/无 data）→ 整行不渲染，不留占位错字 -->
            <div v-if="version" class="text-caption text-grey">版本 {{ version }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 区块二 · 核心优势：5 条（任务审查轮 T1 定稿，「快速记账模板」并入首条，不扩写） -->
    <div class="page-card">
      <div class="section-block">
        <div class="section-title text-caption text-grey font-weight-medium">核心优势</div>
        <ul class="about-list">
          <li v-for="item in advantages" :key="item" class="text-body-2">{{ item }}</li>
        </ul>
      </div>
    </div>

    <!-- 区块三 · 独特功能：多来源账单导入 + 分类兜底链 + 数据回溯可撤销 -->
    <div class="page-card">
      <div class="section-block">
        <div class="section-title text-caption text-grey font-weight-medium">独特功能</div>
        <ul class="about-list">
          <li v-for="item in features" :key="item" class="text-body-2">{{ item }}</li>
        </ul>
      </div>
    </div>

    <!-- 区块四 · 技术实现（白话，面向使用者视角） -->
    <div class="page-card">
      <div class="section-block">
        <div class="section-title text-caption text-grey font-weight-medium">
          技术实现（白话）
        </div>
        <ul class="about-list">
          <li v-for="item in techNotes" :key="item" class="text-body-2">{{ item }}</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getAppVersion } from '@/api/version'

// 版本号唯一来源 = 后端 GET /api/version（真值在 backend/app/constants.py）。
// 本文件不出现任何版本号字面量，也不出现网址与部署字样（任务 §3.2 红线）。
const version = ref('')

// 核心优势 5 条：措辞以设计 §5.2 原文为源只做拼接（「快速记账模板」并入首条），不扩写
const advantages = [
  '收支一笔记全（金额/分类/标签/备注/消费时间），相同账单记 2 次自动纳入快速记账模板',
  '预设+自定义分类与标签双维度',
  '月度预算与分类预算盯进度',
  '统计看板（分类柱状、月度趋势、预算概览）',
  '多人各记各的（数据按登录用户隔离）',
]

// 独特功能（设计 §5.2 区块三逐字）
const features = [
  '多来源账单导入——CSV/Excel/SQL 直传，支付宝/微信/Cashew 导出文件自动识别格式，识别不了可逐列手动指认',
  '分类对不上有兜底链「映射→归入→自动匹配→其他」，一行不丢',
  '数据回溯可撤销',
]

// 技术实现白话（设计 §5.2 区块四逐字）
const techNotes = [
  '数据存在你自己部署的服务器上，不经过任何第三方',
  '导入不怕格式不对（认不出来就手动指认，实在对不上归类兜底不丢账）',
  '全应用单文件数据库，备份即拷一个文件',
]

async function loadVersion() {
  try {
    version.value = (await getAppVersion()) || ''
  } catch (e) {
    // 接口失败 → 版本行整行不渲染（v-if 兜住空串），不留占位、不打扰用户
    console.error('Load app version error:', e)
    version.value = ''
  }
}

onMounted(loadVersion)
</script>

<style scoped>
/* 只补本页列表的排版（无新色值、无新间距体系：字号/行高走 Vuetify 语义类，
   区块节奏与卡片图层全部复用 global.scss 既有 .page-card/.section-block/.section-title） */
.about-list {
  margin: 0;
  padding-left: 20px;
  line-height: 1.8;
}

.about-list li + li {
  margin-top: 4px;
}
</style>
