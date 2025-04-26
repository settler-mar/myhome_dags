/**
 * plugins/vuetify.js
 *
 * Framework documentation: https://vuetifyjs.com`
 */

// Styles
// import "@mdi/font/css/materialdesignicons.css";
import "vuetify/styles";

// Composables
import {createVuetify} from "vuetify";
import mIcon from '@/components/mIcons.vue';

// https://vuetifyjs.com/en/introduction/why-vuetify/#feature-guides
export default createVuetify({
  icons: {
    defaultSet: 'custom',
    sets: {
      custom: {
        component: mIcon,
      },
    },
  },
});
