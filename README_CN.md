<p align="center"><img src= "https://github.com/1Panel-dev/maxkb/assets/52996290/c0694996-0eed-40d8-b369-322bf2a380bf" alt="MaxKB" width="260" /></p>
<h3 align="center">3C 数码售后助手（二开版）</h3>
<h3 align="center">在 MaxKB 基础上完成的业务化落地项目</h3>

本仓库不是从零重写平台，而是基于 MaxKB 做的二次开发，目标是把 3C 售后问答做成可上线、可控风险、可验证效果的版本。

原版 MaxKB 项目地址：
- https://github.com/1Panel-dev/maxkb

## 这次二开做了什么

- 增加售后模式开关：按知识库控制是否启用售后策略，便于灰度上线和回滚
- 优化知识处理：针对售后政策、SOP、产品说明书等内容优化切分，减少关键信息被切散
- 提升检索准确性：回答时更重视品牌、型号、SN/IMEI 等关键信息，降低答错型号概率
- 加强风险控制：证据不足时引导补充信息，不直接给高风险承诺
- 完成改造前后对照评测：用同口径数据对比 OFF/ON，确认业务价值提升

## 业务结果（简版）

- 改造前（baseline）首轮 292 题被服务调用异常严重影响，结果不能代表真实业务能力
- 改造后（200 题对照）在业务关键项上表现更好：
  - 回答可参考性提升
  - 高风险问题合规率提升
  - 平均响应速度提升

详细数据与过程见：
- `docs/after_sales_assistant/17_对照实验报告.md`
- `docs/after_sales_assistant/18_项目说明_面试版.md`
- `docs/after_sales_assistant/19_V1项目总结.md`

## 快速启动

```bash
docker run -d --name=maxkb --restart=always -p 8080:8080 -v ~/.maxkb:/opt/maxkb 1panel/maxkb
```

访问地址：
- http://127.0.0.1:8080

默认账号：
- 用户名：admin
- 密码：MaxKB@123..

## 说明

- 如果你想看原版平台完整介绍，请直接查看上面的原版项目链接
- 本 README 仅保留与本次二开交付直接相关的内容

<p align="center"><img src= "https://github.com/1Panel-dev/maxkb/assets/52996290/c0694996-0eed-40d8-b369-322bf2a380bf" alt="MaxKB" width="300" /></p>
<h3 align="center">强大易用的企业级智能体平台</h3>
<p align="center">
    <a href="https://trendshift.io/repositories/9113" target="_blank"><img src="https://trendshift.io/api/badge/repositories/9113" alt="1Panel-dev%2FMaxKB | Trendshift" style="width: 250px; height: auto;" /></a>
</p>
<p align="center">
  <a href="README_EN.md"><img src="https://img.shields.io/badge/English_README-blue" alt="English README"></a>
  <a href="https://www.gnu.org/licenses/gpl-3.0.html#license-text"><img src="https://img.shields.io/github/license/1Panel-dev/maxkb?color=%231890FF" alt="License: GPL v3"></a>
  <a href="https://github.com/1Panel-dev/maxkb/releases/latest"><img src="https://img.shields.io/github/v/release/1Panel-dev/maxkb" alt="Latest release"></a>
  <a href="https://github.com/1Panel-dev/maxkb"><img src="https://img.shields.io/github/stars/1Panel-dev/maxkb?style=flat-square" alt="Stars"></a>
  <a href="https://hub.docker.com/r/1panel/maxkb"><img src="https://img.shields.io/docker/pulls/1panel/maxkb?label=downloads" alt="Download"></a>
  <a href="https://gitee.com/fit2cloud-feizhiyun/MaxKB"><img src="https://gitee.com/fit2cloud-feizhiyun/MaxKB/badge/star.svg?theme=gvp" alt="Gitee Stars"></a>
  <a href="https://gitcode.com/feizhiyun/MaxKB"><img src="https://gitcode.com/feizhiyun/MaxKB/star/badge.svg" alt="GitCode Stars"></a>
</p>
<hr/>

MaxKB = Max Knowledge Brain，是一个强大易用的企业级智能体平台，致力于解决企业 AI 落地面临的技术门槛高、部署成本高、迭代周期长等问题，助力企业在人工智能时代赢得先机。秉承“开箱即用，伴随成长”的设计理念，MaxKB 支持企业快速接入主流大模型，高效构建专属知识库，并提供从基础问答（RAG）、复杂流程自动化（工作流）到智能体（Agent）的渐进式升级路径，全面赋能智能客服、智能办公助手等多种应用场景。

- **RAG 检索增强生成**：高效搭建本地 AI 知识库，支持直接上传文档 / 自动爬取在线文档，支持文本自动拆分、向量化，有效减少大模型幻觉，提升问答效果；
- **灵活编排**：内置强大的工作流引擎、函数库和 MCP 工具调用能力，支持编排 AI 工作过程，满足复杂业务场景下的需求；
- **无缝嵌入**：支持零编码快速嵌入到第三方业务系统，让已有系统快速拥有智能问答能力，提高用户满意度；
- **模型中立**：支持对接各种大模型，包括本地私有大模型（DeepSeek R1 / Qwen 3 等）、国内公共大模型（通义千问 / 腾讯混元 / 字节豆包 / 百度千帆 / 智谱 AI / Kimi / MiniMax 等）和国外公共大模型（OpenAI / Claude / Gemini 等）。

MaxKB 三分钟视频介绍：https://www.bilibili.com/video/BV18JypYeEkj/

## 快速开始

```
# Linux 机器
docker run -d --name=maxkb --restart=always -p 8080:8080 -v ~/.maxkb:/opt/maxkb registry.fit2cloud.com/maxkb/maxkb

# Windows 机器
docker run -d --name=maxkb --restart=always -p 8080:8080 -v C:/maxkb:/opt/maxkb registry.fit2cloud.com/maxkb/maxkb

# 用户名: admin
# 密码: MaxKB@123..
```

- 你也可以通过 [1Panel 应用商店](https://apps.fit2cloud.com/1panel) 快速部署 MaxKB；
- 如果是内网环境，推荐使用 [离线安装包](https://community.fit2cloud.com/#/products/maxkb/downloads) 进行安装部署；
- MaxKB 不同产品产品版本的对比请参见：[MaxKB 产品版本对比](https://maxkb.cn/price)；
- 如果您需要向团队介绍 MaxKB，可以使用这个 [官方 PPT 材料](https://fit2cloud.com/maxkb/download/introduce-maxkb_2026.pdf)。

如你有更多问题，可以查看使用手册，或者通过论坛与我们交流。

- [案例展示](USE-CASES.md)
- [使用手册](https://maxkb.cn/docs/)
- [论坛求助](https://bbs.fit2cloud.com/c/mk/11)
- 技术交流群

<image height="150px" width="150px" src="https://github.com/1Panel-dev/MaxKB/assets/52996290/a083d214-02be-4178-a1db-4f428124153a"/>

## UI 展示

<table style="border-collapse: collapse; border: 1px solid black;">
  <tr>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/user-attachments/assets/eb285512-a66a-4752-8941-c65ed1592238" alt="MaxKB Demo1"   /></td>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/user-attachments/assets/f732f1f5-472c-4fd2-93c1-a277eda83d04" alt="MaxKB Demo2"   /></td>
  </tr>
  <tr>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/user-attachments/assets/c927474a-9a23-4830-822f-5db26025c9b2" alt="MaxKB Demo3"   /></td>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/user-attachments/assets/e6268996-a46d-4e58-9f30-31139df78ad2" alt="MaxKB Demo4"   /></td>
  </tr>
</table>

## 技术栈

- 前端：[Vue.js](https://cn.vuejs.org/)
- 后端：[Python / Django](https://www.djangoproject.com/)
- LangChain：[LangChain](https://www.langchain.com/)
- 向量数据库：[PostgreSQL / pgvector](https://www.postgresql.org/)

## 飞致云的其他明星项目

- [Cordys CRM](https://github.com/1Panel-dev/CordysCRM) - 新一代的开源 AI CRM 系统
- [1Panel](https://github.com/1panel-dev/1panel/) - 现代化、开源的 Linux 服务器运维管理面板
- [JumpServer](https://github.com/jumpserver/jumpserver/) - 广受欢迎的开源堡垒机
- [DataEase](https://github.com/dataease/dataease/) - 人人可用的开源数据可视化分析工具
- [MeterSphere](https://github.com/metersphere/metersphere/) - 新一代的开源持续测试工具
- [Halo](https://github.com/halo-dev/halo/) - 强大易用的开源建站工具

## License

Copyright (c) 2014-2026 飞致云 FIT2CLOUD, All rights reserved.

Licensed under The GNU General Public License version 3 (GPLv3)  (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

<https://www.gnu.org/licenses/gpl-3.0.html>

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
