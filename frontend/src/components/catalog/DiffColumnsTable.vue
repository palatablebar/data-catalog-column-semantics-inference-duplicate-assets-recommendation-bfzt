<template>
  <div class="diff">
    <div class="diff__head">
      <span class="smallcaps">{{ leftTitle }}</span>
      <span class="smallcaps diff__center">列级对照</span>
      <span class="smallcaps">{{ rightTitle }}</span>
    </div>
    <ul class="diff__rows">
      <li v-for="(row, index) in rows" :key="index" class="diff__row" :class="`diff__row--${row.state}`">
        <div class="diff__cell">
          <template v-if="row.left_column">
            <ColumnChip
              :column-name="row.left_column.column_name"
              :type="row.left_column.inferred_type"
              :confidence="row.left_column.confidence"
            />
          </template>
          <span v-else class="diff__void mono">—</span>
        </div>
        <div class="diff__link">
          <span v-if="row.state === 'shared'" class="diff__match mono">
            {{ Math.round((row.similarity || 1) * 100) }}%
          </span>
          <span v-else class="diff__gap mono">{{ row.state === 'left_only' ? '仅左' : '仅右' }}</span>
        </div>
        <div class="diff__cell diff__cell--right">
          <template v-if="row.right_column">
            <ColumnChip
              :column-name="row.right_column.column_name"
              :type="row.right_column.inferred_type"
              :confidence="row.right_column.confidence"
            />
          </template>
          <span v-else class="diff__void mono">—</span>
        </div>
      </li>
    </ul>
    <div class="diff__foot mono">
      共享列 {{ sharedCount }} · 仅左 {{ leftOnlyCount }} · 仅右 {{ rightOnlyCount }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { DiffRow } from '../../types/models'
import ColumnChip from '../common/ColumnChip.vue'

const props = defineProps<{ rows: DiffRow[]; leftTitle: string; rightTitle: string }>()

const sharedCount = computed(() => props.rows.filter((row) => row.state === 'shared').length)
const leftOnlyCount = computed(() => props.rows.filter((row) => row.state === 'left_only').length)
const rightOnlyCount = computed(() => props.rows.filter((row) => row.state === 'right_only').length)
</script>

<style scoped>
.diff {
  border: 1px solid var(--line);
  background: color-mix(in oklch, var(--sand-raise) 68%, transparent);
}
.diff__head {
  display: grid;
  grid-template-columns: 1fr 64px 1fr;
  gap: 8px;
  padding: 8px 12px;
  border-bottom: 1px solid var(--ink);
  color: var(--ink-faint);
}
.diff__center {
  text-align: center;
}
.diff__rows {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: 420px;
  overflow: auto;
}
.diff__row {
  display: grid;
  grid-template-columns: 1fr 64px 1fr;
  gap: 8px;
  align-items: center;
  padding: 5px 12px;
  border-bottom: 1px dashed var(--line-soft);
}
.diff__row--left_only {
  background: color-mix(in oklch, var(--brick-wash) 40%, transparent);
}
.diff__row--right_only {
  background: color-mix(in oklch, var(--moss-wash) 45%, transparent);
}
.diff__cell {
  min-width: 0;
  overflow: hidden;
}
.diff__cell--right {
  display: flex;
  justify-content: flex-end;
}
.diff__link {
  text-align: center;
}
.diff__match {
  font-size: 10px;
  color: var(--moss);
  border-bottom: 1px solid var(--moss-soft);
}
.diff__gap {
  font-size: 9px;
  color: var(--brick);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}
.diff__void {
  color: var(--ink-faint);
}
.diff__foot {
  padding: 7px 12px;
  font-size: 10px;
  color: var(--ink-soft);
  border-top: 1px solid var(--line);
}
</style>
