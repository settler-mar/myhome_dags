<template>
  <v-container>
    <v-row justify="center">
      <v-col cols="12" sm="8" md="4">
        <v-card>
          <v-card-title>Вход</v-card-title>
          <v-card-text>
            <v-form @submit.prevent="login">
              <v-text-field
                v-model="loginData.username"
                label="Логин"
                required
              ></v-text-field>
              <v-text-field
                v-model="loginData.password"
                label="Пароль"
                type="password"
                required
              ></v-text-field>
              <v-btn type="submit" color="primary">Войти</v-btn>
            </v-form>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import authStore from "@/store/auth";
// import messagesStore from "@/store/messages";
import {mapStores} from "pinia";

export default {
  data() {
    return {
      loginData: {
        username: '',
        password: '',
      },
    };
  },
  computed: {
    ...mapStores(authStore),
  },
  methods: {
    login() {
      console.log('login', this.loginData);
      this.authStore.login(this.loginData);
    },
  },
};
</script>
