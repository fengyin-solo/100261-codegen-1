<template>
  <section class="page" data-module="shuttlebus">
    <header class="page-head">
      <div>
        <h2>摆渡车调度</h2>
        <p class="page-desc">按上车人数与旅客等待时长判定发车；等待超阈值先处置，等待数据缺失挂待确认，可用车低于当天需求下限不许排新趟次。</p>
      </div>
      <div class="page-actions">
        <button class="btn primary" type="button" @click="toggleCreate">登记新趟次</button>
        <button class="btn" type="button" @click="exportRows">导出当天发车清单</button>
      </div>
    </header>

    <div class="stat-row">
      <article v-for="item in stats" :key="item.label" class="stat-card">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <div class="stat-row">
      <article v-for="item in standards" :key="item.航站楼" class="stat-card">
        <span class="stat-label">{{ item.航站楼 }} 发车标准</span>
        <strong class="standard-value">
          满 {{ item.最小发车人数 }} 人 · 等 {{ item.等待阈值分钟 }} 分 · 下限 {{ item.当天需求下限 }} 辆 · 可用 {{ item.可用摆渡车 }} 辆
        </strong>
        <button class="link" type="button" @click="editStandard(item)">调整标准</button>
      </article>
    </div>

    <form v-if="standardForm" class="filter-bar" @submit.prevent="saveStandard">
      <label class="filter-item">
        <span>航站楼</span>
        <input :value="standardForm.航站楼" disabled />
      </label>
      <label v-for="field in standardFields" :key="field" class="filter-item">
        <span>{{ field }}</span>
        <input v-model="standardForm[field]" type="number" min="0" />
      </label>
      <button class="btn primary" type="submit">保存标准</button>
      <button class="btn ghost" type="button" @click="standardForm = null">取消</button>
    </form>

    <form v-if="showCreate" class="filter-bar" @submit.prevent="submitCreate">
      <label class="filter-item">
        <span>趟次编号</span>
        <input v-model="createForm.趟次编号" placeholder="如 SHUT-0007" />
      </label>
      <label class="filter-item">
        <span>航站楼</span>
        <select v-model="createForm.航站楼">
          <option v-for="t in terminals" :key="t" :value="t">{{ t }}</option>
        </select>
      </label>
      <label class="filter-item">
        <span>摆渡车编号</span>
        <input v-model="createForm.摆渡车编号" placeholder="如 BUS-09" />
      </label>
      <label class="filter-item">
        <span>上车人数</span>
        <input v-model="createForm.上车人数" type="number" min="0" />
      </label>
      <label class="filter-item">
        <span>旅客等待时长（分钟，可空）</span>
        <input v-model="createForm.旅客等待时长" type="number" min="0" placeholder="留空则挂待确认" />
      </label>
      <label class="filter-item">
        <span>服务日期</span>
        <input v-model="createForm.服务日期" type="date" />
      </label>
      <button class="btn primary" type="submit">提交登记</button>
      <button class="btn ghost" type="button" @click="showCreate = false">取消</button>
    </form>

    <form class="filter-bar" @submit.prevent="reload">
      <label class="filter-item">
        <span>趟次编号</span>
        <input v-model="filters.keyword" placeholder="按趟次编号检索" />
      </label>
      <label class="filter-item">
        <span>趟次状态</span>
        <select v-model="filters.status">
          <option value="">全部</option>
          <option v-for="s in statuses" :key="s" :value="s">{{ s }}</option>
        </select>
      </label>
      <label class="filter-item">
        <span>航站楼</span>
        <select v-model="filters.terminal">
          <option value="">全部</option>
          <option v-for="t in terminals" :key="t" :value="t">{{ t }}</option>
        </select>
      </label>
      <label class="filter-item">
        <span>服务日期</span>
        <input v-model="filters.date" type="date" />
      </label>
      <button class="btn" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
    </form>

    <table class="data-table">
      <thead>
        <tr>
          <th v-for="column in columns" :key="column">{{ column }}</th>
          <th>可执行动作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="String(row.id)">
          <td v-for="column in columns" :key="column">{{ displayCell(row, column) }}</td>
          <td class="row-actions">
            <button
              v-for="action in rowActions(row)"
              :key="action"
              class="link"
              type="button"
              @click="runAction(action, row)"
            >
              {{ action }}
            </button>
            <span v-if="!rowActions(row).length">—</span>
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td :colspan="columns.length + 1" class="empty-state">暂无摆渡趟次数据，可先登记新趟次</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ total }} 条摆渡趟次记录 · 本批上车人数合计 {{ passengerTotal }} 人</span>
      <span v-if="notice" :class="noticeOk ? 'ok-text' : 'error-text'">{{ notice }}</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { request } from '@/api/client'

type Row = Record<string, string | number | null>
type Standard = {
  航站楼: string
  最小发车人数: number
  等待阈值分钟: number
  当天需求下限: number
  可用摆渡车: number
}

const ENDPOINT = '/api/shuttlebus'
const columns = ['趟次编号', '航站楼', '摆渡车编号', '上车人数', '旅客等待时长', '登记时间', '服务日期', '趟次状态']
const statuses = ['待确认', '待发车', '超时待处置', '已发车', '已取消']
const standardFields = ['最小发车人数', '等待阈值分钟', '当天需求下限', '可用摆渡车'] as const
const today = new Date().toISOString().slice(0, 10)

const rows = ref<Row[]>([])
const total = ref(0)
const passengerTotal = ref(0)
const statusCounts = ref<Record<string, number>>({})
const standards = ref<Standard[]>([])
const notice = ref('')
const noticeOk = ref(true)
const showCreate = ref(false)
const standardForm = ref<Record<string, string> | null>(null)
const emptyCreate = () => ({
  趟次编号: '',
  航站楼: 'T1',
  摆渡车编号: '',
  上车人数: '',
  旅客等待时长: '',
  服务日期: today,
})
const createForm = ref(emptyCreate())
const filters = ref({ keyword: '', status: '', terminal: '', date: today })

const terminals = computed(() => standards.value.map((item) => item.航站楼))

const stats = computed(() => [
  { label: '待发车', value: statusCounts.value['待发车'] ?? 0 },
  { label: '超时待处置', value: statusCounts.value['超时待处置'] ?? 0 },
  { label: '待确认', value: statusCounts.value['待确认'] ?? 0 },
  { label: '本批上车人数合计', value: passengerTotal.value },
])

function displayCell(row: Row, column: string) {
  if (column === '趟次状态') {
    return row.status ?? '—'
  }
  if (column === '旅客等待时长') {
    const wait = row[column]
    return wait === null || wait === undefined || wait === '' ? '缺失' : `${wait} 分钟`
  }
  return row[column] ?? '—'
}

function rowActions(row: Row): string[] {
  const status = String(row.status ?? '')
  if (status === '已发车' || status === '已取消') {
    return []
  }
  const list = ['确认发车']
  if (status === '待确认' || status === '待发车') {
    list.push('补录等待')
  }
  if (status === '超时待处置') {
    list.push('处置超时')
  }
  list.push('取消趟次')
  return list
}

function currentQuery() {
  const params = new URLSearchParams()
  Object.entries(filters.value).forEach(([key, value]) => {
    if (value) {
      params.set(key, value)
    }
  })
  return params.toString()
}

function setNotice(message: string, ok: boolean) {
  notice.value = message
  noticeOk.value = ok
}

function resetFilters() {
  filters.value = { keyword: '', status: '', terminal: '', date: today }
  void reload()
}

function toggleCreate() {
  showCreate.value = !showCreate.value
  if (showCreate.value) {
    createForm.value = emptyCreate()
  }
}

function exportRows() {
  // 与页面同一套筛选条件，清单上的人数合计才能和页面对得上。
  window.open(`${ENDPOINT}/export?${currentQuery()}`, '_blank')
}

function editStandard(item: Standard) {
  standardForm.value = {
    航站楼: item.航站楼,
    最小发车人数: String(item.最小发车人数),
    等待阈值分钟: String(item.等待阈值分钟),
    当天需求下限: String(item.当天需求下限),
    可用摆渡车: String(item.可用摆渡车),
  }
}

async function saveStandard() {
  if (!standardForm.value) {
    return
  }
  const terminal = standardForm.value.航站楼
  try {
    const response = await request(`${ENDPOINT}/standards/${terminal}`, {
      method: 'PUT',
      body: JSON.stringify({ values: standardForm.value }),
    })
    const payload = await response.json()
    setNotice(payload.message ?? '标准已更新', Boolean(payload.ok))
    if (payload.ok) {
      standardForm.value = null
      await loadStandards()
    }
  } catch (error) {
    setNotice(error instanceof Error ? error.message : '标准保存失败', false)
  }
}

async function submitCreate() {
  const values: Record<string, string> = { ...createForm.value }
  if (!values.旅客等待时长) {
    delete values.旅客等待时长
  }
  try {
    const response = await request(ENDPOINT, {
      method: 'POST',
      body: JSON.stringify({ values }),
    })
    const payload = await response.json()
    setNotice(payload.message ?? '登记完成', Boolean(payload.ok))
    if (payload.ok) {
      showCreate.value = false
      await reload()
    }
  } catch (error) {
    setNotice(error instanceof Error ? error.message : '趟次登记失败', false)
  }
}

async function runAction(action: string, row: Row) {
  const values: Record<string, string | number> = { action }
  if (action === '补录等待') {
    const input = window.prompt(`补录趟次 ${row.趟次编号} 的旅客等待时长（分钟）`)
    if (input === null) {
      return
    }
    values.旅客等待时长 = input
  }
  try {
    const response = await request(`${ENDPOINT}/${row.id}/actions`, {
      method: 'POST',
      body: JSON.stringify({ values }),
    })
    const payload = await response.json()
    setNotice(payload.message ?? '动作已执行', Boolean(payload.ok))
    await reload()
  } catch (error) {
    setNotice(error instanceof Error ? error.message : '摆渡车操作失败', false)
  }
}

async function loadStandards() {
  try {
    const response = await request(`${ENDPOINT}/standards`)
    const payload = await response.json()
    standards.value = payload.items ?? []
  } catch (error) {
    setNotice(error instanceof Error ? error.message : '发车标准读取失败', false)
  }
}

async function reload() {
  try {
    const response = await request(`${ENDPOINT}?${currentQuery()}`)
    if (!response.ok) {
      throw new Error('摆渡趟次列表读取失败')
    }
    const payload = await response.json()
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
    passengerTotal.value = payload.passenger_total ?? 0
    statusCounts.value = payload.status_counts ?? {}
  } catch (error) {
    setNotice(error instanceof Error ? error.message : '摆渡趟次列表读取失败', false)
  }
}

onMounted(() => {
  void loadStandards()
  void reload()
})
</script>

<style scoped>
.standard-value {
  display: block;
  font-size: 13px;
  margin: 4px 0;
}
</style>
