<template>
  <div class="shell atlas-surface">
    <div class="contour-field"></div>
    <aside class="rail">
      <div class="rail__brand">
        <p class="smallcaps rail__sheet">SHEET 556 · HECHUAN</p>
        <h1 class="rail__title">CATMAP</h1>
        <p class="rail__subtitle">数据目录测绘台</p>
      </div>

      <nav class="rail__nav">
        <RouterLink
          v-for="item in NAV_ITEMS"
          :key="item.path"
          :to="item.path"
          class="rail__link"
          :class="{ 'is-active': route.path.startsWith(item.path) }"
        >
          <span class="rail__index mono">{{ item.index }}</span>
          <span class="rail__linktext">
            <span class="rail__label">{{ item.label }}</span>
            <span class="rail__hint smallcaps">{{ item.hint }}</span>
          </span>
        </RouterLink>
      </nav>

      <div class="rail__legend">
        <p class="smallcaps rail__legendtitle">SURVEY NOTES</p>
        <dl class="rail__stats">
          <div><dt>资产</dt><dd class="numeric">{{ overview?.assets ?? '—' }}</dd></div>
          <div><dt>列</dt><dd class="numeric">{{ overview?.columns ?? '—' }}</dd></div>
          <div><dt>敏感列</dt><dd class="numeric">{{ overview?.sensitive_columns ?? '—' }}</dd></div>
          <div><dt>待确认重复</dt><dd class="numeric">{{ overview?.pending_pairs ?? '—' }}</dd></div>
        </dl>
      </div>

      <div class="rail__user">
        <RoleBadge v-if="auth.user" :role="auth.user.role" />
        <p class="rail__email mono">{{ auth.user?.email ?? '未登录' }}</p>
        <button class="rail__logout smallcaps" type="button" @click="logout">登出 LOG OUT</button>
      </div>
    </aside>

    <div class="main">
      <header class="legendbar">
        <span class="legendbar__coord mono">N 30°39′12″ · E 104°03′41″ · SCALE 1:500</span>
        <span class="legendbar__rule"></span>
        <span class="legendbar__meta mono">
          {{ overview?.completed_jobs ?? 0 }} INGEST RUNS · {{ overview?.inferred_columns ?? 0 }} COLUMNS SURVEYED
        </span>
      </header>
      <main class="page">
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/authStore'
import { useCatalogStore } from '../../stores/catalogStore'
import { NAV_ITEMS } from '../../constants/routes'
import RoleBadge from './RoleBadge.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const catalog = useCatalogStore()
const overview = computed(() => catalog.overview)

onMounted(() => {
  catalog.refresh()
})

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.shell {
  display: grid;
  grid-template-columns: var(--nav-width) 1fr;
  min-height: 100vh;
}
.rail {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 26px;
  padding: 26px 18px 18px;
  border-right: 1px solid var(--ink);
  background: color-mix(in oklch, var(--sand-raise) 62%, transparent);
  backdrop-filter: blur(1px);
}
.rail__sheet {
  color: var(--brick);
  margin-bottom: 6px;
}
.rail__title {
  font-size: 28px;
  letter-spacing: 0.1em;
  line-height: 1;
}
.rail__subtitle {
  margin-top: 6px;
  font-size: 11.5px;
  color: var(--ink-soft);
  letter-spacing: 0.22em;
}
.rail__nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.rail__link {
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding: 8px 6px;
  color: var(--ink-soft);
  border-left: 2px solid transparent;
  transition:
    border-color 200ms var(--ease),
    background 200ms var(--ease),
    color 200ms var(--ease);
}
.rail__link:hover {
  text-decoration: none;
  background: color-mix(in oklch, var(--sand-deep) 55%, transparent);
  color: var(--ink);
}
.rail__link.is-active {
  border-left-color: var(--moss);
  color: var(--ink);
  background: color-mix(in oklch, var(--moss-wash) 52%, transparent);
}
.rail__index {
  font-size: 10px;
  color: var(--brick);
}
.rail__linktext {
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.rail__label {
  font-family: var(--font-display);
  font-size: 15px;
}
.rail__hint {
  font-size: 8.5px;
  color: var(--ink-faint);
}
.rail__legend {
  margin-top: auto;
  border-top: 1px dashed var(--line);
  padding-top: 14px;
}
.rail__legendtitle {
  color: var(--ink-faint);
  margin-bottom: 8px;
}
.rail__stats {
  margin: 0;
  display: grid;
  gap: 4px;
}
.rail__stats div {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: var(--ink-soft);
}
.rail__stats dd {
  margin: 0;
  color: var(--ink);
}
.rail__user {
  display: flex;
  flex-direction: column;
  gap: 6px;
  border-top: 1px solid var(--line);
  padding-top: 12px;
}
.rail__email {
  font-size: 10.5px;
  color: var(--ink-soft);
  word-break: break-all;
}
.rail__logout {
  background: none;
  border: 0;
  padding: 0;
  text-align: left;
  color: var(--brick);
  font-size: 9px;
  letter-spacing: 0.14em;
}
.rail__logout:hover {
  text-decoration: underline;
}
.main {
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.legendbar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 10px 30px;
  border-bottom: 1px solid var(--line);
  background: color-mix(in oklch, var(--sand-raise) 55%, transparent);
  font-size: 10px;
  color: var(--ink-faint);
}
.legendbar__rule {
  flex: 1;
  height: 1px;
  background: repeating-linear-gradient(
    90deg,
    var(--line) 0 8px,
    transparent 8px 14px
  );
}
.page {
  padding: 22px 30px 40px;
  min-width: 0;
}
@media (max-width: 1023px) {
  .shell {
    grid-template-columns: 1fr;
  }
  .rail {
    border-right: 0;
    border-bottom: 1px solid var(--ink);
  }
  .rail__nav {
    flex-direction: row;
    flex-wrap: wrap;
  }
  .rail__legend {
    display: none;
  }
}
</style>
