<template>
  <div class="tags">
    <PageHeader
      title="标签与敏感列"
      eyebrow="04 / TAG LEGEND"
      subtitle="语义标签分 manual / inferred 两种来源；数据管家可对推断出的手机号 / 身份证 / 邮箱列补打 sensitive 标签并导出目录。"
    >
      <template #actions>
        <TagFilterBar v-model="activeCategory" :options="categoryOptions" />
      </template>
    </PageHeader>

    <ErrorNotice v-if="error" :message="error" />

    <section class="tags__stats">
      <div class="stat ink-panel">
        <p class="smallcaps">标签总数 TAGS</p>
        <p class="stat__value numeric">{{ tags.total }}</p>
      </div>
      <div class="stat ink-panel">
        <p class="smallcaps">敏感列 SENSITIVE</p>
        <p class="stat__value numeric stat__value--hot">{{ tags.summary?.sensitive_columns ?? 0 }}</p>
      </div>
      <div class="stat ink-panel">
        <p class="smallcaps">人工 MANUAL</p>
        <p class="stat__value numeric">{{ tags.summary?.by_source?.manual ?? 0 }}</p>
      </div>
      <div class="stat ink-panel">
        <p class="smallcaps">算法 INFERRED</p>
        <p class="stat__value numeric">{{ tags.summary?.by_source?.inferred ?? 0 }}</p>
      </div>
    </section>

    <div class="tags__grid">
      <section class="taglist ink-panel">
        <header class="taglist__head">
          <span class="smallcaps">标签清单 TAG INDEX</span>
          <span class="mono">{{ filteredTags.length }} 条</span>
        </header>
        <ul class="taglist__rows">
          <li v-for="tag in filteredTags" :key="tag.id" class="tag-row">
            <div class="tag-row__left">
              <TagStamp :tag-name="tag.tag_name" :source="tag.source" />
              <p class="tag-row__column mono">
                {{ tag.asset.asset_key }}<span class="tag-row__dot">·</span>{{ tag.column.column_name }}
              </p>
            </div>
            <div class="tag-row__right mono">
              <span class="tag-row__cat smallcaps">{{ categoryLabel(tag.category) }}</span>
              <span class="tag-row__conf numeric">{{ (tag.confidence * 100).toFixed(0) }}%</span>
              <span class="tag-row__by">{{ tag.tagged_by }}</span>
            </div>
          </li>
        </ul>
      </section>

      <aside class="candidates ink-panel">
        <p class="smallcaps candidates__title">敏感列待复核 CANDIDATES</p>
        <p class="candidates__lead mono">
          下列列已被算法推断为 PII 类型但还没有 sensitive 标签；勾选后批量补标（viewer 也可执行）。
        </p>
        <ul class="candidates__rows">
          <li v-for="column in candidates" :key="column.id" class="candidate-row">
            <label class="candidate-row__label">
              <input v-model="selectedIds" type="checkbox" :value="column.id" />
              <ColumnChip
                :column-name="column.column_name"
                :type="column.inferred_type"
                :confidence="column.confidence"
              />
              <span class="candidate-row__asset mono">{{ column.asset?.asset_key }}</span>
            </label>
          </li>
        </ul>
        <div v-if="!candidates.length" class="empty-state">没有待复核的 PII 列，或已在加载中。</div>

        <div class="candidates__form">
          <label class="field">
            <span class="field__label">批量标签 TAG</span>
            <input id="bulk-tag-name" v-model="tagName" class="mono" type="text" />
          </label>
          <button
            id="bulk-tag-submit"
            class="btn btn--primary"
            type="button"
            :disabled="!selectedIds.length || tagging || !perm.can('tag:write')"
            @click="submitBulk"
          >
            {{ tagging ? '打标中…' : `批量打标（${selectedIds.length}）` }}
          </button>
        </div>
        <p class="candidates__note smallcaps">标签来源记录为 manual，并写入 audit_log。</p>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import PageHeader from '../components/common/PageHeader.vue'
import ErrorNotice from '../components/common/ErrorNotice.vue'
import TagStamp from '../components/common/TagStamp.vue'
import ColumnChip from '../components/common/ColumnChip.vue'
import TagFilterBar from '../components/catalog/TagFilterBar.vue'
import { bulkTag, fetchTags } from '../api/tags'
import { fetchColumns } from '../api/columns'
import { usePermission } from '../hooks/usePermission'
import type { ColumnItem, TagRow } from '../types/models'
import { TAG_CATEGORY_LABELS } from '../constants/enums'

const perm = usePermission()
const tags = ref<{
  items: TagRow[]
  total: number
  summary?: { by_category: Record<string, number>; by_source: Record<string, number>; sensitive_columns: number }
}>({ items: [], total: 0 })
const columns = ref<ColumnItem[]>([])
const activeCategory = ref('')
const selectedIds = ref<string[]>([])
const tagName = ref('sensitive:high')
const tagging = ref(false)
const error = ref('')

const filteredTags = computed(() => {
  const items = tags.value.items ?? []
  if (!activeCategory.value) return items
  return items.filter((tag) => tag.category === activeCategory.value)
})

const candidates = computed(() => {
  const sensitiveColumns = new Set(
    (tags.value.items ?? [])
      .filter((tag) => tag.tag_name.startsWith('sensitive:'))
      .map((tag) => tag.column.id),
  )
  return columns.value
    .filter((column) => ['phone', 'id_card', 'email'].includes(column.inferred_type ?? ''))
    .filter((column) => !sensitiveColumns.has(column.id))
    .slice(0, 8)
})

const categoryOptions = computed(() => [
  { value: '', label: '全部', count: tags.value.total },
  { value: 'pii', label: '隐私', count: tags.value.summary?.by_category?.pii ?? 0 },
  { value: 'business', label: '业务', count: tags.value.summary?.by_category?.business ?? 0 },
  { value: 'governance', label: '治理', count: tags.value.summary?.by_category?.governance ?? 0 },
])

function categoryLabel(category: string) {
  return TAG_CATEGORY_LABELS[category] ?? category
}

async function loadTags() {
  try {
    tags.value = await fetchTags({})
  } catch (err) {
    error.value = (err as { message?: string }).message ?? '读取标签失败'
  }
}

async function loadCandidates() {
  try {
    const data = await fetchColumns({ only_profiled: true, page_size: 200 })
    columns.value = data.items
  } catch {
    columns.value = []
  }
}

async function submitBulk() {
  if (!selectedIds.value.length) return
  tagging.value = true
  error.value = ''
  try {
    await bulkTag([...selectedIds.value], tagName.value.trim(), 'pii')
    selectedIds.value = []
    await Promise.all([loadTags(), loadCandidates()])
  } catch (err) {
    error.value = (err as { message?: string }).message ?? '打标失败'
  } finally {
    tagging.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadTags(), loadCandidates()])
})
</script>

<style scoped>
.tags__stats {
  display: flex;
  gap: 8px;
  margin-bottom: 14px;
}
.stat {
  padding: 8px 14px;
  min-width: 104px;
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
.tags__grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 400px;
  gap: 14px;
  align-items: start;
}
.taglist {
  overflow: hidden;
}
.taglist__head {
  display: flex;
  justify-content: space-between;
  padding: 9px 12px;
  border-bottom: 1px solid var(--ink);
  color: var(--ink-faint);
}
.taglist__rows {
  list-style: none;
  margin: 0;
  padding: 0;
}
.tag-row {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  padding: 8px 12px;
  border-bottom: 1px dashed var(--line-soft);
  align-items: center;
}
.tag-row__left {
  min-width: 0;
}
.tag-row__column {
  margin-top: 4px;
  font-size: 10.5px;
  color: var(--ink-soft);
  word-break: break-all;
}
.tag-row__dot {
  margin: 0 5px;
  color: var(--ink-faint);
}
.tag-row__right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
  font-size: 10px;
  color: var(--ink-faint);
}
.tag-row__cat {
  font-size: 8.5px;
  border: 1px solid var(--line);
  padding: 1px 5px;
}
.tag-row__conf {
  color: var(--moss);
}
.tag-row__by {
  max-width: 130px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.candidates {
  padding: 12px;
  position: sticky;
  top: 14px;
}
.candidates__title {
  color: var(--ink-faint);
}
.candidates__lead {
  margin-top: 6px;
  font-size: 10px;
  color: var(--ink-soft);
  line-height: 1.5;
}
.candidates__rows {
  list-style: none;
  margin: 12px 0 0;
  padding: 0;
  display: grid;
  gap: 6px;
}
.candidate-row__label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}
.candidate-row__asset {
  font-size: 9.5px;
  color: var(--ink-faint);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.candidates__form {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px dashed var(--line);
  display: grid;
  gap: 8px;
}
.candidates__note {
  margin-top: 8px;
  color: var(--ink-faint);
  font-size: 8.5px;
}
@media (max-width: 1279px) {
  .tags__grid {
    grid-template-columns: 1fr;
  }
  .candidates {
    position: static;
  }
}
</style>
