<template>
  <span
    class="column-chip"
    :class="[`column-chip--${type || 'unknown'}`, { 'is-manual': source === 'manual' }]"
    :title="`${columnName} · ${typeLabel} · 置信度 ${confidenceText}`"
  >
    <span class="column-chip__name mono">{{ columnName }}</span>
    <span class="column-chip__type smallcaps">{{ typeLabel }}</span>
    <span v-if="source === 'manual'" class="column-chip__flag">人工</span>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ColumnSemanticType } from '../../types/models'
import { COLUMN_TYPE_LABELS } from '../../constants/enums'

const props = defineProps<{
  columnName: string
  type?: ColumnSemanticType | null
  confidence?: number
  source?: string | null
}>()

const typeLabel = computed(() => COLUMN_TYPE_LABELS[props.type ?? 'unknown'] ?? '未知')
const confidenceText = computed(() => `${Math.round((props.confidence ?? 0) * 100)}%`)
</script>

<style scoped>
.column-chip {
  display: inline-flex;
  align-items: baseline;
  gap: 6px;
  padding: 2px 7px;
  border: 1px solid var(--line);
  border-bottom-width: 2px;
  border-radius: var(--radius-sm);
  background: var(--sand-raise);
  white-space: nowrap;
}
.column-chip__name {
  font-size: 11.5px;
  color: var(--ink);
}
.column-chip__type {
  font-size: 9px;
  color: var(--ink-faint);
}
.column-chip__flag {
  font-size: 9px;
  color: var(--brick);
  border-left: 1px solid var(--line);
  padding-left: 6px;
}
.column-chip--phone,
.column-chip--id_card {
  border-bottom-color: var(--brick);
}
.column-chip--email {
  border-bottom-color: var(--gold);
}
.column-chip--amount {
  border-bottom-color: var(--moss);
}
.column-chip--datetime {
  border-bottom-color: var(--moss-soft);
}
.column-chip--enum {
  border-bottom-color: var(--ink-faint);
}
.column-chip--ambiguous {
  border-bottom-color: var(--gold);
  border-bottom-style: dashed;
}
.column-chip--unknown {
  border-bottom-color: var(--line);
  color: var(--ink-soft);
}
.column-chip--phone .column-chip__type,
.column-chip--id_card .column-chip__type {
  color: var(--brick);
}
.column-chip.is-manual {
  background: var(--brick-wash);
}
</style>
