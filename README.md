<p align="center">
  <img src="./ui/public/theme/default.jpg" alt="3C数码售后助手" width="420" />
</p>

<h3 align="center">3C 数码售后助手（二次开发版）</h3>

<p align="center">基于开源项目 <a href="https://github.com/1Panel-dev/MaxKB">MaxKB</a> 的领域化改造与业务交付实现。</p>

<hr/>

本仓库在 MaxKB 之上针对「3C 数码售后」场景做了二次开发：在保留平台原有能力的前提下，增加可开关的领域策略、检索与安全管控，并完成对照评测；配套演示库与 Text2SQL 工作流联调说明见 `mock_data/text2sql/`。原版产品介绍请以 MaxKB 官方仓库为准。

## 二次开发概要

- 知识库级「售后模式」开关（默认关闭，切换仅影响后续导入），导入侧按售后文档形态增强分段并写入结构化元数据。
- 检索侧对品牌、型号、SN/IMEI 等信号加权，降低错型号、错规则召回。
- 对话链路：弱证据拒答与高风险承诺后置拦截；售后上下文下边侧寒暄类问题可走固定短回复以降低怪异版式。
- Text2SQL：画布侧完成演示库只读查询链路；平台在 `ToolExecutor` 执行前对 `sql` 入参统一剥离 Markdown 代码围栏，并在 `database=after_sales_demo` 时执行与演示工具一致的只读白名单校验（`apps/common/utils/demo_sql_gate.py`）。
- 管理端品牌化与登录体验调整，与「3C 数码售后助手」对外口径一致。

## 评测摘要（200 题扩样本，售后模式 OFF → ON）

以下为业务侧主指标摘录（细则与实验条件曾在交付文档中记录，此处仅保留摘要口径）。

| 指标 | OFF → ON |
|------|-----------|
| business_useful_rate | 0.85 → 1.0 |
| high_risk_compliance_rate | 约 0.8049 → 1.0 |
| refusal_correct_rate | 约 0.3333 → 0.5（拒答子样本较少，作辅证） |
| avg_latency_s | 约 6.21 → 约 4.46 |

关键词子串通过率可能随合规收紧而下降，解读时应以业务可用性与高风险合规为主指标。

## 快速启动（沿用 MaxKB 官方镜像）

```bash
docker run -d --name=maxkb --restart=always -p 8080:8080 -v ~/.maxkb:/opt/maxkb 1panel/maxkb
```

默认管理员账号与密码请以 MaxKB 官方文档为准。

## 本地开发与前端静态资源

如需在本仓库修改 `ui/` 后在本机 Django 集成环境查看效果：

```bash
bash scripts/build-ui-static.sh
```

然后重启 Web 进程并强刷浏览器。

说明：`README_CN.md` 与本文内容一致（便于习惯中文文件名的读者打开）。

## License

沿用 MaxKB 项目所使用的 GNU General Public License v3（GPLv3），详见仓库根目录 `LICENSE`。
