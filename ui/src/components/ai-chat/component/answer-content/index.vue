<template>
  <div class="item-content lighter">
    <div v-for="(answer_text, blockIdx) in answer_text_list" :key="blockIdx" class="mb-8">
      <div class="avatar mr-8" v-if="showAvatar">
        <img v-if="application.avatar" :src="application.avatar" height="28px" width="28px" />
        <LogoIcon v-else height="28px" width="28px" />
      </div>
      <div
        class="content"
        @mouseup="openControl"
        :style="{
          'padding-right': showUserAvatar ? 'var(--padding-left)' : '0',
        }"
      >
        <el-card shadow="always" class="border-r-8" style="--el-card-padding: 6px 16px">
          <div class="answer-md-area">
            <MdRenderer
              v-if="
                (chatRecord.write_ed === undefined || chatRecord.write_ed === true) &&
                answer_text.length == 0 &&
                answer_text
                  .map((item) => item.content)
                  .join('')
                  .trim().length == 0
              "
              :source="$t('chat.tip.answerMessage')"
            ></MdRenderer>
            <template v-else-if="answer_text.length > 0">
              <MdRenderer
                v-for="(answer, index) in answer_text"
                :key="index"
                :chat_record_id="answer.chat_record_id"
                :child_node="answer.child_node"
                :runtime_node_id="answer.runtime_node_id"
                :reasoning_content="answer.reasoning_content"
                :disabled="loading || type == 'log'"
                :source="formatAnswerForDisplay(answer.content, chatRecord.paragraph_list)"
                :send-message="chatMessage"
              ></MdRenderer>
            </template>
            <p v-else-if="chatRecord.is_stop" shadow="always" style="margin: 0.5rem 0">
              {{ $t('chat.tip.stopAnswer') }}
            </p>
            <p v-else shadow="always" style="margin: 0.5rem 0">
              {{ $t('chat.tip.answerLoading') }} <span class="dotting"></span>
            </p>
            <!-- 回答依据：右下角小标签，悬停展示知识库中的具体文档与片段（避免正文里括号 SOP 出处） -->
            <div
              v-if="showSourceFootnote(chatRecord, blockIdx)"
              class="answer-source-footnote"
            >
              <el-tooltip placement="top-end" effect="dark" :show-after="200">
                <template #content>
                  <div class="answer-source-footnote__tip">
                    <div class="answer-source-footnote__tip-title">回答依据：</div>
                    <div
                      v-for="(p, pi) in footnoteParagraphList(chatRecord)"
                      :key="pi"
                      class="answer-source-footnote__item"
                    >
                      <div class="answer-source-footnote__doc">{{ p.document_name }}</div>
                      <div class="answer-source-footnote__snippet">{{ truncateForFootnote(p.content) }}</div>
                    </div>
                  </div>
                </template>
                <span class="answer-source-footnote__chip" tabindex="0" title="鼠标悬停查看回答依据"
                  >回答依据</span
                >
              </el-tooltip>
            </div>
          </div>
          <!-- 知识来源 -->
          <KnowledgeSourceComponent
            :data="chatRecord"
            :application="application"
            :type="type"
            :appType="application.type"
            :executionIsRightPanel="props.executionIsRightPanel"
            @open-execution-detail="emit('openExecutionDetail')"
            @openParagraph="emit('openParagraph')"
            @openParagraphDocument="(val: string) => emit('openParagraphDocument', val)"
            v-if="showSource(chatRecord) && blockIdx === chatRecord.answer_text_list.length - 1"
          />
        </el-card>
      </div>
    </div>

    <div
      class="content"
      :style="{
        'padding-left': showAvatar ? 'var(--padding-left)' : '0',
        'padding-right': showUserAvatar ? 'var(--padding-left)' : '0',
      }"
      v-if="!selection"
    >
      <OperationButton
        :type="type"
        :application="application"
        :chatRecord="chatRecord"
        @update:chatRecord="(event: any) => emit('update:chatRecord', event)"
        :loading="loading"
        :start-chat="startChat"
        :stop-chat="stopChat"
        :regenerationChart="regenerationChart"
      ></OperationButton>
    </div>
  </div>
</template>
<script setup lang="ts">
import { computed, onMounted } from 'vue'
import KnowledgeSourceComponent from '@/components/ai-chat/component/knowledge-source-component/index.vue'
import MdRenderer from '@/components/markdown/MdRenderer.vue'
import OperationButton from '@/components/ai-chat/component/operation-button/index.vue'
import { type chatType } from '@/api/type/application'
import bus from '@/bus'
import { arraySort } from '@/utils/array'
import { formatAnswerForDisplay } from '@/utils/answerEvidence'

const props = defineProps<{
  chatRecord: chatType
  application: any
  loading: boolean
  sendMessage: (question: string, other_params_data?: any, chat?: chatType) => Promise<boolean>
  chatManagement: any
  type: 'log' | 'ai-chat' | 'debug-ai-chat' | 'share'
  executionIsRightPanel?: boolean
  selection?: boolean
}>()

const emit = defineEmits([
  'update:chatRecord',
  'openExecutionDetail',
  'openParagraph',
  'openParagraphDocument',
])

const showAvatar = computed(() => {
  return props.application.show_avatar == undefined ? true : props.application.show_avatar
})
const showUserAvatar = computed(() => {
  return props.application.show_user_avatar == undefined ? true : props.application.show_user_avatar
})
const chatMessage = (question: string, type: 'old' | 'new', other_params_data?: any) => {
  if (type === 'old') {
    add_answer_text_list(props.chatRecord.answer_text_list)
    props.sendMessage(question, other_params_data, props.chatRecord).then(() => {
      props.chatManagement.open(props.chatRecord.id)
      props.chatManagement.write(props.chatRecord.id)
    })
  } else {
    props.sendMessage(question, other_params_data)
  }
}
const add_answer_text_list = (answer_text_list: Array<any>) => {
  answer_text_list.push([])
}

const openControl = (event: any) => {
  if (props.type !== 'log') {
    bus.emit('open-control', event)
  }
}

const answer_text_list = computed(() => {
  return props.chatRecord.answer_text_list.map((item) => {
    if (typeof item == 'string') {
      return [
        {
          content: item,
          chat_record_id: undefined,
          child_node: undefined,
          runtime_node_id: undefined,
          reasoning_content: undefined,
        },
      ]
    } else if (item instanceof Array) {
      return item
    } else {
      return [item]
    }
  })
})

function showSource(row: any) {
  if (props.type === 'log') {
    return true
  } else if (row.write_ed && 500 !== row.status) {
    return true
  }
  return false
}

function showSourceFootnote(row: any, blockIdx: number) {
  if (!showSource(row) || blockIdx !== props.chatRecord.answer_text_list.length - 1) {
    return false
  }
  const n = row.paragraph_list?.length || 0
  return n > 0
}

function normalizeParagraphMeta(p: any) {
  const row = { ...p }
  if (row.meta && typeof row.meta === 'string') {
    try {
      row.meta = JSON.parse(row.meta)
    } catch {
      // 保持原样
    }
  }
  return row
}

function footnoteParagraphList(row: any) {
  const raw = row.paragraph_list || []
  const list = raw.map(normalizeParagraphMeta)
  return arraySort(list, 'similarity', true)
}

function truncateForFootnote(text: string | undefined, maxLen = 140) {
  const t = (text || '').replace(/\s+/g, ' ').trim()
  if (t.length <= maxLen) {
    return t
  }
  return `${t.slice(0, maxLen)}…`
}

const regenerationChart = (chat: chatType) => {
  const container = props.chatRecord?.upload_meta
    ? props.chatRecord.upload_meta
    : props.chatRecord.execution_details?.find((detail) => detail.type === 'start-node')

  props.sendMessage(chat.problem_text, {
    re_chat: true,
    image_list: container?.image_list || [],
    document_list: container?.document_list || [],
    audio_list: container?.audio_list || [],
    video_list: container?.video_list || [],
    other_list: container?.other_list || [],
  })
}
const stopChat = (chat: chatType) => {
  props.chatManagement.stop(chat.id)
}
const startChat = (chat: chatType) => {
  props.chatManagement.write(chat.id)
}

onMounted(() => {
  bus.on('chat:stop', () => {
    stopChat(props.chatRecord)
  })
})
</script>
<style lang="scss" scoped>
.answer-md-area {
  position: relative;
  padding-bottom: 36px;
}

.answer-source-footnote {
  position: absolute;
  right: 0;
  bottom: 2px;
  z-index: 2;
}

.answer-source-footnote__chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 22px;
  padding: 0 8px;
  font-size: 11px;
  line-height: 1;
  color: var(--el-color-primary);
  cursor: help;
  user-select: none;
  white-space: nowrap;
  border: 1px solid var(--el-color-primary-light-5);
  border-radius: 4px;
  background: var(--el-bg-color);
}

.answer-source-footnote__tip {
  max-width: 420px;
  max-height: 360px;
  overflow: auto;
  line-height: 1.45;
}

.answer-source-footnote__tip-title {
  margin-bottom: 8px;
  font-weight: 600;
}

.answer-source-footnote__item + .answer-source-footnote__item {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.12);
}

.answer-source-footnote__doc {
  margin-bottom: 4px;
  font-weight: 600;
}

.answer-source-footnote__snippet {
  font-size: 12px;
  opacity: 0.92;
  word-break: break-word;
}
</style>
