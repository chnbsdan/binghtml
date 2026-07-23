# binghtml


基于 `bing` 项目数据，自动生成 WebP 格式图片和展示页面的升级版工具。

## 功能

- 从 `chnbsdan/bing` 项目获取图片数据
- 将 PNG 图片转换为 WebP 格式（体积缩小 70%+）
- 自动生成 `index.json` 和 `index.html`
- 部署到 `page` 分支，支持 Cloudflare Pages / EdgeOne

## 工作流程

1. GitHub Action 每天自动运行
2. 读取 `bing` 项目的最新 JSON 数据
3. 下载 PNG 图片并转换为 WebP
4. 生成 `page` 分支并推送

## 手动触发

在 Actions 页面点击 "Run workflow" 即可手动构建。
