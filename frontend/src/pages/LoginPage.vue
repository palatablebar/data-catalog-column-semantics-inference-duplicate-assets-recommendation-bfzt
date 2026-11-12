<template>
  <div class="login atlas-surface">
    <div class="contour-field"></div>
    <section class="cover">
      <p class="smallcaps cover__sheet">SHEET 556 · DATA CATALOG SURVEY</p>
      <h1 class="cover__title">城市测绘<br /><em>地图册</em></h1>
      <p class="cover__lead">
        合川零售 · 数据治理组。4000 张表散落在 8 个数仓 schema 里，
        这里把「找哪张表、哪张表重复、哪列是敏感列」画成一张可检索的地图。
      </p>
      <dl class="cover__meta">
        <div><dt class="smallcaps">SHEETS</dt><dd class="numeric">42</dd></div>
        <div><dt class="smallcaps">COLUMNS</dt><dd class="numeric">320</dd></div>
        <div><dt class="smallcaps">SURVEYORS</dt><dd class="numeric">5</dd></div>
      </dl>
      <ul class="cover__accounts">
        <li><span class="mono">admin@catmap.demo</span><span class="smallcaps">平台管理员</span></li>
        <li><span class="mono">analyst@catmap.demo</span><span class="smallcaps">数据分析</span></li>
        <li><span class="mono">viewer@catmap.demo</span><span class="smallcaps">数据管家</span></li>
      </ul>
      <p class="cover__hint smallcaps">演示口令统一 Demo@2026</p>
    </section>

    <section class="panel">
      <div class="panel__head">
        <p class="smallcaps">ENTRY No. 001</p>
        <h2 class="panel__title">入库登记</h2>
        <p class="panel__sub">使用数据治理组账号进入测绘台</p>
      </div>
      <form class="panel__form" @submit.prevent="submit">
        <label class="field">
          <span class="field__label">邮箱 EMAIL</span>
          <input
            id="login-email"
            v-model="email"
            type="email"
            name="email"
            autocomplete="username"
            placeholder="admin@catmap.demo"
          />
        </label>
        <label class="field">
          <span class="field__label">口令 PASSWORD</span>
          <input
            id="login-password"
            v-model="password"
            type="password"
            name="password"
            autocomplete="current-password"
            placeholder="Demo@2026"
          />
        </label>
        <ErrorNotice v-if="error" :message="error" />
        <button id="login-submit" class="btn btn--primary panel__submit" type="submit" :disabled="auth.loading">
          {{ auth.loading ? '登记中…' : '进入地图册 →' }}
        </button>
      </form>
      <p class="panel__foot smallcaps">JWT · 3 ROLES · AUDIT LOGGED</p>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import ErrorNotice from '../components/common/ErrorNotice.vue'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const email = ref('admin@catmap.demo')
const password = ref('Demo@2026')
const error = ref('')

async function submit() {
  error.value = ''
  try {
    await auth.login(email.value.trim(), password.value)
    const redirect = (route.query.redirect as string) || '/assets'
    await router.push(redirect)
  } catch (err) {
    error.value = (err as { message?: string }).message ?? '登录失败'
  }
}
</script>

<style scoped>
.login {
  position: relative;
  min-height: 100vh;
  display: grid;
  grid-template-columns: 1.15fr 0.85fr;
  overflow: hidden;
}
.cover {
  position: relative;
  z-index: 1;
  padding: 76px clamp(36px, 6vw, 96px) 48px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  border-right: 1px solid var(--ink);
}
.cover__sheet {
  color: var(--brick);
}
.cover__title {
  font-size: clamp(46px, 6vw, 82px);
  line-height: 0.95;
  letter-spacing: 0.02em;
}
.cover__title em {
  color: var(--moss);
  font-style: italic;
}
.cover__lead {
  max-width: 46ch;
  color: var(--ink-soft);
  font-size: 13px;
  line-height: 1.7;
  border-left: 2px solid var(--brick);
  padding-left: 14px;
}
.cover__meta {
  display: flex;
  gap: 34px;
  margin: 6px 0 0;
}
.cover__meta dt {
  color: var(--ink-faint);
  margin-bottom: 2px;
}
.cover__meta dd {
  margin: 0;
  font-family: var(--font-display);
  font-size: 26px;
}
.cover__accounts {
  list-style: none;
  margin: 10px 0 0;
  padding: 14px 0 0;
  border-top: 1px dashed var(--line);
  display: grid;
  gap: 5px;
  max-width: 330px;
}
.cover__accounts li {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 11px;
  color: var(--ink-soft);
}
.cover__accounts .smallcaps {
  color: var(--ink-faint);
  font-size: 8.5px;
}
.cover__hint {
  color: var(--brick);
}
.panel {
  position: relative;
  z-index: 1;
  align-self: center;
  margin: 40px clamp(24px, 4vw, 64px);
  padding: 30px 30px 22px;
  border: 1px solid var(--ink);
  background: color-mix(in oklch, var(--sand-raise) 88%, transparent);
  box-shadow: 8px 8px 0 color-mix(in oklch, var(--ink) 8%, transparent);
}
.panel__head {
  border-bottom: 1px solid var(--line);
  padding-bottom: 14px;
  margin-bottom: 18px;
}
.panel__head .smallcaps {
  color: var(--brick);
}
.panel__title {
  font-size: 27px;
  margin-top: 2px;
}
.panel__sub {
  margin-top: 4px;
  font-size: 11px;
  color: var(--ink-soft);
}
.panel__form {
  display: grid;
  gap: 14px;
}
.panel__submit {
  justify-content: center;
  margin-top: 4px;
  padding: 9px 14px;
}
.panel__foot {
  margin-top: 18px;
  color: var(--ink-faint);
  border-top: 1px dashed var(--line);
  padding-top: 10px;
  text-align: center;
}
@media (max-width: 1023px) {
  .login {
    grid-template-columns: 1fr;
  }
  .cover {
    border-right: 0;
    border-bottom: 1px solid var(--ink);
    padding: 40px 24px 28px;
  }
}
</style>
