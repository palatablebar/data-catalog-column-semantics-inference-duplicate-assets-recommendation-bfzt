<template>
  <div class="assets">
    <PageHeader
      title="资产检索"
      eyebrow="01 / ASSET INDEX"
      subtitle="左侧按数仓分层与业务域定位，右侧展开表与列卡片；敏感列与推断类型直接标注在列上。"
    >
      <template #actions>
        <input
          id="asset-search"
          v-model="search"
          class="search mono"
          type="search"
          placeholder="搜表名 / 资产键 / 域…"
          @keyup.enter="reload(1)"
        />
        <button class="btn btn--ghost" type="button" :disabled="exporting" @click="exportCsv">
          {{ exporting ? '导出中…' : '导出目录 CSV' }}
        </button>
      </template>
    </PageHeader>

    <div class="assets__grid">
      <aside class="tree ink-panel">
        <p class="tree__title smallcaps">数仓分层 LAYERS</p>
        <button
          type="button"
          class="tree__item"
          :class="{ 'is-active': !activeLayer && !activeDomain }"
          @click="pickLayer('')"
        >
          <span class="mono">全部资产</span>
          <span class="numeric">{{ stats?.assets ?? 0 }}</span>
        </button>
        <button
          v-for="layer in layers"
          :key="layer.value"
          type="button"
          class="tree__item"
          :class="{ 'is-active': activeLayer === layer.value }"
          @click="pickLayer(layer.value)"
        >
          <span class="mono">{{ layer.label }}</span>
          <span class="numeric">{{ layer.count }}</span>
        </button>
        <hr class="ink-rule tree__rule" />
        <p class="tree__title smallcaps">业务域 DOMAINS</p>
        <button
          v-for="domain in domains"
          :key="domain.value"
          type="button"
          class="tree__item tree__item--sub"
          :class="{ 'is-active': activeDomain === domain.value }"
          @click="pickDomain(domain.value)"
        >
          <span class="mono">{{ domain.value }}</span>
          <span class="numeric">{{ domain.count }}</span>
        </button>
        <LegendPanel
          class="tree__legend"
          title="列语义图例"
          :items="[
            { label: '手机号 / 身份证', color: 'var(--brick)' },
            { label: '邮箱', color: 'var(--gold)' },
            { label: '金额', color: 'var(--moss)' },
            { label: '日期 / 枚举', color: 'var(--moss-soft)' },
          ]"
        />
      </aside>

      <section class="list ink-panel">
        <header class="list__head">
          <span class="smallcaps">表 SHEET INDEX</span>
          <span class="mono list__count">{{ total }} 张</span>
        </header>
        <ErrorNotice v-if="error" :message="error" />
        <div v-if="loading" class="empty-state">正在调阅目录…</div>
        <ul v-else class="list__rows">
          <li
            v-for="asset in items"
            :key="asset.id"
            class="asset-row"
            :class="{ 'is-selected': selectedId === asset.id }"
            @click="selectAsset(asset.id)"
          >
            <div class="asset-row__main">
              <span class="asset-row__layer mono">{{ asset.layer }}</span>
              <span class="asset-row__key mono">{{ asset.asset_key }}</span>
              <span v-if="asset.source_kind === 'sample_table'" class="asset-row__flag">样例</span>
            </div>
            <div class="asset-row__meta mono">
              <span>{{ asset.domain }}</span>
              <span>{{ asset.column_count }} 列</span>
              <span>{{ formatNumber(asset.row_count) }} 行</span>
              <span v-if="asset.sensitive_tag_count" class="asset-row__sensitive">
                敏感 {{ asset.sensitive_tag_count }}
              </span>
            </div>
          </li>
        </ul>
        <footer class="list__foot">
          <button class="btn btn--ghost" type="button" :disabled="page <= 1" @click="reload(page - 1)">上一页</button>
          <span class="mono smallcaps">PAGE {{ page }}</span>
          <button class="btn btn--ghost" type="button" :disabled="page * pageSize >= total" @click="reload(page + 1)">
            下一页
          </button>
        </footer>
      </section>

      <section class="detail ink-panel">
        <div v-if="!detail" class="empty-state">
          <p class="smallcaps" style="color: var(--brick); margin-bottom: 6px">SHEET NOT SELECTED</p>
          左侧选择一张表，这里会展开列卡片、负责人和敏感列标注。
        </div>
        <template v-else>
          <header class="detail__head">
            <p class="smallcaps detail__layer">{{ detail.layer.toUpperCase() }} · {{ detail.domain }}域</p>
            <h3 class="detail__title">{{ detail.table_name }}</h3>
            <p class="detail__desc">{{ detail.description }}</p>
            <dl class="detail__facts">
              <div><dt>负责人</dt><dd>{{ detail.owner_name }}</dd></div>
              <div><dt>行数</dt><dd class="numeric">{{ formatNumber(detail.row_count) }}</dd></div>
              <div><dt>列数</dt><dd class="numeric">{{ detail.column_count }}</dd></div>
              <div><dt>来源</dt><dd>{{ detail.source_kind === 'sample_table' ? '样例数据' : '仅元数据' }}</dd></div>
            </dl>
          </header>
          <div class="detail__columns">
            <p class="smallcaps detail__section">列卡片 COLUMNS</p>
            <ul class="detail__collen">
              <li v-for="column in detailColumns" :key="column.id" class="detail__col">
                <ColumnChip
                  :column-name="column.column_name"
                  :type="column.inferred_type"
                  :confidence="column.confidence"
                  :source="column.inference_source"
                />
                <span class="detail__datatype mono">{{ column.data_type }}</span>
                <TagStamp
                  v-for="tag in column.tags"
                  :key="tag.id"
                  :tag-name="tag.tag_name"
                  :source="tag.source"
                />
              </li>
            </ul>
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
import LegendPanel from '../components/common/LegendPanel.vue'
import ColumnChip from '../components/common/ColumnChip.vue'
import TagStamp from '../components/common/TagStamp.vue'
import { exportCatalogCsv, fetchAsset, fetchAssets } from '../api/assets'
import { useAssetTree } from '../hooks/useAssetTree'
import type { AssetDetail, AssetListItem } from '../types/models'
import { numberText } from '../utils/format'

const { layers, domains, stats, load: loadTree } = useAssetTree()
const items = ref<AssetListItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const search = ref('')
const activeLayer = ref('')
const activeDomain = ref('')
const loading = ref(false)
const error = ref('')
const selectedId = ref('')
const detail = ref<AssetDetail | null>(null)
const exporting = ref(false)

const detailColumns = computed(() => (detail.value?.columns ?? []).slice(0, 18))

function formatNumber(value: number | undefined) {
  return numberText(value)
}

async function reload(nextPage = page.value) {
  loading.value = true
  error.value = ''
  try {
    const data = await fetchAssets({
      page: nextPage,
      page_size: pageSize,
      q: search.value || undefined,
      layer: activeLayer.value || undefined,
      domain: activeDomain.value || undefined,
    })
    items.value = data.items
    total.value = data.total
    page.value = data.page
    if (!selectedId.value && data.items.length) {
      await selectAsset(data.items[0].id)
    }
  } catch (err) {
    error.value = (err as { message?: string }).message ?? '读取资产失败'
  } finally {
    loading.value = false
  }
}

async function selectAsset(assetId: string) {
  selectedId.value = assetId
  try {
    detail.value = await fetchAsset(assetId)
  } catch (err) {
    error.value = (err as { message?: string }).message ?? '读取资产详情失败'
  }
}

async function pickLayer(layer: string) {
  activeLayer.value = layer
  selectedId.value = ''
  await reload(1)
}

async function pickDomain(domain: string) {
  activeDomain.value = activeDomain.value === domain ? '' : domain
  selectedId.value = ''
  await reload(1)
}

async function exportCsv() {
  exporting.value = true
  try {
    const response = await exportCatalogCsv()
    const blob = new Blob([response.data], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'catmap-catalog.csv'
    link.click()
    URL.revokeObjectURL(url)
  } catch (err) {
    error.value = (err as { message?: string }).message ?? '导出失败'
  } finally {
    exporting.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadTree(), reload(1)])
})
</script>

<style scoped>
.assets__grid {
  display: grid;
  grid-template-columns: 208px minmax(0, 1fr) 360px;
  gap: 14px;
  align-items: start;
}
.search {
  width: 210px;
  padding: 6px 10px;
  border: 1px solid var(--line);
  background: var(--sand-raise);
  font-size: 11.5px;
}
.search:focus {
  outline: none;
  border-color: var(--moss);
}
.tree {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 3px;
  position: sticky;
  top: 14px;
}
.tree__title {
  color: var(--ink-faint);
  margin: 4px 0 5px;
}
.tree__item {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  padding: 4px 6px;
  border: 0;
  border-left: 2px solid transparent;
  background: transparent;
  font-size: 11px;
  color: var(--ink-soft);
  text-align: left;
}
.tree__item:hover {
  color: var(--ink);
  background: color-mix(in oklch, var(--sand-deep) 50%, transparent);
}
.tree__item.is-active {
  border-left-color: var(--moss);
  color: var(--ink);
  background: color-mix(in oklch, var(--moss-wash) 50%, transparent);
}
.tree__item--sub {
  padding-left: 14px;
}
.tree__rule {
  margin: 10px 0;
}
.tree__legend {
  margin-top: 12px;
}
.list {
  display: flex;
  flex-direction: column;
  min-height: 480px;
}
.list__head {
  display: flex;
  justify-content: space-between;
  padding: 9px 12px;
  border-bottom: 1px solid var(--ink);
  color: var(--ink-faint);
}
.list__rows {
  list-style: none;
  margin: 0;
  padding: 0;
  flex: 1;
}
.asset-row {
  padding: 8px 12px;
  border-bottom: 1px dashed var(--line-soft);
  cursor: pointer;
  transition: background 150ms var(--ease);
}
.asset-row:hover {
  background: color-mix(in oklch, var(--moss-wash) 42%, transparent);
}
.asset-row.is-selected {
  background: color-mix(in oklch, var(--moss-wash) 72%, transparent);
  box-shadow: inset 2px 0 0 var(--moss);
}
.asset-row__main {
  display: flex;
  align-items: baseline;
  gap: 8px;
}
.asset-row__layer {
  font-size: 9px;
  text-transform: uppercase;
  color: var(--brick);
  border: 1px solid var(--brick-soft);
  padding: 0 4px;
}
.asset-row__key {
  font-size: 12px;
  color: var(--ink);
}
.asset-row__flag {
  font-size: 8.5px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--moss);
  border-bottom: 1px solid var(--moss-soft);
}
.asset-row__meta {
  display: flex;
  gap: 12px;
  margin-top: 2px;
  padding-left: 38px;
  font-size: 10px;
  color: var(--ink-faint);
}
.asset-row__sensitive {
  color: var(--brick);
}
.list__foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  border-top: 1px solid var(--line);
}
.detail {
  padding: 14px;
  position: sticky;
  top: 14px;
  max-height: calc(100vh - 150px);
  overflow: auto;
}
.detail__layer {
  color: var(--brick);
}
.detail__title {
  font-size: 21px;
  word-break: break-all;
  margin-top: 2px;
}
.detail__desc {
  margin-top: 6px;
  font-size: 11px;
  color: var(--ink-soft);
  line-height: 1.55;
}
.detail__facts {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px 10px;
  margin: 12px 0 0;
  padding: 10px 0;
  border-top: 1px dashed var(--line);
  border-bottom: 1px dashed var(--line);
}
.detail__facts div {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 10.5px;
  color: var(--ink-faint);
}
.detail__facts dd {
  margin: 0;
  color: var(--ink);
}
.detail__section {
  color: var(--ink-faint);
  margin: 12px 0 8px;
}
.detail__collen {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 7px;
}
.detail__col {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.detail__datatype {
  font-size: 9.5px;
  color: var(--ink-faint);
}
@media (max-width: 1279px) {
  .assets__grid {
    grid-template-columns: 180px minmax(0, 1fr);
  }
  .detail {
    grid-column: 1 / -1;
    position: static;
    max-height: none;
  }
}
</style>
