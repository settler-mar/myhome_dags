/**
 * router/index.ts
 *
 * Automatic routes for `./src/pages/*.vue`
 * Doc ? https://github.com/hannoeru/vite-plugin-pages
 */

// Composable
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
    return [...routes.map(route => setMeta(route)),
      {
        path: '/:all(.*)',
        component: () => import('@/views/[...all].vue'),
        meta: {showAppBar: false}
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
    ]
  }
});

// Middleware для маршрутов /config/*
router.beforeEach((to, from, next) => {
  const isAuthenticated = checkAuth()

  // Блокируем доступ к авторизации/регистрации после входа
  if (isAuthenticated && ['/login'].includes(to.path)) {
    next('/')
  }
  // Перенаправляем на страницу входа, если пользователь не авторизован
  else if ('/login' !== to.path && !isAuthenticated) {
    // Защита маршрутов, требующих авторизации
    next('/login')
  } else {
    next()
  }
})

// Пример функции проверки авторизации
function checkAuth() {
  // Логика проверки (например, наличие токена)
  console.log('checkAuth', !!localStorage.getItem('token'))
  // localStorage.setItem('token', '123123')
  return !!localStorage.getItem('token')
}

// Logs created routes
// console.log(router.getRoutes());


export default router;
