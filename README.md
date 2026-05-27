<div align="center">

# 🕸️ CodeGraph-Lite

**🚀 轻量级代码结构可视化工具 - 将代码库转化为交互式知识图谱**

[![npm version](https://img.shields.io/npm/v/codegraph-lite.svg?style=flat-square&color=blue)](https://www.npmjs.com/package/codegraph-lite)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://opensource.org/licenses/MIT)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.2-blue.svg?style=flat-square&logo=typescript)](https://www.typescriptlang.org/)
[![Node.js](https://img.shields.io/badge/Node.js-16+-green.svg?style=flat-square&logo=node.js)](https://nodejs.org/)

[English](README.md) | [简体中文](README.zh-CN.md) | [繁體中文](README.zh-TW.md)

</div>

---

## 🎉 项目介绍

**CodeGraph-Lite** 是一款专为开发者打造的轻量级代码可视化工具。它通过解析代码的AST（抽象语法树），自动生成代码知识图谱，帮助开发者快速理解项目结构、发现代码依赖关系、优化架构设计。

### 💡 灵感来源

本项目灵感来源于 GitHub Trending 上的热门项目 [Understand-Anything](https://github.com/Lum1104/Understand-Anything)，但我们做了以下**差异化优化**：

- ✨ **更轻量** - 零配置即可使用，无需复杂依赖
- ⚡ **更快速** - 优化的AST解析引擎，大型项目秒级分析
- 🎨 **更美观** - 精心设计的可视化界面，支持暗黑模式
- 🔧 **更易用** - 简洁的CLI命令，支持多种导出格式
- 🌐 **更开放** - 完全开源，支持自定义扩展

### 🎯 解决的核心痛点

- 🤯 **新团队成员** - 面对大型代码库不知从何入手
- 🔍 **代码审查** - 难以快速理解代码间的依赖关系
- 📊 **架构优化** - 缺乏直观的架构视图辅助决策
- 📚 **技术文档** - 手动维护架构图耗时费力

---

## ✨ 核心特性

### 🎨 **交互式可视化**
- 基于 D3.js 的力导向图，支持拖拽、缩放、筛选
- 节点按类型着色（文件、函数、类、接口等）
- 实时搜索高亮，快速定位目标代码

### 📊 **多维度分析**
- **结构视图** - 文件、函数、类的层级关系
- **依赖视图** - 导入、调用、继承等依赖关系
- **统计视图** - 代码量、复杂度、语言分布

### 🔧 **多语言支持**
- ✅ **TypeScript / JavaScript** - 完整支持
- 🚧 **Python** - 即将支持
- 🚧 **Go** - 即将支持
- 🚧 **更多语言** - 持续扩展中

### 📤 **灵活导出**
- **JSON** - 完整的图谱数据
- **DOT** - Graphviz 格式，可生成静态图
- **CSV** - 节点和边的表格数据

### ⚡ **高性能**
- 增量分析，只处理变更文件
- 并行解析，充分利用多核CPU
- 流式处理，支持大型代码库

---

## 🚀 快速开始

### 📋 环境要求

- **Node.js** >= 16.0.0
- **npm** >= 8.0.0

### 📦 安装

```bash
# 全局安装
npm install -g codegraph-lite

# 或使用 npx（无需安装）
npx codegraph-lite --help
```

### 🔍 分析项目

```bash
# 分析当前目录
codegraph analyze .

# 分析指定项目
codegraph analyze /path/to/your/project

# 自定义输出路径
codegraph analyze . -o ./output/my-graph.json
```

### 🌐 启动可视化

```bash
# 启动可视化服务器
codegraph visualize

# 指定端口
codegraph visualize -p 8080

# 自动打开浏览器
codegraph visualize --open
```

### 📊 查看统计

```bash
# 显示代码库统计信息
codegraph stats

# 指定图谱文件
codegraph stats -g ./custom-graph.json
```

---

## 📖 详细使用指南

### 🔧 CLI 命令

```bash
# 分析命令
codegraph analyze <path> [options]
  -o, --output <file>      输出文件路径 (默认: .codegraph/graph.json)
  -i, --include <patterns> 包含文件模式 (默认: src/**/*)
  -e, --exclude <patterns> 排除文件模式 (默认: node_modules/**)
  --incremental            启用增量分析 (默认: true)

# 可视化命令
codegraph visualize [options]
  -p, --port <number>      服务器端口 (默认: 3000)
  -g, --graph <file>       知识图谱文件路径 (默认: .codegraph/graph.json)
  --no-open               不自动打开浏览器

# 导出命令
codegraph export [options]
  -g, --graph <file>       知识图谱文件路径 (默认: .codegraph/graph.json)
  -f, --format <format>    导出格式: json|dot|csv (默认: json)
  -o, --output <file>      输出文件路径

# 统计命令
codegraph stats [options]
  -g, --graph <file>       知识图谱文件路径 (默认: .codegraph/graph.json)
```

### 🎨 可视化界面操作

| 操作 | 说明 |
|------|------|
| 🖱️ **拖拽节点** | 调整节点位置 |
| 🔍 **滚轮缩放** | 放大/缩小视图 |
| 👆 **点击节点** | 查看详细信息 |
| 🔎 **搜索框** | 搜索并高亮节点 |
| ☑️ **类型筛选** | 按节点类型过滤 |
| ⚡ **物理引擎** | 开启/关闭力导向动画 |

### 📤 导出格式示例

**DOT 格式（Graphviz）**
```bash
codegraph export -f dot -o graph.dot
# 生成图片: dot -Tpng graph.dot -o graph.png
```

**CSV 格式**
```bash
codegraph export -f csv -o graph.csv
# 可用 Excel 或数据分析工具打开
```

---

## 💡 设计思路与迭代规划

### 🏗️ 架构设计

```
CodeGraph-Lite
├── Parser Core      # AST 解析引擎
├── Graph Builder    # 图谱构建器
├── Visualizer       # 可视化服务器
└── CLI Interface    # 命令行接口
```

### 🎯 技术选型

- **TypeScript** - 类型安全，开发体验佳
- **Babel Parser** - 强大的JS/TS AST解析
- **D3.js** - 业界标准的可视化库
- **Express + WebSocket** - 实时交互服务器
- **Commander.js** - 优雅的CLI框架

### 📅 迭代计划

#### v1.1.0（近期）
- [ ] Python 语言支持
- [ ] 更多导出格式（SVG、PNG）
- [ ] 代码复杂度分析

#### v1.2.0（规划中）
- [ ] Go 语言支持
- [ ] 差异分析模式
- [ ] CI/CD 集成

#### v2.0.0（愿景）
- [ ] 插件系统
- [ ] 团队协作功能
- [ ] 云端托管

---

## 📦 打包与部署

### 🏗️ 本地构建

```bash
# 克隆仓库
git clone https://github.com/gitstq/CodeGraph-Lite.git
cd CodeGraph-Lite

# 安装依赖
npm install

# 构建
npm run build

# 本地测试
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

### ☁️ 云平台部署

支持一键部署到 Vercel、Netlify、Heroku 等平台。

---

## 🤝 贡献指南

我们欢迎所有形式的贡献！

### 📝 提交 Issue

- 使用清晰的标题描述问题
- 提供复现步骤和环境信息
- 附上错误日志和截图

### 🔧 提交 PR

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'feat: add amazing feature'`)
4. 推送分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

### 📏 代码规范

- 使用 TypeScript 严格模式
- 遵循 ESLint 配置
- 提交前运行测试 (`npm test`)
- 使用 [Conventional Commits](https://conventionalcommits.org/)

---

## 📄 开源协议

本项目采用 [MIT 协议](LICENSE) 开源。

---

## 🙏 致谢

- 灵感来源：[Understand-Anything](https://github.com/Lum1104/Understand-Anything)
- 可视化引擎：[D3.js](https://d3js.org/)
- AST解析：[Babel](https://babeljs.io/)

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给我们一个 Star！**

**💬 有任何问题或建议，欢迎提交 Issue 或 Discussion**

Made with ❤️ by [Lobster](https://github.com/gitstq)

</div>
