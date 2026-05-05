<template>
  <svg
    :class="!isDefaultTheme ? 'custom-logo-color' : 'default-logo-tone'"
    :height="height"
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 48 48"
    fill="none"
    aria-hidden="true"
  >
    <title>3C数码售后助手</title>
    <rect width="48" height="48" rx="12" fill="currentColor" fill-opacity="0.12" />
    <path
      fill="currentColor"
      d="M24 10c-4.5 0-8 3.2-8.8 7.4-.1.4-.5.7-1 .7h-1.6c-1.2 0-2.1 1-2.1 2.2v4.2c0 1.1.9 2 2 2h1.2c.8 4.2 4.3 7.3 8.8 7.3h1.4c4.5 0 8-3.1 8.8-7.3h1.2c1.1 0 2-.9 2-2v-4.2c0-1.2-.9-2.2-2.1-2.2H34c-.5 0-.9-.3-1-.7C32.1 13.2 28.5 10 24 10Zm-4 14.5a2.5 2.5 0 1 1 0-5 2.5 2.5 0 0 1 0 5Zm8 0a2.5 2.5 0 1 1 0-5 2.5 2.5 0 0 1 0 5ZM14 18.5l-2.2-1.1c-.4-.2-.6-.7-.4-1.1.2-.4.7-.6 1.1-.4L14 17v1.5Zm20 0V17l1.5-.8c.4-.2.9 0 1.1.4.2.4 0 .9-.4 1.1L34 18.5ZM24 34c-2 0-3.5 1.4-3.5 3.2V38h7v-.8c0-1.8-1.6-3.2-3.5-3.2h-1Z"
    />
  </svg>
</template>
<script setup lang="ts">
import { computed } from 'vue'
import useStore from '@/stores'
defineOptions({ name: 'LogoIcon' })

defineProps({
  height: {
    type: String,
    default: '36px',
  },
})
const { theme } = useStore()
const isDefaultTheme = computed(() => {
  return theme.isDefaultTheme()
})
</script>
<style lang="scss" scoped>
.custom-logo-color {
  color: var(--el-color-primary);
}
.default-logo-tone {
  color: #0d9488;
}
</style>
