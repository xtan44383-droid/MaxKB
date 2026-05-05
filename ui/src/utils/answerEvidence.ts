/**
 * 对话答案展示：去掉正文里杂乱的括号出处，并在「依据」小节编号项末尾注入可溯源脚标（使用全局 supPopover）。
 */
import { arraySort } from '@/utils/array'

function normalizeParagraphMeta(p: any) {
  const row = { ...p }
  if (row.meta && typeof row.meta === 'string') {
    try {
      row.meta = JSON.parse(row.meta)
    } catch {
      // 忽略解析失败
    }
  }
  return row
}

function truncateSnippet(text: string | undefined, maxLen: number) {
  const t = (text || '').replace(/\s+/g, ' ').trim()
  if (t.length <= maxLen) {
    return t
  }
  return `${t.slice(0, maxLen)}…`
}

/** 用于塞进 data-title：展示知识库真实文件名（可较长）+ 分段摘录；不使用模型随口写的「步骤1」类字样 */
function buildParagraphTooltipHtml(p: any) {
  const name = (p.document_name || '').trim() || '知识库文档'
  const snippet = truncateSnippet(p.content, 280)
  const esc = (s: string) =>
    s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  return (
    `<div style="max-width:440px;text-align:left;line-height:1.45">` +
    `<div style="font-size:12px;opacity:.85;margin-bottom:6px">来源：</div>` +
    `<div style="font-weight:600;word-break:break-all;margin-bottom:10px">${esc(name)}</div>` +
    `<div style="font-size:12px;opacity:.85;margin-bottom:4px">引用片段：</div>` +
    `<div style="font-size:12px;opacity:.95;word-break:break-word">${esc(snippet)}</div>` +
    `</div>`
  )
}

function escapeAttrDoubleQuoted(html: string) {
  return html.replace(/&/g, '&amp;').replace(/"/g, '&quot;')
}

/** 1→¹ … 9→⁹，超过 9 用普通数字避免排版怪异 */
function superscriptLabel(n: number) {
  const map = ['¹', '²', '³', '⁴', '⁵', '⁶', '⁷', '⁸', '⁹']
  if (n >= 1 && n <= 9) {
    return map[n - 1]
  }
  return `[${n}]`
}

/**
 * 去掉模型在正文里直接写出来的括号出处（含「来源：诊断步骤1」等），避免与脚标重复；
 * 真实可溯源信息统一走段落上的悬停浮层（document_name 来自知识库）。
 */
export function sanitizeAnswerDisplay(text: string | undefined) {
  if (!text) {
    return ''
  }
  let s = text
  s = s.replace(/\([^)]*[Ss][Oo][Pp][^)]*\)/g, '')
  s = s.replace(/（[^）]*[Ss][Oo][Pp][^）]*）/g, '')
  s = s.replace(/\([^)]*前置条件[^)]*\)/g, '')
  s = s.replace(/（[^）]*前置条件[^）]*）/g, '')
  // 模型常见的「（来源：xxx）」「（出处：xxx）」，含句号写在括号外的情况多跑一轮
  for (let k = 0; k < 3; k++) {
    s = s.replace(/（来源：[^）]*）\s*。?/g, '')
    s = s.replace(/\(来源：[^)]*\)\s*。?/g, '')
    s = s.replace(/（出处：[^）]*）\s*。?/g, '')
    s = s.replace(/\(出处：[^)]*\)\s*。?/g, '')
    s = s.replace(/（参见：[^）]*）\s*。?/g, '')
  }
  s = s.replace(/\s*。\s*。+/g, '。')
  s = s.replace(/[ \t]+\r?\n/g, '\n')
  s = s.replace(/\n{3,}/g, '\n\n')
  return s
}

/**
 * 在「依据」小节的每条编号末尾追加 <sup data-title="...">脚标</sup>，与 paragraph_list 按顺序对应（不足则循环映射）。
 */
export function injectBasisSupFootnotes(text: string, paragraphList: any[] | undefined) {
  if (!text || !paragraphList?.length) {
    return text
  }
  const sorted = arraySort(paragraphList.map(normalizeParagraphMeta), 'similarity', true)

  const lines = text.split(/\r?\n/)
  let mode: 'seek' | 'basis' = 'seek'
  let basisLineCount = 0

  const enterBasis = (line: string) => {
    const t = line.trim()
    if (/^(#{1,6}\s*)依据\s*[：:]?\s*$/.test(t)) {
      return true
    }
    if (/^(#{1,6}\s*)\*\*依据\*\*\s*[：:]?\s*$/.test(t)) {
      return true
    }
    if (/^\*\*依据[：:]\*\*\s*$/.test(t)) {
      return true
    }
    if (/^\*\*依据\s*[：:]\*\*\s*$/.test(t)) {
      return true
    }
    if (/^\*\*依据\*\*\s*[：:]/.test(t)) {
      return true
    }
    if (/^依据\s*[：:]/.test(t)) {
      return true
    }
    return false
  }

  const leaveBasis = (line: string) => {
    const t = line.trim()
    if (/^(#{1,6}\s*)(保修规则|建议操作|结论)(\s|：|:|$)/.test(t)) {
      return true
    }
    if (/^(#{1,6}\s*)\*\*(保修规则|建议操作|结论)\*\*/.test(t)) {
      return true
    }
    if (/^\*\*(保修规则|建议操作|结论)/.test(t)) {
      return true
    }
    return false
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    if (mode === 'seek') {
      if (enterBasis(line)) {
        mode = 'basis'
      }
      continue
    }
    if (mode === 'basis') {
      if (leaveBasis(line)) {
        mode = 'seek'
        continue
      }
      if (/^\s*\d+([\.、．）)])\s*.+/.test(line) && !line.includes('<sup')) {
        basisLineCount += 1
        const p = sorted[(basisLineCount - 1) % sorted.length]
        const tip = buildParagraphTooltipHtml(p)
        const attr = escapeAttrDoubleQuoted(tip)
        const sup = `<sup data-title="${attr}">${superscriptLabel(basisLineCount)}</sup>`
        lines[i] = `${line.trimEnd()} ${sup}`
      }
    }
  }

  return lines.join('\n')
}

export function formatAnswerForDisplay(raw: string | undefined, paragraphList: any[] | undefined) {
  const cleaned = sanitizeAnswerDisplay(raw)
  return injectBasisSupFootnotes(cleaned, paragraphList)
}
