<template>
  <div class="dups">
    <PageHeader
      title="相似表推荐"
      eyebrow="03 / DUPLICATE PLATE"
      subtitle="列签名归一化 → MinHash k=128 + 16×8 LSH 候选 → 精确 Jaccard + 列名结构相似；score = 0.7×jaccard + 0.3×结构相似。"
    >
      <template #actions>
        <button
          id="run-recompute"
          class="btn btn--primary"
          type="button"
          :disabled="!perm.can('duplicate:recompute') || recomputing"
          :title="perm.can('duplicate:recompute') ? '重新计算 42 张资产的两两相似度' : '仅 admin 可重算'"
          @click="runRecompute"
        >
          {{ recomputing ? '计算中…' : '重新计算相似度' }}
        </button>
        <PermissionHint v-if="!perm.can('duplicate:recompute')" label="仅管理员可重算" />
      </template>
    </PageHeader>

    <ErrorNotice v-if="error" :message="error" />

    <section class="dups__stats">
      <div class="stat ink-panel">
        <p class="smallcaps">总对数 PAIRS</p>
        <p class="stat__value numeric">{{ pairs.total }}</p>
      </div>
      <div class="stat ink-panel">
        <p class="smallcaps">待确认 RECOMMENDED</p>
        <p class="stat__value numeric">{{ pairs.recommended_total ?? 0 }}</p>
      </div>
      <div class="stat ink-panel">
        <p class="smallcaps">真重复 ≥0.85</p>
        <p class="stat__value numeric stat__value--hot">{{ pairs.true_duplicate_total ?? 0 }}</p>
      </div>
      <div class="stat ink-panel">
        <p class="smallcaps">已排除 DISMISSED</p>
        <p class="stat__value numeric">{{ pairs.dismissed_total ?? 0 }}</p>
      </div>
      <p class="dups__legend mono">
        候选对 = LSH 同桶 · 引擎：{{ engineInfo }}
      </p>
    </section>

    <div class="dups__grid">
      <section class="pairlist ink-panel">
        <header class="pairlist__head">
          <span class="smallcaps">TOP {{ pairs.items?.length ?? 0 }} 推荐</span>
          <span class="mono">按 score 倒序</span>
        </header>
        <ul class="pairlist__rows">
          <li
            v-for="pair in pairs.items"
            :key="pair.id"
            class="pair-row"
            :class="{ 'is-selected': selectedId === pair.id }"
            @click="selectPair(pair.id)"
          >
            <div class="pair-row__top">
              <span class="pair-row__rank mono">#{{ rankOf(pair.id) }}</span>
              <span class="pair-row__verdict" :class="{ 'is-hot': pair.score >= 0.85 }">
                {{ verdictLabel(pair.verdict) }}
              </span>
              <span class="pair-row__status mono">{{ statusLabel(pair.status) }}</span>
            </div>
            <p class="pair-row__names mono">
              {{ pair.left.table_name }}<span class="pair-row__arrow"> ⇄ </span>{{ pair.right.table_name }}
            </p>
            <SimilarityBar :score="pair.score" />
            <p class="pair-row__meta mono">
              jaccard {{ pair.jaccard.toFixed(3) }} · 结构 {{ pair.structure_score.toFixed(3) }} ·
              {{ pair.left.column_count }} vs {{ pair.right.column_count }} 列
            </p>
          </li>
        </ul>
      </section>

      <section class="pair-detail">
        <div v-if="!detail" class="empty-state">选择左侧一对表，展开并排 diff 与合并建议。</div>
        <template v-else>
          <header class="pair-detail__head ink-panel">
            <div class="pair-detail__names">
              <div>
                <p class="smallcaps">A / {{ detail.left.layer.toUpperCase() }}</p>
                <h3 class="pair-detail__title">{{ detail.left.asset_key }}</h3>
                <p class="mono pair-detail__sub">{{ detail.left.owner_name }} · {{ formatNumber(detail.left.row_count) }} 行</p>
              </div>
              <span class="pair-detail__vs mono">VS</span>
              <div class="pair-detail__right">
                <p class="smallcaps">B / {{ detail.right.layer.toUpperCase() }}</p>
                <h3 class="pair-detail__title">{{ detail.right.asset_key }}</h3>
                <p class="mono pair-detail__sub">{{ detail.right.owner_name }} · {{ formatNumber(detail.right.row_count) }} 行</p>
              </div>
            </div>
            <div class="pair-detail__scorebox">
              <p class="smallcaps">综合相似度 SCORE</p>
              <p class="pair-detail__score numeric">{{ detail.score.toFixed(3) }}</p>
              <SimilarityBar :score="detail.score" />
            </div>
          </header>

          <div class="pair-detail__body">
            <DiffColumnsTable
              v-if="detail.diff && detail.diff.length"
              :rows="detail.diff"
              :left-title="detail.left.table_name"
              :right-title="detail.right.table_name"
            />
            <div v-else class="empty-state">该对表没有列级 diff 数据，请先重新计算相似度。</div>

            <aside class="merge ink-panel">
              <p class="smallcaps merge__title">合并建议 MERGE NOTE</p>
              <template v-if="mergeSuggestion">
                <p class="merge__drop mono">
                  下线 <strong>{{ mergeSuggestion.drop_asset_key }}</strong>
                </p>
                <p class="merge__keep mono">保留 <strong>{{ mergeSuggestion.keep_asset_key }}</strong></p>
                <p class="smallcaps merge__label">动作 ACTIONS</p>
                <ol class="merge__actions">
                  <li v-for="(action, index) in mergeSuggestion.actions" :key="index">{{ action }}</li>
                </ol>
                <p class="smallcaps merge__label">保留列并集 UNION ({{ mergeSuggestion.union_columns?.length ?? 0 }})</p>
                <p class="merge__union mono">{{ (mergeSuggestion.union_columns ?? []).join(' · ') }}</p>
                <p class="merge__gen mono">
                  {{ mergeSuggestion.generated_by ? `由 ${mergeSuggestion.generated_by} 生成` : '引擎自动生成' }}
                </p>
              </template>
              <p v-else class="merge__empty mono">尚未生成合并建议。</p>

              <div class="merge__buttons">
                <button
                  id="gen-merge"
                  class="btn btn--primary"
                  type="button"
                  :disabled="!perm.can('duplicate:merge') || merging"
                  @click="generateMerge"
                >
                  {{ merging ? '生成中…' : '生成合并建议' }}
                </button>
                <button
                  class="btn btn--ghost"
                  type="button"
                  :disabled="!perm.can('duplicate:dismiss')"
                  @click="dismissCurrent"
                >
                  标记非重复
                </button>
              </div>
              <p v-if="!perm.can('duplicate:merge')" class="smallcaps merge__readonly">
                当前角色无 duplicate:merge 权限
              </p>
            </aside>
          </div>
        </template>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import PageHeader from '../components/common/PageHeader.vue'
import ErrorNotice from '../components/common/ErrorNotice.vue'
import PermissionHint from '../components/common/PermissionHint.vue'
import SimilarityBar from '../components/common/SimilarityBar.vue'
import DiffColumnsTable from '../components/catalog/DiffColumnsTable.vue'
import {
  dismissPair,
  fetchPair,
  fetchPairs,
  generateMergeSuggestion,
  recomputePairs,
} from '../api/duplicates'
import { usePermission } from '../hooks/usePermission'
import type { MergeSuggestion, SimilarityPair } from '../types/models'
import { PAIR_STATUS_LABELS, VERDICT_LABELS } from '../constants/enums'
import { numberText } from '../utils/format'

const perm = usePermission()
const pairs = ref<{
  items: SimilarityPair[]
  total: number
  recommended_total?: number
  dismissed_total?: number
  true_duplicate_total?: number
}>({ items: [], total: 0 })
const detail = ref<SimilarityPair | null>(null)
const selectedId = ref('')
const error = ref('')
const recomputing = ref(false)
const merging = ref(false)

const engineInfo = computed(() => {
  const first = pairs.value.items?.[0]
  return first ? `${first.method} · k=128 · 16×8` : 'minhash-lsh · k=128 · 16×8'
})

const mergeSuggestion = computed<MergeSuggestion | null>(() => {
  const suggestion = detail.value?.suggestion as MergeSuggestion | undefined
  return suggestion && suggestion.drop_asset_key ? suggestion : null
})

function formatNumber(value: number | undefined) {
  return numberText(value)
}
function verdictLabel(verdict: string) {
  return VERDICT_LABELS[verdict] ?? verdict
}
function statusLabel(status: string) {
  return PAIR_STATUS_LABELS[status] ?? status
}
function rankOf(pairId: string) {
  return (pairs.value.items.findIndex((item) => item.id === pairId) ?? 0) + 1
}

async function loadPairs() {
  try {
    pairs.value = await fetchPairs(5)
    if (!selectedId.value && pairs.value.items.length) {
      await selectPair(pairs.value.items[0].id)
    }
  } catch (err) {
    error.value = (err as { message?: string }).message ?? '读取相似表失败'
  }
}

async function selectPair(pairId: string) {
  selectedId.value = pairId
  try {
    detail.value = await fetchPair(pairId)
  } catch (err) {
    error.value = (err as { message?: string }).message ?? '读取相似表详情失败'
  }
}

async function runRecompute() {
  recomputing.value = true
  error.value = ''
  try {
    await recomputePairs(6)
    await loadPairs()
    if (selectedId.value) await selectPair(selectedId.value)
  } catch (err) {
    error.value = (err as { message?: string }).message ?? '重算失败'
  } finally {
    recomputing.value = false
  }
}

async function generateMerge() {
  if (!detail.value) return
  merging.value = true
  try {
    await generateMergeSuggestion(detail.value.id)
    await selectPair(detail.value.id)
  } catch (err) {
    error.value = (err as { message?: string }).message ?? '生成合并建议失败'
  } finally {
    merging.value = false
  }
}

async function dismissCurrent() {
  if (!detail.value) return
  try {
    await dismissPair(detail.value.id, '人工复核：口径不同，非重复')
    await loadPairs()
    if (pairs.value.items.length) await selectPair(pairs.value.items[0].id)
  } catch (err) {
    error.value = (err as { message?: string }).message ?? '操作失败'
  }
}

onMounted(loadPairs)
</script>

<style scoped>
.dups__stats {
  display: flex;
  align-items: stretch;
  gap: 8px;
  margin-bottom: 14px;
}
.stat {
  padding: 8px 14px;
  min-width: 110px;
  color: var(--ink-faint);
}
.stat__value {
  font-family: var(--font-display);
  font-size: 24px;
  color: var(--ink);
  line-height: 1.15;
}
.stat__value--hot {
  color: var(--brick);
}
.dups__legend {
  margin-left: auto;
  align-self: flex-end;
  font-size: 10px;
  color: var(--ink-faint);
  max-width: 300px;
  text-align: right;
}
.dups__grid {
  display: grid;
  grid-template-columns: 380px minmax(0, 1fr);
  gap: 14px;
  align-items: start;
}
.pairlist {
  overflow: hidden;
  position: sticky;
  top: 14px;
}
.pairlist__head {
  display: flex;
  justify-content: space-between;
  padding: 9px 12px;
  border-bottom: 1px solid var(--ink);
  color: var(--ink-faint);
}
.pairlist__rows {
  list-style: none;
  margin: 0;
  padding: 0;
}
.pair-row {
  padding: 9px 12px;
  border-bottom: 1px dashed var(--line-soft);
  cursor: pointer;
  transition: background 160ms var(--ease);
}
.pair-row:hover {
  background: color-mix(in oklch, var(--moss-wash) 40%, transparent);
}
.pair-row.is-selected {
  background: color-mix(in oklch, var(--moss-wash) 70%, transparent);
  box-shadow: inset 2px 0 0 var(--moss);
}
.pair-row__top {
  display: flex;
  align-items: center;
  gap: 8px;
}
.pair-row__rank {
  font-size: 10px;
  color: var(--brick);
}
.pair-row__verdict {
  font-size: 9.5px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--ink-soft);
  border: 1px solid var(--line);
  padding: 1px 6px;
}
.pair-row__verdict.is-hot {
  color: var(--brick);
  border-color: var(--brick-soft);
}
.pair-row__status {
  margin-left: auto;
  font-size: 9px;
  color: var(--ink-faint);
}
.pair-row__names {
  margin: 5px 0 7px;
  font-size: 11.5px;
  color: var(--ink);
  word-break: break-all;
}
.pair-row__arrow {
  color: var(--brick);
}
.pair-row__meta {
  margin-top: 5px;
  font-size: 9.5px;
  color: var(--ink-faint);
}
.pair-detail {
  min-width: 0;
}
.pair-detail__head {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  padding: 14px 16px;
  margin-bottom: 12px;
}
.pair-detail__names {
  display: flex;
  gap: 20px;
  align-items: center;
  flex-wrap: wrap;
}
.pair-detail__right {
  text-align: left;
}
.pair-detail__vs {
  font-family: var(--font-display);
  font-size: 20px;
  color: var(--brick);
}
.pair-detail__title {
  font-size: 18px;
  margin-top: 2px;
  word-break: break-all;
}
.pair-detail__sub {
  margin-top: 3px;
  font-size: 10.5px;
  color: var(--ink-faint);
}
.pair-detail__scorebox {
  min-width: 190px;
}
.pair-detail__score {
  font-family: var(--font-display);
  font-size: 34px;
  line-height: 1.05;
  color: var(--brick);
}
.pair-detail__body {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 12px;
  align-items: start;
}
.merge {
  padding: 12px;
}
.merge__title {
  color: var(--ink-faint);
  margin-bottom: 8px;
}
.merge__drop {
  font-size: 11px;
  color: var(--brick);
}
.merge__keep {
  font-size: 11px;
  color: var(--moss);
  margin-top: 3px;
}
.merge__label {
  color: var(--ink-faint);
  margin: 12px 0 5px;
}
.merge__actions {
  margin: 0;
  padding-left: 16px;
  display: grid;
  gap: 4px;
  font-size: 10.5px;
  color: var(--ink-soft);
}
.merge__union {
  font-size: 10px;
  color: var(--ink-soft);
  word-break: break-all;
}
.merge__gen {
  margin-top: 8px;
  font-size: 9px;
  color: var(--ink-faint);
}
.merge__empty {
  font-size: 10.5px;
  color: var(--ink-faint);
}
.merge__buttons {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 14px;
}
.merge__readonly {
  margin-top: 8px;
  color: var(--brick);
}
@media (max-width: 1279px) {
  .dups__grid {
    grid-template-columns: 1fr;
  }
  .pairlist {
    position: static;
  }
  .pair-detail__body {
    grid-template-columns: 1fr;
  }
}
</style>
