<template>
  <v-app>
    <v-main>
      <!-- App bar, will be present on all pages -->
      <v-app-bar
        v-if="$route.meta.showAppBar"
        :elevation="2"
        scroll-behavior="hide"
        class="app_bar"
        v-bind:class="{'hide_bar':!$route.meta.showAppBar}">
        <template v-slot:prepend>
          <v-menu>
            <template v-slot:activator="{ props }">
              <v-btn icon="mdi-dots-vertical" variant="text" v-bind="props"></v-btn>
            </template>

            <v-list>
              <v-list-item
                v-for="(item, i) in menuItems"
                :key="i"
                @click="item.click"
              >
                <v-list-item-title>{{ item.title }}</v-list-item-title>
              </v-list-item>
            </v-list>
          </v-menu>
        </template>

        <v-app-bar-title
          style="cursor: pointer"
          @click="() => $router.push('/')"
        >
          <v-icon>mdi-note</v-icon>
          M-HOME control
        </v-app-bar-title>
      </v-app-bar>

      <!-- App messenger -->
      <AppMessenger/>

      <!-- The router view will be rendered here -->
      <router-view/>
    </v-main>
  </v-app>
</template>

<script>
import router from "@/router";

export default {
  computed: {
    menuItems() {
      let items = [];
      router.getRoutes().forEach((route) => {
        console.log(route);
        if (route.meta && route.meta.showInMenu) {
          items.push({
            title: route.meta.title,
            click: () => this.$router.push(route.path),
          });
        }
      });
      items.push({
        title: 'Выход',
        click: () => this.$router.push('/login'),
      });
      return items;
    },
  },
  beforeUnmount() {
    this.$websocket.close();
  },
};
</script>

<style>
.app_bar {
  transition: max-height 0.5s;
  max-height: 100px;
  overflow: hidden;
}

.hide_bar {
  max-height: 0;
}
</style>
