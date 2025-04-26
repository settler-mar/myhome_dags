import {createApp} from "vue";
import App from "./App.vue";
import mIcon from '@/components/mIcons.vue';
import {registerPlugins} from "@/plugins";
import {webSocketService} from "./services/websocket.js";

const fontStyle = document.createElement('link');
fontStyle.rel = 'stylesheet';
fontStyle.href = '/api/fonts/style.css';
document.head.appendChild(fontStyle);

const app = createApp(App);

app.component('m-icon', mIcon);
app.component('v-icon', mIcon); // Переопределяем <v-icon>

app.config.globalProperties.$websocket = webSocketService;

app.config.errorHandler = function (err, vm, info) {
  console.log('errorHandler', err, vm, info);
};

registerPlugins(app);
app.mount("#app");
