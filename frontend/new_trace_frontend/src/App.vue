<script setup>
</script>

<template>
  <router-view />
</template>

<style>
/* 全局重置样式 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body {
  width: 100%;
  height: 100%;
  overflow: hidden;
  margin: 0;
  padding: 0;
}

#app {
  width: 100%;
  height: 100%;
  margin: 0;
  padding: 0;
  max-width: none !important;
  text-align: initial !important;
}
</style>
