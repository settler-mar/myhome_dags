/**
 * main.js
 *
 * Bootstraps Vuetify and other plugins then mounts the App`
 */

// Plugins
import {registerPlugins} from "@/plugins";

// Components
import App from "./App.vue";

// Composables
import {createApp} from "vue";

// Services
import {webSocketService} from "./services/websocket.js";

const app = createApp(App);

app.config.globalProperties.$websocket = webSocketService;

app.config.errorHandler = function (err, vm, info) {
   console.log('errorHandler', err, vm, info);
  // handle error
  // `info` is a Vue-specific error info, e.g. which lifecycle hook
  // the error was found in. Only available in 2.2.0+
}

registerPlugins(app);


app.mount("#app");
