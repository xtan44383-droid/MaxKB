<template>
  <img
    v-if="theme.themeInfo?.loginLogo"
    :src="fileURL"
    alt="3C数码售后助手"
    height="45px"
    class="mr-8"
  />
  <!-- 使用 DOM 文本而非 SVG <text>，避免部分环境下中文显示为问号 -->
  <span
    v-else
    class="logo-full-wordmark mr-8"
    :class="isDefaultTheme ? 'logo-full-wordmark--default' : 'logo-full-wordmark--custom'"
    :style="wordmarkStyle"
  >3C数码售后助手</span>
</template>
<script setup lang="ts">
import { computed } from 'vue'
import useStore from '@/stores'
defineOptions({ name: 'LogoFull' })

const props = defineProps({
  height: {
    type: String,
    default: '36px',
  },
})
const { theme } = useStore()
const isDefaultTheme = computed(() => {
  return theme.isDefaultTheme()
})

const fileURL = computed(() => {
  if (theme.themeInfo) {
    if (typeof theme.themeInfo?.loginLogo === 'string') {
      return theme.themeInfo?.loginLogo
    } else {
      return URL.createObjectURL(theme.themeInfo?.loginLogo)
    }
  } else {
    return ''
  }
})

// height 为整块 Logo 区域高度，正文字号按比例缩小（原 SVG 约 17px 对应 36～45 区域）
const wordmarkStyle = computed(() => {
  const n = parseInt(String(props.height), 10) || 36
  const fs = Math.min(22, Math.max(14, Math.round(n * 0.44)))
  return {
    fontSize: `${fs}px`,
    lineHeight: `${n}px`,
  }
})
</script>
<style lang="scss" scoped>
.logo-full-wordmark {
  font-family:
    system-ui,
    -apple-system,
    'Segoe UI',
    'PingFang SC',
    'Microsoft YaHei',
    'Noto Sans SC',
    sans-serif;
  font-weight: 700;
  display: inline-block;
  white-space: nowrap;
}
.logo-full-wordmark--default {
  color: #0d9488;
}
.logo-full-wordmark--custom {
  color: var(--el-color-primary);
}
</style>
