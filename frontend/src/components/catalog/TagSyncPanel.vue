<template>
  <section class="sync ink-panel">
    <header class="sync__head">
      <p class="smallcaps">敏感标签同步 SENSITIVE SYNC</p>
      <button class="btn btn--ghost sync__refresh" type="button" :disabled="loading" @click="loadPreview">
        刷新预览
      </button>
    </header>
    <p class="sync__lead mono">
      仅传播人工确认（manual）的 sensitive 标签：目标列缺标签才补，已有判断保留原结论，语义冲突列出跳过原因。
    </p>

    <ErrorNotice v-if="error" :message="error" />

    <div v-if="preview" class="sync__stats">
      <div class="sync__stat sync__stat--apply">
        <p class="smallcaps">补标 APPLY</p>
        <p class="sync__num numeric">{{ preview.summary.apply }}</p>
      </div>
      <div class="sync__stat sync__stat--skip">
        <p class="smallcaps">跳过 SKIPPED</p>
        <p class="sync__num numeric">{{ preview.summary.skipped }}</p>
      </div>
      <div class="sync__stat sync__stat--conflict">
        <p class="smallcaps">冲突 CONFLICT</p>
        <p class="sync__num numeric">{{ preview.summary.conflict }}</p>
      </div>
    </div>

    <ul v-if="preview?.items.length" class="sync__rows">
      <li
        v-for="(item, index) in preview.items"
        :key="`${item.source_column.id}-${item.tag.tag_name}-${item.target_column.id}-${index}`"
        class="sync-row"
        :class="`sync-row--${item.state}`"
      >
        <div class="sync-row__top">
          <span class="sync-row__state smallcaps">{{ stateLabel(item.state) }}</span>
          <TagStamp :tag-name="item.tag.tag_name" :source="item.tag.source" />
        </div>
        <p class="sync-row__path mono">
          {{ item.source_asset_key }}.<strong>{{ item.source_column.column_name }}</strong>
          <span class="sync-row__arrow">→</span>
          {{ item.target_asset_key }}.<strong>{{ item.target_column.column_name }}</strong>
        </p>
        <p class="sync-row__types mono">
          类型 {{ typeText(item.source_column.inferred_type) }} → {{ typeText(item.target_column.inferred_type) }}
        </p>
        <p v-if="item.reason" class="sync-row__reason mono">{{ item.reason }}</p>
      </li>
    </ul>
    <div v-else-if="preview && !loading" class="empty-state">
      该对表没有可传播的人工敏感标签（仅 manual 且 sensitive:* 才会同步）。
    </div>

    <div class="sync__actions">
      <button
        id="apply-tag-sync"
        class="btn btn--primary"
        type="button"
        :disabled="!canSync || loading || applying || !preview || preview.summary.apply === 0"
        :title="!canSync ? '当前角色无 tag:sync 权限' : '只补目标表缺失的敏感标签，重复执行不新增记录'"
        @click="submitApply"
      >
        {{ applying ? '应用中…' : `确认应用（补 ${preview?.summary.apply ?? 0} 标）` }}
      </button>
      <p v-if="lastResult" class="sync__last mono">
        本次实际新增 {{ lastResult.created }} 条；写入失败将整体回滚，两张表保持原样。
      </p>
      <p v-if="!canSync" class="smallcaps sync__readonly">当前角色无 tag:sync 权限</p>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import ErrorNotice from '../common/ErrorNotice.vue'
import TagStamp from '../common/TagStamp.vue'
import { applyTagSync, previewTagSync } from '../../api/duplicates'
import { usePermission } from '../../hooks/usePermission'
import { TAG_SYNC_STATE_LABELS, COLUMN_TYPE_LABELS } from '../../constants/enums'
import type { TagSyncPreview, TagSyncApplyResult } from '../../types/models'

const props = defineProps<{ pairId: string }>()

const perm = usePermission()
const canSync = perm.can('tag:sync')

const preview = ref<TagSyncPreview | null>(null)
const lastResult = ref<TagSyncApplyResult | null>(null)
const loading = ref(false)
const applying = ref(false)
const error = ref('')

function stateLabel(state: string) {
  return TAG_SYNC_STATE_LABELS[state] ?? state
}
function typeText(type: string | null | undefined) {
  return type ? (COLUMN_TYPE_LABELS[type as keyof typeof COLUMN_TYPE_LABELS] ?? type) : '未推断'
}

async function loadPreview() {
  if (!props.pairId) return
  loading.value = true
  error.value = ''
  try {
    preview.value = await previewTagSync(props.pairId)
  } catch (err) {
    preview.value = null
    error.value = (err as { message?: string }).message ?? '加载同步预览失败'
  } finally {
    loading.value = false
  }
}

async function submitApply() {
  if (!props.pairId) return
  applying.value = true
  error.value = ''
  try {
    lastResult.value = await applyTagSync(props.pairId)
    // 重新拉取应用后的权威预览：补标项此时应转为 skipped，计数与按钮状态即时归零
    await loadPreview()
  } catch (err) {
    error.value = (err as { message?: string }).message ?? '应用同步失败，已回滚未写入'
  } finally {
    applying.value = false
  }
}

watch(
  () => props.pairId,
  () => {
    lastResult.value = null
    loadPreview()
  },
  { immediate: true },
)
</script>

<style scoped>
.sync {
  padding: 12px;
  margin-top: 12px;
}
.sync__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.sync__head .smallcaps {
  color: var(--ink-faint);
}
.sync__refresh {
  font-size: 10px;
  padding: 2px 8px;
}
.sync__lead {
  margin-top: 6px;
  font-size: 10px;
  color: var(--ink-soft);
  line-height: 1.5;
}
.sync__stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
  margin-top: 10px;
}
.sync__stat {
  border: 1px solid var(--line);
  padding: 6px 8px;
  background: var(--sand-raise);
}
.sync__stat .smallcaps {
  font-size: 8.5px;
  color: var(--ink-faint);
}
.sync__num {
  font-family: var(--font-display);
  font-size: 22px;
  line-height: 1.1;
  margin-top: 2px;
}
.sync__stat--apply .sync__num {
  color: var(--moss);
}
.sync__stat--skip .sync__num {
  color: var(--ink-soft);
}
.sync__stat--conflict .sync__num {
  color: var(--brick);
}
.sync__rows {
  list-style: none;
  margin: 10px 0 0;
  padding: 0;
  display: grid;
  gap: 6px;
  max-height: 320px;
  overflow: auto;
}
.sync-row {
  border: 1px solid var(--line-soft);
  border-left-width: 3px;
  padding: 6px 8px;
  background: color-mix(in oklch, var(--sand-raise) 60%, transparent);
}
.sync-row--apply {
  border-left-color: var(--moss);
}
.sync-row--skipped {
  border-left-color: var(--ink-faint);
}
.sync-row--conflict {
  border-left-color: var(--brick);
  background: color-mix(in oklch, var(--brick-wash) 45%, transparent);
}
.sync-row__top {
  display: flex;
  align-items: center;
  gap: 8px;
}
.sync-row__state {
  font-size: 9px;
  letter-spacing: 0.08em;
  color: var(--ink-faint);
}
.sync-row--apply .sync-row__state {
  color: var(--moss);
}
.sync-row--conflict .sync-row__state {
  color: var(--brick);
}
.sync-row__path {
  margin-top: 5px;
  font-size: 10.5px;
  color: var(--ink);
  word-break: break-all;
}
.sync-row__arrow {
  color: var(--brick);
  margin: 0 4px;
}
.sync-row__types {
  margin-top: 2px;
  font-size: 9.5px;
  color: var(--ink-faint);
}
.sync-row__reason {
  margin-top: 3px;
  font-size: 9.5px;
  color: var(--brick-soft);
}
.sync__actions {
  margin-top: 12px;
  display: grid;
  gap: 6px;
}
.sync__last {
  font-size: 9.5px;
  color: var(--moss);
}
.sync__readonly {
  color: var(--brick);
  font-size: 9px;
}
</style>
