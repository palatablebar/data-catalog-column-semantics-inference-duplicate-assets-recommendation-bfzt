<template>
  <div class="ingest">
    <PageHeader
      title="采集任务"
      eyebrow="05 / INGEST LOG"
      subtitle="Celery worker 读取 schema sample 的 5 张样例表，逐列统计空值率 / 基数 / 长度分布并写入列统计，供语义推断使用。"
    >
      <template #actions>
        <button
          id="run-ingest"
          class="btn btn--primary"
          type="button"
          :disabled="!perm.can('ingest:run') || running"
          :title="perm.can('ingest:run') ? '对 5 张样例表发起采集' : '仅平台管理员可跑采集'"
          @click="runJob"
        >
          {{ running ? '采集进行中…' : '运行采集' }}
        </button>
        <PermissionHint v-if="!perm.can('ingest:run')" label="仅管理员可跑采集" />
      </template>
    </PageHeader>

    <ErrorNotice v-if="error" :message="error" />

    <section class="cards">
      <div class="card ink-panel">
        <p class="smallcaps">列采样覆盖率 COVERAGE</p>
        <p class="card__value numeric">{{ percent(overview?.coverage) }}</p>
        <p class="card__hint mono">
          {{ overview?.profiled_columns ?? 0 }} / {{ overview?.total_columns ?? 0 }} 列已采样
        </p>
      </div>
      <div class="card ink-panel">
        <p class="smallcaps">样例表 SAMPLE TABLES</p>
        <p class="card__value numeric">{{ overview?.sample_assets ?? 0 }}</p>
        <p class="card__hint mono">每表 300 行 · 共 1500 行</p>
      </div>
      <div class="card ink-panel">
        <p class="smallcaps">人工纠正 MANUAL</p>
        <p class="card__value numeric">{{ overview?.manual_columns ?? 0 }}</p>
        <p class="card__hint mono">inference_source = manual</p>
      </div>
      <div class="card ink-panel">
        <p class="smallcaps">最近完成 LAST DONE</p>
        <p class="card__value card__value--sm mono">
          {{ overview?.last_completed ? shortTime(overview.last_completed.finished_at) : '—' }}
        </p>
        <p class="card__hint mono">{{ overview?.last_completed?.job_name ?? '暂无完成记录' }}</p>
      </div>
    </section>

    <div class="ingest__grid">
      <section class="joblist ink-panel">
        <header class="joblist__head">
          <span class="smallcaps">采集台账 JOB LOG</span>
          <span class="mono">queued {{ counts.queued ?? 0 }} · running {{ counts.running ?? 0 }} · done {{ counts.completed ?? 0 }}</span>
        </header>
        <ul class="joblist__rows">
          <li
            v-for="job in jobs"
            :key="job.id"
            class="job-row"
            :class="{ 'is-selected': selectedId === job.id }"
            @click="selectJob(job.id)"
          >
            <div class="job-row__main">
              <span class="job-row__name mono">{{ job.job_name }}</span>
              <JobStatusTag :status="job.status" />
            </div>
            <p class="job-row__scope mono">{{ job.scope }}</p>
            <p class="job-row__meta mono">
              {{ job.connection_name }} · {{ job.triggered_by }} · {{ shortTime(job.started_at) }}
            </p>
          </li>
        </ul>
      </section>

      <aside class="jobdetail ink-panel">
        <div v-if="!detail" class="empty-state">选择左侧任务查看采集统计。</div>
        <template v-else>
          <p class="smallcaps jobdetail__eyebrow">{{ detail.status.toUpperCase() }} · INGEST RUN</p>
          <h3 class="jobdetail__title">{{ detail.job_name }}</h3>
          <p class="jobdetail__scope mono">{{ detail.scope }}</p>
          <dl class="jobdetail__facts">
            <div><dt>连接</dt><dd class="mono">{{ detail.connection_name }}</dd></div>
            <div><dt>触发人</dt><dd class="mono">{{ detail.triggered_by }}</dd></div>
            <div><dt>开始</dt><dd class="mono">{{ shortTime(detail.started_at) }}</dd></div>
            <div><dt>结束</dt><dd class="mono">{{ shortTime(detail.finished_at) }}</dd></div>
          </dl>
          <p class="smallcaps jobdetail__label">采集统计 STATS</p>
          <dl class="jobdetail__stats">
            <div v-for="(value, key) in detail.stats" :key="key">
              <dt class="mono">{{ key }}</dt>
              <dd class="numeric">{{ value }}</dd>
            </div>
          </dl>
          <p v-if="detail.error_message" class="jobdetail__error mono">{{ detail.error_code }} · {{ detail.error_message }}</p>
        </template>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import PageHeader from '../components/common/PageHeader.vue'
import ErrorNotice from '../components/common/ErrorNotice.vue'
import PermissionHint from '../components/common/PermissionHint.vue'
import JobStatusTag from '../components/catalog/JobStatusTag.vue'
import { fetchIngestOverview, fetchJobs, runIngest } from '../api/ingest'
import { useJobPolling } from '../hooks/useJobPolling'
import { usePermission } from '../hooks/usePermission'
import type { IngestJob } from '../types/models'
import { percent, shortTime } from '../utils/format'

const perm = usePermission()
const jobs = ref<IngestJob[]>([])
const counts = ref<Record<string, number>>({})
const overview = ref<Record<string, any> | null>(null)
const selectedId = ref('')
const detail = ref<IngestJob | null>(null)
const error = ref('')
const running = ref(false)
const { poll } = useJobPolling((job) => {
  detail.value = job
  if (job.status === 'completed' || job.status === 'failed') {
    running.value = false
    loadAll()
  }
})

async function loadAll() {
  try {
    const [jobData, overviewData] = await Promise.all([fetchJobs(20), fetchIngestOverview()])
    jobs.value = jobData.items
    counts.value = jobData.counts
    overview.value = overviewData
    if (!selectedId.value && jobs.value.length) {
      selectedId.value = jobs.value[0].id
      detail.value = jobs.value[0]
    }
  } catch (err) {
    error.value = (err as { message?: string }).message ?? '读取采集任务失败'
  }
}

function selectJob(jobId: string) {
  selectedId.value = jobId
  detail.value = jobs.value.find((job) => job.id === jobId) ?? null
}

async function runJob() {
  running.value = true
  error.value = ''
  try {
    const job = await runIngest()
    selectedId.value = job.id
    detail.value = job
    await loadAll()
    poll(job.id)
  } catch (err) {
    running.value = false
    error.value = (err as { message?: string }).message ?? '发起采集失败'
  }
}

onMounted(loadAll)
</script>

<style scoped>
.cards {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  margin-bottom: 14px;
}
.card {
  padding: 10px 14px;
  color: var(--ink-faint);
}
.card__value {
  font-family: var(--font-display);
  font-size: 28px;
  color: var(--ink);
  line-height: 1.15;
  margin-top: 2px;
}
.card__value--sm {
  font-size: 15px;
  padding-top: 8px;
}
.card__hint {
  margin-top: 3px;
  font-size: 9.5px;
  color: var(--ink-faint);
}
.ingest__grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 14px;
  align-items: start;
}
.joblist {
  overflow: hidden;
}
.joblist__head {
  display: flex;
  justify-content: space-between;
  padding: 9px 12px;
  border-bottom: 1px solid var(--ink);
  color: var(--ink-faint);
  font-size: 9.5px;
}
.joblist__rows {
  list-style: none;
  margin: 0;
  padding: 0;
}
.job-row {
  padding: 9px 12px;
  border-bottom: 1px dashed var(--line-soft);
  cursor: pointer;
}
.job-row:hover {
  background: color-mix(in oklch, var(--moss-wash) 38%, transparent);
}
.job-row.is-selected {
  background: color-mix(in oklch, var(--moss-wash) 66%, transparent);
  box-shadow: inset 2px 0 0 var(--moss);
}
.job-row__main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.job-row__name {
  font-size: 12px;
}
.job-row__scope {
  margin-top: 3px;
  font-size: 10px;
  color: var(--ink-soft);
}
.job-row__meta {
  margin-top: 2px;
  font-size: 9.5px;
  color: var(--ink-faint);
}
.jobdetail {
  padding: 14px;
  position: sticky;
  top: 14px;
}
.jobdetail__eyebrow {
  color: var(--brick);
}
.jobdetail__title {
  font-size: 20px;
  margin-top: 2px;
}
.jobdetail__scope {
  margin-top: 4px;
  font-size: 10.5px;
  color: var(--ink-soft);
}
.jobdetail__facts {
  display: grid;
  gap: 3px;
  margin: 12px 0;
  padding: 10px 0;
  border-top: 1px dashed var(--line);
  border-bottom: 1px dashed var(--line);
}
.jobdetail__facts div {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  font-size: 10.5px;
  color: var(--ink-faint);
}
.jobdetail__facts dd {
  margin: 0;
  color: var(--ink);
  text-align: right;
}
.jobdetail__label {
  color: var(--ink-faint);
  margin-bottom: 6px;
}
.jobdetail__stats {
  display: grid;
  gap: 3px;
  margin: 0;
}
.jobdetail__stats div {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  font-size: 10.5px;
}
.jobdetail__stats dt {
  color: var(--ink-faint);
}
.jobdetail__stats dd {
  margin: 0;
  color: var(--ink);
}
.jobdetail__error {
  margin-top: 12px;
  border: 1px solid var(--brick-soft);
  background: var(--brick-wash);
  color: var(--brick);
  padding: 7px 9px;
  font-size: 10px;
}
@media (max-width: 1279px) {
  .cards {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .ingest__grid {
    grid-template-columns: 1fr;
  }
  .jobdetail {
    position: static;
  }
}
</style>
