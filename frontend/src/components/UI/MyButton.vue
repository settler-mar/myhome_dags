<template>
  <button class="btn">
    <slot></slot>
  </button>
</template>

<script>
export default {
  name: 'my-button'
}
</script>

<style scoped>
.btn {
  position: relative;
  display: block;
  padding: 11px 0 10px 0;
  color: #fffeee;
  margin: 0 auto;
  background: #68b706;
  font-size: 18px;
  text-align: center;
  font-style: normal;
  width: 100%;
  border: 1px solid #81c13b;
  border-width: 1px 1px 3px;
  margin-bottom: 10px;
  line-height: normal;
  max-width: 240px;
  margin-top: 35px;
  cursor: pointer;
}

.btn-sm {
  height: auto;
  padding: 1px 10px;
  width: auto;
  margin: 0;
  font-size: 14px;
}
.btn-mm{
  height: auto;
  padding: 1px 1px;
  width: auto;
  margin: 1px;
  font-size: 18px;
}

.btn-ms {
  /*height: auto;*/
  padding: 5px 10px;
  /*width: auto;*/
  margin-top: 10px;
  font-size: 14px;
}

.btn-red {
  background: #b70d0e;
  border: 1px solid #e81113;
}

:disabled {
  background: #b9b9b9;
  border-color: #8f8f8f;
}
</style>
