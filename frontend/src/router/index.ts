import { createRouter, createWebHistory } from 'vue-router'
import { setupGuards } from './guards'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/assets' },
    {
      path: '/login',
      name: 'login',
      component: () => import('../pages/LoginPage.vue'),
      meta: { public: true },
    },
    { path: '/assets', name: 'assets', component: () => import('../pages/AssetsPage.vue') },
    { path: '/columns', name: 'columns', component: () => import('../pages/ColumnsPage.vue') },
    { path: '/duplicates', name: 'duplicates', component: () => import('../pages/DuplicatesPage.vue') },
    { path: '/tags', name: 'tags', component: () => import('../pages/TagsPage.vue') },
    { path: '/ingest', name: 'ingest', component: () => import('../pages/IngestPage.vue') },
    { path: '/:pathMatch(.*)*', redirect: '/assets' },
  ],
})

setupGuards(router)

export default router
