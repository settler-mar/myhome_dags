// router/index.ts

import {createRouter, createWebHistory} from "vue-router/auto";

function setMeta(route, parentPath = '') {
  let path = parentPath + ('/' + route.path).replace('//', '/')
  let title = path.split('/').pop().replace(/([A-Z])/g, ' $1').trim().toLocaleLowerCase()
  title = title.charAt(0).toUpperCase() + title.slice(1)
  route.meta = {
    showAppBar: !['/login', '/register', '/', '/404'].includes(route.path),
    requiresAuth: path.startsWith('/configs/'),
    showInMenu: path.startsWith('/configs/'),
    title: title,
  }
  if ('children' in route) {
    route.children = route.children.map(child => setMeta(child, path))
  }
  return route
}

let router = createRouter({
  history: createWebHistory(),
  extendRoutes(routes) {
    return [
      ...routes.map(route => setMeta(route)),
      {
        path: '/:all(.*)',
        component: () => import('@/views/[...all].vue'),
        meta: {showAppBar: false},
      },
      {
        path: '/configs/users',
        component: () => import('@/views/TablePage.vue'),
        meta: {
          requiresAuth: true,
          showAppBar: true,
          showInMenu: true,
          title: 'Пользователи',
          tableModel: 'users',
        },
      },
      {
        path: '/configs/errors/:groupId/:logFile?',
        component: () => import('@/pages/configs/errors.vue'),
        meta: {
          requiresAuth: true,
          showAppBar: true,
          showInMenu: false,
          title: 'Errors',
        },
      },
    ]
  }
})

router.beforeEach((to, from, next) => {
  const isAuthenticated = checkAuth()

  if (isAuthenticated && ['/login'].includes(to.path)) {
    next('/')
  } else if ('/login' !== to.path && !isAuthenticated) {
    next('/login')
  } else {
    next()
  }
})

function checkAuth() {
  console.log('checkAuth', !!localStorage.getItem('token'))
  return !!localStorage.getItem('token')
}

export default router
