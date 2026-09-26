<template>
  <section class="page">
    <header class="page-head">
      <div>
        <h2>运营概览</h2>
        <p class="page-desc">汇总各业务模块的关键指标，先看总量再看异常。</p>
      </div>
    </header>
    <div class="stat-row">
      <article v-for="card in cards" :key="card.label" class="stat-card">
        <span class="stat-label">{{ card.label }}</span>
        <strong class="stat-value">{{ card.value }}</strong>
      </article>
    </div>
    <table class="data-table">
      <thead>
        <tr><th>业务模块</th><th>今日新增</th><th>待处理</th><th>异常量</th></tr>
      </thead>
      <tbody>
        <tr v-for="row in moduleRows" :key="row.name">
          <td>{{ row.name }}</td>
          <td>{{ row.created }}</td>
          <td>{{ row.pending }}</td>
          <td>{{ row.abnormal }}</td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { fetchJson } from '@/api/client'

type Overview = {
  cards: { label: string; value: number }[]
  modules: { name: string; created: number; pending: number; abnormal: number }[]
}

const cards = ref<Overview['cards']>([])
const moduleRows = ref<Overview['modules']>([])

onMounted(async () => {
  try {
    const payload = await fetchJson<Overview>('/api/overview')
    cards.value = payload.cards
    moduleRows.value = payload.modules
  } catch {
    cards.value = [{"label": "业务模块", "value": 0}, {"label": "今日新增", "value": 0}]
    moduleRows.value = [{"name": "机位分配", "created": 0, "pending": 0, "abnormal": 0}, {"name": "引导入位", "created": 0, "pending": 0, "abnormal": 0}, {"name": "廊桥对接", "created": 0, "pending": 0, "abnormal": 0}, {"name": "行李装卸", "created": 0, "pending": 0, "abnormal": 0}, {"name": "航食配餐", "created": 0, "pending": 0, "abnormal": 0}, {"name": "航油加注", "created": 0, "pending": 0, "abnormal": 0}, {"name": "除冰作业", "created": 0, "pending": 0, "abnormal": 0}, {"name": "清水排污", "created": 0, "pending": 0, "abnormal": 0}, {"name": "推出开车", "created": 0, "pending": 0, "abnormal": 0}, {"name": "地面设备", "created": 0, "pending": 0, "abnormal": 0}, {"name": "货物装卸", "created": 0, "pending": 0, "abnormal": 0}, {"name": "放行签派", "created": 0, "pending": 0, "abnormal": 0}, {"name": "过站保障", "created": 0, "pending": 0, "abnormal": 0}, {"name": "机坪巡查", "created": 0, "pending": 0, "abnormal": 0}, {"name": "航空气象", "created": 0, "pending": 0, "abnormal": 0}, {"name": "特种车辆", "created": 0, "pending": 0, "abnormal": 0}, {"name": "人员排班", "created": 0, "pending": 0, "abnormal": 0}, {"name": "跑道灯光", "created": 0, "pending": 0, "abnormal": 0}, {"name": "应急处置", "created": 0, "pending": 0, "abnormal": 0}, {"name": "质量监察", "created": 0, "pending": 0, "abnormal": 0}]
  }
})
</script>
