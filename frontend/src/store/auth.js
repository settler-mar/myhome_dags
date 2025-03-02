import {defineStore, mapStores} from "pinia";
import {ref, computed} from "vue";
import {webSocketService} from "@/services/websocket";
import useMessageStore from "@/store/messages";
import {secureFetch} from "@/services/fetch";

const store = defineStore("auth", {
  // load data from localStorage (user, token)
  state: () => {
    const user = localStorage.getItem("user") || null;
    const token = localStorage.getItem("token") || null;
    const user_data = JSON.parse(localStorage.getItem("user_data")) || null;
    return {
      user: ref(user),
      token: ref(token),
      user_data: ref(user_data),
    };
  },
  actions: {
    async login({username, password}) {
      const MessageStore = useMessageStore();
      try {
        const response = secureFetch(`/api/token`, {
          method: 'POST',
          dataType: 'url',
          data: {username, password,},
        });
        const auth = await response;
        const status = auth.status;
        const auth_data = await auth.json();
        if (status === 200) {
          MessageStore.addMessage({
            type: "success",
            message: "Login successful",
          });
          const {access_token} = auth_data;
          this.token = access_token;
          this.user = username;
          localStorage.setItem("user", username);
          localStorage.setItem("token", access_token);

          const user_req = secureFetch(`/api/me/`)
          const user_data = await user_req;
          this.user_data = user_data.json();
          localStorage.setItem("user_data", JSON.stringify(user_data));
          console.log('auth ok')
          // redirect
          const redirect = localStorage.getItem('redirect') || '/'
          localStorage.removeItem('redirect');
          location.href = redirect;
          return 'ok'
        }
        if (status === 401) {
          MessageStore.addMessage({
            type: "error",
            message: auth_data.detail || "Login failed",
          });
          return 'error'
        }
      } catch (error) {
        console.error("Error:", error);
      }
    },
    logout() {
      console.log('logout')
      localStorage.removeItem("user");
      localStorage.removeItem("token");
      localStorage.removeItem("user_data");
      this.user = null;
      this.token = null;
      // useMessageStore().clear();
      location.href = '/login';
    },
  },
  computed: {
  },
})

export default store;
