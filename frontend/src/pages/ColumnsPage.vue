<template>
  <div class="columns">
    <PageHeader
      title="列语义推断校验"
      eyebrow="02 / COLUMN SURVEY"
      subtitle="6 类正则命中率 + 列名词典 + 基数/空值特征加权打分；右侧展开证据与命中样本，歧义与未知单列标注。"
    >
      <template #actions>
        <input v-model="search" class="search mono" type="search" placeholder="搜列名 / 表名…" @keyup.enter="reload(1)" />
        <button
          id="run-infer"
          class="btn btn--primary"
          type="button"
          :disabled="!perm.can('column:infer') || inferring"
          :title="perm.can('column:infer') ? '对所有已采样列重新推断' : '仅 admin / analyst 可执行推断'"
          @click="runInfer"
        >
          {{ inferring ? '推断中…' : '运行语义推断' }}
        </button>
      </template>
    </PageHeader>

    <section class="summary">
      <button
        v-for="item in summaryCards"
        :key="item.type"
        type="button"
        class="summary__card"
        :class="{ 'is-active': activeType === item.type }"
        @click="pickType(item.type)"
      >
        <span class="smallcaps summary__label">{{ item.label }}</span>
        <span class="summary__value numeric">{{ item.count }}</span>
        <span class="summary__hint mono">{{ item.hint }}</span>
      </button>
      <div class="summary__meta">
        <p class="smallcaps">PROFILED {{ summary?.profiled_columns ?? 0 }} / {{ summary?.total_columns ?? 0 }}</p>
        <p class="smallcaps">HUMAN CORRECTED {{ summary?.human_corrected ?? 0 }}</p>
      </div>
    </section>

    <div class="columns__grid">
      <section class="tablewrap ink-panel">
        <ErrorNotice v-if="error" :message="error" />
        <div v-if="loading" class="empty-state">正在比对列签名…</div>
        <table v-else class="data-table">
          <thead>
            <tr>
              <th>列 COLUMN</th>
              <th>所属表 SHEET</th>
              <th>语义类型 TYPE</th>
              <th>置信度 CONF.</th>
              <th>来源 SOURCE</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="column in items"
              :key="column.id"
              class="column-row"
              :class="{ 'is-selected': selected?.id === column.id }"
              @click="selectColumn(column)"
            >
              <td>
                <ColumnChip
                  :column-name="column.column_name"
                  :type="column.inferred_type"
                  :confidence="column.confidence"
                  :source="column.inference_source"
                />
              </td>
              <td class="mono cell-asset">{{ column.asset?.asset_key }}</td>
              <td class="mono">{{ typeLabel(column.inferred_type) }}</td>
              <td><ConfidenceMeter :value="column.confidence" :type="column.inferred_type" /></td>
              <td class="mono cell-source">{{ sourceLabel(column.inference_source) }}</td>
            </tr>
          </tbody>
        </table>
        <footer class="tablewrap__foot">
          <button class="btn btn--ghost" type="button" :disabled="page <= 1" @click="reload(page - 1)">上一页</button>
          <span class="mono smallcaps">PAGE {{ page }} · {{ total }} 列</span>
          <button class="btn btn--ghost" type="button" :disabled="page * pageSize >= total" @click="reload(page + 1)">
            下一页
          </button>
        </footer>
      </section>

      <aside class="evidence ink-panel">
        <div v-if="!selected" class="empty-state">选择左侧任意一列查看推断证据。</div>
        <template v-else>
          <header class="evidence__head">
            <p class="smallcaps evidence__eyebrow">{{ selected.asset?.asset_key }}</p>
            <h3 class="evidence__title">{{ selected.column_name }}</h3>
            <div class="evidence__chips">
              <ColumnChip
                :column-name="selected.column_name"
                :type="selected.inferred_type"
                :confidence="selected.confidence"
                :source="selected.inference_source"
              />
              <ConfidenceMeter :value="selected.confidence" :type="selected.inferred_type" />
            </div>
          </header>

          <div class="evidence__block">
            <p class="smallcaps evidence__label">证据 EVIDENCE</p>
            <EvidenceList :lines="selected.evidence ?? []" />
          </div>

          <div class="evidence__block">
            <p class="smallcaps evidence__label">候选 CANDIDATES</p>
            <ul class="evidence__cands">
              <li v-for="cand in selected.candidates ?? []" :key="cand.type" class="evidence__cand">
                <span class="mono">{{ typeLabel(cand.type as never) }}</span>
                <span class="evidence__candtrack"><span :style="{ width: `${cand.score * 100}%` }"></span></span>
                <span class="numeric">{{ cand.score.toFixed(3) }}</span>
              </li>
            </ul>
          </div>

          <div class="evidence__block">
            <p class="smallcaps evidence__label">统计 STATS</p>
            <dl class="evidence__stats">
              <div><dt>采样数</dt><dd class="numeric">{{ selected.stats?.sample_count ?? 0 }}</dd></div>
              <div><dt>空值率</dt><dd class="numeric">{{ percent(selected.stats?.null_rate) }}</dd></div>
              <div><dt>唯一值</dt><dd class="numeric">{{ selected.stats?.unique_count ?? 0 }}</dd></div>
              <div><dt>声明类型</dt><dd class="mono">{{ selected.data_type }}</dd></div>
            </dl>
            <p class="smallcaps evidence__label" style="margin-top: 10px">命中样本前 3 个</p>
            <ul class="evidence__samples">
              <li v-for="(value, index) in (selected.sample_values ?? []).slice(0, 3)" :key="index" class="mono">
                {{ value ?? 'NULL' }}
              </li>
            </ul>
          </div>

          <div class="evidence__block evidence__block--correct">
            <p class="smallcaps evidence__label">人工纠错 MANUAL CORRECTION</p>
            <div v-if="corrected" class="evidence__done mono">已记录 manual 来源纠正（置信度 1.0）</div>
            <template v-else>
              <div class="evidence__correctrow">
                <select v-model="correctType" class="evidence__select mono" :disabled="!perm.can('column:correct')">
                  <option v-for="type in typeOptions" :key="type" :value="type">{{ typeLabel(type as never) }}</option>
                </select>
                <button
                  class="btn btn--danger"
                  type="button"
                  :disabled="!perm.can('column:correct') || correcting"
                  @click="applyCorrection"
                >
                  {{ correcting ? '提交中…' : '纠正类型' }}
                </button>
              </div>
              <p v-if="!perm.can('column:correct')" class="smallcaps evidence__readonly">当前角色只读：无 column:correct 权限</p>
            </template>
          </div>
        </template>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import PageHeader from '../components/common/PageHeader.vue'
import ErrorNotice from '../components/common/ErrorNotice.vue'
import ColumnChip from '../components/common/ColumnChip.vue'
import ConfidenceMeter from '../components/common/ConfidenceMeter.vue'
import EvidenceList from '../components/catalog/EvidenceList.vue'
import { correctColumnType, fetchColumnSummary, fetchColumns, inferColumns } from '../api/columns'
import { usePermission } from '../hooks/usePermission'
import type { ColumnItem } from '../types/models'
import { COLUMN_TYPE_LABELS, COLUMN_TYPE_ORDER, INFERENCE_SOURCE_LABELS } from '../constants/enums'
import { percent } from '../utils/format'

const perm = usePermission()
const summary = ref<Record<string, number> | null>(null)
const items = ref<ColumnItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 15
const activeType = ref('typed')
const search = ref('')
const loading = ref(false)
const error = ref('')
const selected = ref<ColumnItem | null>(null)
const inferring = ref(false)
const correcting = ref(false)
const corrected = ref(false)
const correctType = ref('enum')

const typeOptions = COLUMN_TYPE_ORDER
const summaryCards = computed(() => {
  const byType = summary.value?.by_type ?? {}
  const profileType = Number(byType['phone'] ?? 0) + Number(byType['id_card'] ?? 0) + Number(byType['email'] ?? 0)
  return [
    { type: 'phone', label: '手机号', count: Number(byType['phone'] ?? 0), hint: 'PHONE' },
    { type: 'email', label: '邮箱', count: Number(byType['email'] ?? 0), hint: 'EMAIL' },
    { type: 'id_card', label: '身份证', count: Number(byType['id_card'] ?? 0), hint: 'ID_CARD' },
    { type: 'amount', label: '金额', count: Number(byType['amount'] ?? 0), hint: 'AMOUNT' },
    { type: 'datetime', label: '日期时间', count: Number(byType['datetime'] ?? 0), hint: 'DATETIME' },
    { type: 'enum', label: '枚举', count: Number(byType['enum'] ?? 0), hint: 'ENUM' },
    { type: 'unknown', label: '未知', count: Number(byType['unknown'] ?? 0), hint: 'UNKNOWN' },
    { type: 'typed', label: '全部命中', count: profileType, hint: 'PII TYPED' },
  ]
})

function typeLabel(type: string | null) {
  if (!type) return '—'
  return COLUMN_TYPE_LABELS[type as keyof typeof COLUMN_TYPE_LABELS] ?? type
}

function sourceLabel(source: string | null) {
  if (!source) return '未推断'
  return INFERENCE_SOURCE_LABELS[source] ?? source
}

async function loadSummary() {
  try {
    summary.value = await fetchColumnSummary()
  } catch {
    summary.value = null
  }
}

async function reload(nextPage = page.value) {
  loading.value = true
  error.value = ''
  try {
    const data = await fetchColumns({
      page: nextPage,
      page_size: pageSize,
      q: search.value || undefined,
      inferred_type: activeType.value === 'typed' ? 'typed' : activeType.value,
    })
    items.value = data.items
    total.value = data.total
    page.value = data.page
    if (!selected.value && data.items.length) {
      selectColumn(data.items[0])
    }
  } catch (err) {
    error.value = (err as { message?: string }).message ?? '读取列失败'
  } finally {
    loading.value = false
  }
}

function selectColumn(column: ColumnItem) {
  selected.value = column
  corrected.value = false
  correctType.value = 'enum'
}

async function pickType(type: string) {
  activeType.value = type
  selected.value = null
  await reload(1)
}

async function runInfer() {
  inferring.value = true
  error.value = ''
  try {
    await inferColumns()
    await Promise.all([loadSummary(), reload(1)])
  } catch (err) {
    error.value = (err as { message?: string }).message ?? '推断失败，请先运行采集任务'
  } finally {
    inferring.value = false
  }
}

async function applyCorrection() {
  if (!selected.value) return
  correcting.value = true
  try {
    await correctColumnType(selected.value.id, correctType.value, '人工复核：样例与业务口径不符')
    corrected.value = true
    await Promise.all([loadSummary(), reload(page.value)])
    const updated = items.value.find((item) => item.id === selected.value?.id)
    if (updated) selected.value = updated
  } catch (err) {
    error.value = (err as { message?: string }).message ?? '纠正失败'
  } finally {
    correcting.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadSummary(), reload(1)])
})
</script>

<style scoped>
.search {
  width: 200px;
  padding: 6px 10px;
  border: 1px solid var(--line);
  background: var(--sand-raise);
  font-size: 11.5px;
}
.summary {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: stretch;
  margin-bottom: 14px;
}
.summary__card {
  display: flex;
  flex-direction: column;
  gap: 1px;
  padding: 7px 12px;
  min-width: 96px;
  border: 1px solid var(--line);
  border-bottom: 3px solid var(--line-soft);
  background: color-mix(in oklch, var(--sand-raise) 70%, transparent);
  text-align: left;
  transition: all 160ms var(--ease);
}
.summary__card:hover {
  border-bottom-color: var(--ink);
}
.summary__card.is-active {
  border-bottom-color: var(--moss);
  background: color-mix(in oklch, var(--moss-wash) 55%, transparent);
}
.summary__label {
  color: var(--ink-faint);
  font-size: 8.5px;
}
.summary__value {
  font-family: var(--font-display);
  font-size: 22px;
  line-height: 1.1;
}
.summary__hint {
  font-size: 8px;
  color: var(--ink-faint);
}
.summary__meta {
  margin-left: auto;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  gap: 3px;
  color: var(--ink-faint);
  text-align: right;
}
.columns__grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 380px;
  gap: 14px;
  align-items: start;
}
.tablewrap {
  overflow: hidden;
}
.cell-asset {
  color: var(--ink-soft);
  max-width: 190px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.cell-source {
  color: var(--brick);
}
.column-row {
  cursor: pointer;
}
.tablewrap__foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  border-top: 1px solid var(--line);
}
.evidence {
  padding: 14px;
  position: sticky;
  top: 14px;
  max-height: calc(100vh - 150px);
  overflow: auto;
}
.evidence__eyebrow {
  color: var(--brick);
}
.evidence__title {
  font-size: 21px;
  margin-top: 2px;
  word-break: break-all;
}
.evidence__chips {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  flex-wrap: wrap;
}
.evidence__block {
  border-top: 1px dashed var(--line);
  margin-top: 12px;
  padding-top: 10px;
}
.evidence__label {
  color: var(--ink-faint);
  margin-bottom: 7px;
}
.evidence__cands {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 5px;
}
.evidence__cand {
  display: grid;
  grid-template-columns: 74px 1fr 44px;
  gap: 8px;
  align-items: center;
  font-size: 10.5px;
  color: var(--ink-soft);
}
.evidence__candtrack {
  height: 4px;
  background: var(--line-soft);
}
.evidence__candtrack span {
  display: block;
  height: 100%;
  background: var(--moss-soft);
}
.evidence__stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 3px 12px;
  margin: 0;
}
.evidence__stats div {
  display: flex;
  justify-content: space-between;
  font-size: 10.5px;
  color: var(--ink-faint);
}
.evidence__stats dd {
  margin: 0;
  color: var(--ink);
}
.evidence__samples {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 3px;
  font-size: 10px;
  color: var(--ink-soft);
  word-break: break-all;
}
.evidence__correctrow {
  display: flex;
  gap: 6px;
}
.evidence__select {
  flex: 1;
  padding: 5px 8px;
  border: 1px solid var(--line);
  background: var(--sand-raise);
  font-size: 11px;
}
.evidence__readonly {
  margin-top: 6px;
  color: var(--brick);
}
.evidence__done {
  font-size: 10.5px;
  color: var(--moss);
  border: 1px dashed var(--moss-soft);
  padding: 6px 8px;
}
@media (max-width: 1279px) {
  .columns__grid {
    grid-template-columns: 1fr;
  }
  .evidence {
    position: static;
    max-height: none;
  }
}
</style>
