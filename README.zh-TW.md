<div align="center">

# 🕸️ CodeGraph-Lite

**🚀 輕量級代碼結構可視化工具 - 將代碼庫轉化為交互式知識圖譜**

[![npm version](https://img.shields.io/npm/v/codegraph-lite.svg?style=flat-square&color=blue)](https://www.npmjs.com/package/codegraph-lite)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://opensource.org/licenses/MIT)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.2-blue.svg?style=flat-square&logo=typescript)](https://www.typescriptlang.org/)
[![Node.js](https://img.shields.io/badge/Node.js-16+-green.svg?style=flat-square&logo=node.js)](https://nodejs.org/)

[English](README.md) | [简体中文](README.zh-CN.md) | [繁體中文](README.zh-TW.md)

</div>

---

## 🎉 項目介紹

**CodeGraph-Lite** 是一款專為開發者打造的輕量級代碼可視化工具。它通過解析代碼的AST（抽象語法樹），自動生成代碼知識圖譜，幫助開發者快速理解項目結構、發現代碼依賴關係、優化架構設計。

### 💡 靈感來源

本項目靈感來源於 GitHub Trending 上的熱門項目 [Understand-Anything](https://github.com/Lum1104/Understand-Anything)，但我們做了以下**差異化優化**：

- ✨ **更輕量** - 零配置即可使用，無需複雜依賴
- ⚡ **更快速** - 優化的AST解析引擎，大型項目秒級分析
- 🎨 **更美觀** - 精心設計的可視化界面，支持暗黑模式
- 🔧 **更易用** - 簡潔的CLI命令，支持多種導出格式
- 🌐 **更開放** - 完全開源，支持自定義擴展

### 🎯 解決的核心痛點

- 🤯 **新團隊成員** - 面對大型代碼庫不知從何入手
- 🔍 **代碼審查** - 難以快速理解代碼間的依賴關係
- 📊 **架構優化** - 缺乏直觀的架構視圖輔助決策
- 📚 **技術文檔** - 手動維護架構圖耗時費力

---

## ✨ 核心特性

### 🎨 **交互式可視化**
- 基於 D3.js 的力導向圖，支持拖拽、縮放、篩選
- 節點按類型著色（文件、函數、類、接口等）
- 實時搜索高亮，快速定位目標代碼

### 📊 **多維度分析**
- **結構視圖** - 文件、函數、類的層級關係
- **依賴視圖** - 導入、調用、繼承等依賴關係
- **統計視圖** - 代碼量、複雜度、語言分佈

### 🔧 **多語言支持**
- ✅ **TypeScript / JavaScript** - 完整支持
- 🚧 **Python** - 即將支持
- 🚧 **Go** - 即將支持
- 🚧 **更多語言** - 持續擴展中

### 📤 **靈活導出**
- **JSON** - 完整的圖譜數據
- **DOT** - Graphviz 格式，可生成靜態圖
- **CSV** - 節點和邊的表格數據

### ⚡ **高性能**
- 增量分析，只處理變更文件
- 並行解析，充分利用多核CPU
- 流式處理，支持大型代碼庫

---

## 🚀 快速開始

### 📋 環境要求

- **Node.js** >= 16.0.0
- **npm** >= 8.0.0

### 📦 安裝

```bash
# 全局安裝
npm install -g codegraph-lite

# 或使用 npx（無需安裝）
npx codegraph-lite --help
```

### 🔍 分析項目

```bash
# 分析當前目錄
codegraph analyze .

# 分析指定項目
codegraph analyze /path/to/your/project

# 自定義輸出路徑
codegraph analyze . -o ./output/my-graph.json
```

### 🌐 啟動可視化

```bash
# 啟動可視化服務器
codegraph visualize

# 指定端口
codegraph visualize -p 8080

# 自動打開瀏覽器
codegraph visualize --open
```

### 📊 查看統計

```bash
# 顯示代碼庫統計信息
codegraph stats

# 指定圖譜文件
codegraph stats -g ./custom-graph.json
```

---

## 📖 詳細使用指南

### 🔧 CLI 命令

```bash
# 分析命令
codegraph analyze <path> [options]
  -o, --output <file>      輸出文件路徑 (默認: .codegraph/graph.json)
  -i, --include <patterns> 包含文件模式 (默認: src/**/*)
  -e, --exclude <patterns> 排除文件模式 (默認: node_modules/**)
  --incremental            啟用增量分析 (默認: true)

# 可視化命令
codegraph visualize [options]
  -p, --port <number>      服務器端口 (默認: 3000)
  -g, --graph <file>       知識圖譜文件路徑 (默認: .codegraph/graph.json)
  --no-open               不自動打開瀏覽器

# 導出命令
codegraph export [options]
  -g, --graph <file>       知識圖譜文件路徑 (默認: .codegraph/graph.json)
  -f, --format <format>    導出格式: json|dot|csv (默認: json)
  -o, --output <file>      輸出文件路徑

# 統計命令
codegraph stats [options]
  -g, --graph <file>       知識圖譜文件路徑 (默認: .codegraph/graph.json)
```

### 🎨 可視化界面操作

| 操作 | 說明 |
|------|------|
| 🖱️ **拖拽節點** | 調整節點位置 |
| 🔍 **滾輪縮放** | 放大/縮小視圖 |
| 👆 **點擊節點** | 查看詳細信息 |
| 🔎 **搜索框** | 搜索並高亮節點 |
| ☑️ **類型篩選** | 按節點類型過濾 |
| ⚡ **物理引擎** | 開啟/關閉力導向動畫 |

### 📤 導出格式示例

**DOT 格式（Graphviz）**
```bash
codegraph export -f dot -o graph.dot
# 生成圖片: dot -Tpng graph.dot -o graph.png
```

**CSV 格式**
```bash
codegraph export -f csv -o graph.csv
# 可用 Excel 或數據分析工具打開
```

---

## 💡 設計思路與迭代規劃

### 🏗️ 架構設計

```
CodeGraph-Lite
├── Parser Core      # AST 解析引擎
├── Graph Builder    # 圖譜構建器
├── Visualizer       # 可視化服務器
└── CLI Interface    # 命令行接口
```

### 🎯 技術選型

- **TypeScript** - 類型安全，開發體驗佳
- **Babel Parser** - 強大的JS/TS AST解析
- **D3.js** - 業界標準的可視化庫
- **Express + WebSocket** - 實時交互服務器
- **Commander.js** - 優雅的CLI框架

### 📅 迭代計劃

#### v1.1.0（近期）
- [ ] Python 語言支持
- [ ] 更多導出格式（SVG、PNG）
- [ ] 代碼複雜度分析

#### v1.2.0（規劃中）
- [ ] Go 語言支持
- [ ] 差異分析模式
- [ ] CI/CD 集成

#### v2.0.0（願景）
- [ ] 插件系統
- [ ] 團隊協作功能
- [ ] 雲端託管

---

## 📦 打包與部署

### 🏗️ 本地構建

```bash
# 克隆倉庫
git clone https://github.com/gitstq/CodeGraph-Lite.git
cd CodeGraph-Lite

# 安裝依賴
npm install

# 構建
npm run build

# 本地測試
npm start -- analyze .
```

### 🐳 Docker 部署

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install --production
COPY dist ./dist
EXPOSE 3000
CMD ["node", "dist/cli.js", "visualize", "-p", "3000"]
```

### ☁️ 雲平台部署

支持一鍵部署到 Vercel、Netlify、Heroku 等平台。

---

## 🤝 貢獻指南

我們歡迎所有形式的貢獻！

### 📝 提交 Issue

- 使用清晰的標題描述問題
- 提供復現步驟和環境信息
- 附上錯誤日誌和截圖

### 🔧 提交 PR

1. Fork 本倉庫
2. 創建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'feat: add amazing feature'`)
4. 推送分支 (`git push origin feature/amazing-feature`)
5. 創建 Pull Request

### 📏 代碼規範

- 使用 TypeScript 嚴格模式
- 遵循 ESLint 配置
- 提交前運行測試 (`npm test`)
- 使用 [Conventional Commits](https://conventionalcommits.org/)

---

## 📄 開源協議

本項目採用 [MIT 協議](LICENSE) 開源。

---

## 🙏 致謝

- 靈感來源：[Understand-Anything](https://github.com/Lum1104/Understand-Anything)
- 可視化引擎：[D3.js](https://d3js.org/)
- AST解析：[Babel](https://babeljs.io/)

---

<div align="center">

**⭐ 如果這個項目對你有幫助，請給我們一個 Star！**

**💬 有任何問題或建議，歡迎提交 Issue 或 Discussion**

Made with ❤️ by [Lobster](https://github.com/gitstq)

</div>
