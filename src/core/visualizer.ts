/**
 * 可视化服务器模块
 * 提供Web界面展示代码知识图谱
 */

import * as http from 'http';
import * as fs from 'fs';
import * as path from 'path';
import express from 'express';
import WebSocket from 'ws';
import open from 'open';
import { KnowledgeGraph, CodeNode, CodeEdge } from '../types';

export class VisualizerServer {
  private app: express.Application;
  private server: http.Server | null = null;
  private wss: WebSocket.Server | null = null;
  private graph: KnowledgeGraph | null = null;
  private port: number;

  constructor(port: number = 3000) {
    this.port = port;
    this.app = express();
    this.setupRoutes();
  }

  /**
   * 设置路由
   */
  private setupRoutes(): void {
    this.app.use(express.json());
    this.app.use(express.static(path.join(__dirname, '../public')));

    // API路由
    this.app.get('/api/graph', (req, res) => {
      if (!this.graph) {
        return res.status(404).json({ error: 'Graph not loaded' });
      }
      res.json(this.graph);
    });

    this.app.get('/api/nodes', (req, res) => {
      if (!this.graph) {
        return res.status(404).json({ error: 'Graph not loaded' });
      }
      const { type, search } = req.query;
      let nodes = this.graph.nodes;

      if (type) {
        nodes = nodes.filter(n => n.type === type);
      }

      if (search) {
        const searchLower = (search as string).toLowerCase();
        nodes = nodes.filter(n =>
          n.name.toLowerCase().includes(searchLower) ||
          n.filePath.toLowerCase().includes(searchLower)
        );
      }

      res.json(nodes);
    });

    this.app.get('/api/edges/:nodeId', (req, res) => {
      if (!this.graph) {
        return res.status(404).json({ error: 'Graph not loaded' });
      }
      const nodeId = req.params.nodeId;
      const edges = this.graph.edges.filter(
        e => e.source === nodeId || e.target === nodeId
      );
      res.json(edges);
    });

    this.app.get('/api/stats', (req, res) => {
      if (!this.graph) {
        return res.status(404).json({ error: 'Graph not loaded' });
      }

      const stats = {
        totalNodes: this.graph.nodes.length,
        totalEdges: this.graph.edges.length,
        nodeTypes: {} as Record<string, number>,
        edgeTypes: {} as Record<string, number>,
        languageDistribution: this.graph.metadata.languageDistribution
      };

      this.graph.nodes.forEach(node => {
        stats.nodeTypes[node.type] = (stats.nodeTypes[node.type] || 0) + 1;
      });

      this.graph.edges.forEach(edge => {
        stats.edgeTypes[edge.type] = (stats.edgeTypes[edge.type] || 0) + 1;
      });

      res.json(stats);
    });

    // 主页面
    this.app.get('/', (req, res) => {
      res.send(this.getHTMLTemplate());
    });
  }

  /**
   * 加载知识图谱
   */
  loadGraph(graph: KnowledgeGraph): void {
    this.graph = graph;
    this.broadcast('graph:loaded', {
      nodeCount: graph.nodes.length,
      edgeCount: graph.edges.length
    });
  }

  /**
   * 启动服务器
   */
  async start(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.server = this.app.listen(this.port, () => {
        console.log(`🚀 可视化服务器已启动: http://localhost:${this.port}`);

        // 设置WebSocket
        this.wss = new WebSocket.Server({ server: this.server! });
        this.wss.on('connection', (ws) => {
          console.log('🔌 WebSocket客户端已连接');

          ws.on('message', (message) => {
            try {
              const data = JSON.parse(message.toString());
              this.handleWebSocketMessage(ws, data);
            } catch (error) {
              console.error('WebSocket消息解析失败:', error);
            }
          });

          ws.on('close', () => {
            console.log('🔌 WebSocket客户端已断开');
          });
        });

        resolve();
      });

      this.server.on('error', reject);
    });
  }

  /**
   * 打开浏览器
   */
  async openBrowser(): Promise<void> {
    await open(`http://localhost:${this.port}`);
  }

  /**
   * 停止服务器
   */
  stop(): void {
    if (this.wss) {
      this.wss.close();
    }
    if (this.server) {
      this.server.close();
    }
  }

  /**
   * 处理WebSocket消息
   */
  private handleWebSocketMessage(ws: WebSocket, data: any): void {
    switch (data.type) {
      case 'get:node':
        const node = this.graph?.nodes.find(n => n.id === data.nodeId);
        ws.send(JSON.stringify({ type: 'node:data', node }));
        break;
      case 'get:neighbors':
        const neighbors = this.getNodeNeighbors(data.nodeId);
        ws.send(JSON.stringify({ type: 'neighbors:data', neighbors }));
        break;
      case 'search:nodes':
        const results = this.searchNodes(data.query);
        ws.send(JSON.stringify({ type: 'search:results', results }));
        break;
    }
  }

  /**
   * 获取节点邻居
   */
  private getNodeNeighbors(nodeId: string): { nodes: CodeNode[]; edges: CodeEdge[] } {
    if (!this.graph) return { nodes: [], edges: [] };

    const edges = this.graph.edges.filter(
      e => e.source === nodeId || e.target === nodeId
    );

    const neighborIds = new Set<string>();
    edges.forEach(e => {
      if (e.source !== nodeId) neighborIds.add(e.source);
      if (e.target !== nodeId) neighborIds.add(e.target);
    });

    const nodes = this.graph.nodes.filter(n => neighborIds.has(n.id));

    return { nodes, edges };
  }

  /**
   * 搜索节点
   */
  private searchNodes(query: string): CodeNode[] {
    if (!this.graph) return [];

    const queryLower = query.toLowerCase();
    return this.graph.nodes.filter(n =>
      n.name.toLowerCase().includes(queryLower) ||
      n.filePath.toLowerCase().includes(queryLower) ||
      n.type.toLowerCase().includes(queryLower)
    );
  }

  /**
   * 广播消息
   */
  private broadcast(type: string, data: any): void {
    if (!this.wss) return;

    const message = JSON.stringify({ type, data });
    this.wss.clients.forEach(client => {
      if (client.readyState === WebSocket.OPEN) {
        client.send(message);
      }
    });
  }

  /**
   * 获取HTML模板
   */
  private getHTMLTemplate(): string {
    return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>CodeGraph-Lite | 代码知识图谱可视化</title>
  <script src="https://d3js.org/d3.v7.min.js"></script>
  <style>
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }

    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
      color: #fff;
      min-height: 100vh;
      overflow: hidden;
    }

    .header {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      height: 60px;
      background: rgba(0, 0, 0, 0.3);
      backdrop-filter: blur(10px);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 20px;
      z-index: 1000;
      border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    }

    .logo {
      font-size: 20px;
      font-weight: bold;
      background: linear-gradient(90deg, #00d4ff, #7b2cbf);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .search-box {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .search-box input {
      width: 300px;
      padding: 8px 15px;
      border: 1px solid rgba(255, 255, 255, 0.2);
      border-radius: 20px;
      background: rgba(255, 255, 255, 0.1);
      color: #fff;
      font-size: 14px;
      outline: none;
      transition: all 0.3s;
    }

    .search-box input:focus {
      border-color: #00d4ff;
      background: rgba(255, 255, 255, 0.15);
    }

    .search-box input::placeholder {
      color: rgba(255, 255, 255, 0.5);
    }

    .stats-bar {
      display: flex;
      gap: 20px;
      font-size: 13px;
      color: rgba(255, 255, 255, 0.7);
    }

    .stat-item {
      display: flex;
      align-items: center;
      gap: 5px;
    }

    .stat-value {
      color: #00d4ff;
      font-weight: bold;
    }

    .main-container {
      display: flex;
      height: 100vh;
      padding-top: 60px;
    }

    .sidebar {
      width: 300px;
      background: rgba(0, 0, 0, 0.2);
      border-right: 1px solid rgba(255, 255, 255, 0.1);
      padding: 20px;
      overflow-y: auto;
    }

    .sidebar h3 {
      font-size: 14px;
      color: rgba(255, 255, 255, 0.5);
      margin-bottom: 15px;
      text-transform: uppercase;
      letter-spacing: 1px;
    }

    .filter-group {
      margin-bottom: 20px;
    }

    .filter-item {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 8px 10px;
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.2s;
      margin-bottom: 5px;
    }

    .filter-item:hover {
      background: rgba(255, 255, 255, 0.1);
    }

    .filter-item input[type="checkbox"] {
      width: 16px;
      height: 16px;
      accent-color: #00d4ff;
    }

    .filter-item label {
      flex: 1;
      cursor: pointer;
      font-size: 13px;
    }

    .filter-count {
      background: rgba(0, 212, 255, 0.2);
      color: #00d4ff;
      padding: 2px 8px;
      border-radius: 10px;
      font-size: 11px;
    }

    .graph-container {
      flex: 1;
      position: relative;
      overflow: hidden;
    }

    #graph {
      width: 100%;
      height: 100%;
    }

    .node {
      cursor: pointer;
      transition: all 0.3s;
    }

    .node:hover {
      filter: brightness(1.3);
    }

    .node-circle {
      stroke: #fff;
      stroke-width: 2px;
      transition: all 0.3s;
    }

    .node-label {
      font-size: 12px;
      fill: #fff;
      pointer-events: none;
      text-shadow: 0 1px 3px rgba(0, 0, 0, 0.8);
    }

    .link {
      stroke: rgba(255, 255, 255, 0.3);
      stroke-width: 1px;
      transition: all 0.3s;
    }

    .link:hover {
      stroke: #00d4ff;
      stroke-width: 2px;
    }

    .node-details {
      position: fixed;
      right: 20px;
      top: 80px;
      width: 350px;
      background: rgba(0, 0, 0, 0.5);
      backdrop-filter: blur(10px);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 12px;
      padding: 20px;
      z-index: 100;
      display: none;
    }

    .node-details.active {
      display: block;
    }

    .node-details h3 {
      font-size: 16px;
      margin-bottom: 15px;
      color: #00d4ff;
    }

    .detail-row {
      display: flex;
      justify-content: space-between;
      padding: 8px 0;
      border-bottom: 1px solid rgba(255, 255, 255, 0.1);
      font-size: 13px;
    }

    .detail-label {
      color: rgba(255, 255, 255, 0.5);
    }

    .detail-value {
      color: #fff;
      text-align: right;
      max-width: 200px;
      word-break: break-all;
    }

    .controls {
      position: fixed;
      bottom: 20px;
      left: 320px;
      display: flex;
      gap: 10px;
      z-index: 100;
    }

    .control-btn {
      width: 40px;
      height: 40px;
      border: none;
      border-radius: 10px;
      background: rgba(0, 0, 0, 0.5);
      backdrop-filter: blur(10px);
      color: #fff;
      font-size: 18px;
      cursor: pointer;
      transition: all 0.2s;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .control-btn:hover {
      background: rgba(0, 212, 255, 0.3);
      transform: scale(1.1);
    }

    .loading {
      position: fixed;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      text-align: center;
      z-index: 1000;
    }

    .loading-spinner {
      width: 50px;
      height: 50px;
      border: 3px solid rgba(0, 212, 255, 0.3);
      border-top-color: #00d4ff;
      border-radius: 50%;
      animation: spin 1s linear infinite;
      margin: 0 auto 20px;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }

    .loading p {
      color: rgba(255, 255, 255, 0.7);
    }

    .legend {
      position: fixed;
      bottom: 20px;
      right: 20px;
      background: rgba(0, 0, 0, 0.5);
      backdrop-filter: blur(10px);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 10px;
      padding: 15px;
      z-index: 100;
    }

    .legend h4 {
      font-size: 12px;
      color: rgba(255, 255, 255, 0.5);
      margin-bottom: 10px;
    }

    .legend-item {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 5px;
      font-size: 12px;
    }

    .legend-color {
      width: 12px;
      height: 12px;
      border-radius: 50%;
    }
  </style>
</head>
<body>
  <div class="header">
    <div class="logo">
      <span>🕸️</span>
      <span>CodeGraph-Lite</span>
    </div>
    <div class="search-box">
      <input type="text" id="searchInput" placeholder="🔍 搜索节点...">
    </div>
    <div class="stats-bar">
      <div class="stat-item">
        <span>📁 文件:</span>
        <span class="stat-value" id="fileCount">0</span>
      </div>
      <div class="stat-item">
        <span>🔧 函数:</span>
        <span class="stat-value" id="funcCount">0</span>
      </div>
      <div class="stat-item">
        <span>📦 类:</span>
        <span class="stat-value" id="classCount">0</span>
      </div>
      <div class="stat-item">
        <span>🔗 关系:</span>
        <span class="stat-value" id="edgeCount">0</span>
      </div>
    </div>
  </div>

  <div class="main-container">
    <div class="sidebar">
      <h3>🎨 节点类型过滤</h3>
      <div class="filter-group" id="typeFilters">
        <div class="filter-item">
          <input type="checkbox" id="filter-file" checked>
          <label for="filter-file">📁 文件</label>
          <span class="filter-count" id="count-file">0</span>
        </div>
        <div class="filter-item">
          <input type="checkbox" id="filter-function" checked>
          <label for="filter-function">🔧 函数</label>
          <span class="filter-count" id="count-function">0</span>
        </div>
        <div class="filter-item">
          <input type="checkbox" id="filter-class" checked>
          <label for="filter-class">📦 类</label>
          <span class="filter-count" id="count-class">0</span>
        </div>
        <div class="filter-item">
          <input type="checkbox" id="filter-interface" checked>
          <label for="filter-interface">🔌 接口</label>
          <span class="filter-count" id="count-interface">0</span>
        </div>
        <div class="filter-item">
          <input type="checkbox" id="filter-import" checked>
          <label for="filter-import">📥 导入</label>
          <span class="filter-count" id="count-import">0</span>
        </div>
      </div>

      <h3>🌐 语言分布</h3>
      <div class="filter-group" id="langDistribution"></div>
    </div>

    <div class="graph-container">
      <svg id="graph"></svg>
    </div>
  </div>

  <div class="node-details" id="nodeDetails">
    <h3 id="detailTitle">节点详情</h3>
    <div id="detailContent"></div>
  </div>

  <div class="controls">
    <button class="control-btn" onclick="zoomIn()" title="放大">+</button>
    <button class="control-btn" onclick="zoomOut()" title="缩小">-</button>
    <button class="control-btn" onclick="resetZoom()" title="重置">⟲</button>
    <button class="control-btn" onclick="togglePhysics()" title="物理引擎">⚡</button>
  </div>

  <div class="legend">
    <h4>图例</h4>
    <div class="legend-item">
      <div class="legend-color" style="background: #ff6b6b;"></div>
      <span>文件</span>
    </div>
    <div class="legend-item">
      <div class="legend-color" style="background: #4ecdc4;"></div>
      <span>函数</span>
    </div>
    <div class="legend-item">
      <div class="legend-color" style="background: #45b7d1;"></div>
      <span>类</span>
    </div>
    <div class="legend-item">
      <div class="legend-color" style="background: #96ceb4;"></div>
      <span>接口</span>
    </div>
    <div class="legend-item">
      <div class="legend-color" style="background: #feca57;"></div>
      <span>导入</span>
    </div>
  </div>

  <div class="loading" id="loading">
    <div class="loading-spinner"></div>
    <p>正在加载知识图谱...</p>
  </div>

  <script>
    // 颜色映射
    const colorMap = {
      file: '#ff6b6b',
      function: '#4ecdc4',
      class: '#45b7d1',
      interface: '#96ceb4',
      variable: '#dda0dd',
      import: '#feca57',
      export: '#ff9ff3'
    };

    // 全局变量
    let svg, g, simulation, nodes = [], links = [];
    let currentTransform = d3.zoomIdentity;
    let physicsEnabled = true;

    // 初始化
    async function init() {
      try {
        const response = await fetch('/api/graph');
        const graph = await response.json();

        updateStats(graph);
        updateFilters(graph);
        renderGraph(graph);

        document.getElementById('loading').style.display = 'none';
      } catch (error) {
        console.error('加载图谱失败:', error);
        document.querySelector('.loading p').textContent = '加载失败，请刷新重试';
      }
    }

    // 更新统计信息
    function updateStats(graph) {
      const stats = {
        file: 0, function: 0, class: 0, interface: 0, import: 0, export: 0
      };

      graph.nodes.forEach(node => {
        if (stats[node.type] !== undefined) {
          stats[node.type]++;
        }
      });

      document.getElementById('fileCount').textContent = stats.file;
      document.getElementById('funcCount').textContent = stats.function;
      document.getElementById('classCount').textContent = stats.class;
      document.getElementById('edgeCount').textContent = graph.edges.length;

      // 更新过滤器计数
      Object.keys(stats).forEach(type => {
        const el = document.getElementById('count-' + type);
        if (el) el.textContent = stats[type];
      });
    }

    // 更新过滤器
    function updateFilters(graph) {
      const langDist = graph.metadata.languageDistribution;
      const langContainer = document.getElementById('langDistribution');

      Object.entries(langDist).forEach(([lang, count]) => {
        const item = document.createElement('div');
        item.className = 'filter-item';
        item.innerHTML = \`
          <span>\${lang.toUpperCase()}</span>
          <span class="filter-count">\${count}</span>
        \`;
        langContainer.appendChild(item);
      });
    }

    // 渲染图谱
    function renderGraph(graph) {
      const container = document.getElementById('graph');
      const width = container.clientWidth;
      const height = container.clientHeight;

      svg = d3.select('#graph')
        .attr('width', width)
        .attr('height', height);

      // 添加缩放行为
      const zoom = d3.zoom()
        .scaleExtent([0.1, 4])
        .on('zoom', (event) => {
          currentTransform = event.transform;
          g.attr('transform', event.transform);
        });

      svg.call(zoom);

      g = svg.append('g');

      // 准备数据
      nodes = graph.nodes.map(n => ({ ...n }));
      links = graph.edges.map(e => ({ ...e }));

      // 创建力导向模拟
      simulation = d3.forceSimulation(nodes)
        .force('link', d3.forceLink(links).id(d => d.id).distance(100))
        .force('charge', d3.forceManyBody().strength(-300))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collision', d3.forceCollide().radius(30));

      // 绘制连线
      const link = g.append('g')
        .selectAll('line')
        .data(links)
        .enter().append('line')
        .attr('class', 'link');

      // 绘制节点
      const node = g.append('g')
        .selectAll('g')
        .data(nodes)
        .enter().append('g')
        .attr('class', 'node')
        .call(d3.drag()
          .on('start', dragstarted)
          .on('drag', dragged)
          .on('end', dragended));

      // 节点圆形
      node.append('circle')
        .attr('class', 'node-circle')
        .attr('r', d => d.type === 'file' ? 20 : 12)
        .attr('fill', d => colorMap[d.type] || '#888');

      // 节点标签
      node.append('text')
        .attr('class', 'node-label')
        .attr('dy', d => d.type === 'file' ? 35 : 25)
        .attr('text-anchor', 'middle')
        .text(d => d.name.length > 15 ? d.name.substring(0, 15) + '...' : d.name);

      // 点击事件
      node.on('click', (event, d) => showNodeDetails(d));

      // 更新位置
      simulation.on('tick', () => {
        link
          .attr('x1', d => d.source.x)
          .attr('y1', d => d.source.y)
          .attr('x2', d => d.target.x)
          .attr('y2', d => d.target.y);

        node.attr('transform', d => \`translate(\${d.x},\${d.y})\`);
      });

      // 过滤器事件
      setupFilters();
    }

    // 设置过滤器
    function setupFilters() {
      document.querySelectorAll('#typeFilters input').forEach(checkbox => {
        checkbox.addEventListener('change', filterNodes);
      });
    }

    // 过滤节点
    function filterNodes() {
      const checkedTypes = new Set();
      document.querySelectorAll('#typeFilters input:checked').forEach(cb => {
        checkedTypes.add(cb.id.replace('filter-', ''));
      });

      const filteredNodes = nodes.filter(n => checkedTypes.has(n.type));
      const filteredNodeIds = new Set(filteredNodes.map(n => n.id));
      const filteredLinks = links.filter(l =>
        filteredNodeIds.has(l.source.id) && filteredNodeIds.has(l.target.id)
      );

      // 更新可视化
      g.selectAll('.node').style('display', d =>
        checkedTypes.has(d.type) ? 'block' : 'none'
      );

      g.selectAll('.link').style('display', d =>
        filteredNodeIds.has(d.source.id) && filteredNodeIds.has(d.target.id)
          ? 'block' : 'none'
      );
    }

    // 显示节点详情
    function showNodeDetails(node) {
      const details = document.getElementById('nodeDetails');
      const title = document.getElementById('detailTitle');
      const content = document.getElementById('detailContent');

      title.textContent = node.name;

      content.innerHTML = \`
        <div class="detail-row">
          <span class="detail-label">类型</span>
          <span class="detail-value">\${node.type}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">文件路径</span>
          <span class="detail-value">\${node.filePath}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">行号</span>
          <span class="detail-value">\${node.lineStart} - \${node.lineEnd}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">语言</span>
          <span class="detail-value">\${node.language}</span>
        </div>
        \${node.metadata?.signature ? \`
        <div class="detail-row">
          <span class="detail-label">签名</span>
          <span class="detail-value">\${node.metadata.signature}</span>
        </div>
        \` : ''}
        \${node.metadata?.params ? \`
        <div class="detail-row">
          <span class="detail-label">参数</span>
          <span class="detail-value">\${node.metadata.params.join(', ')}</span>
        </div>
        \` : ''}
      \`;

      details.classList.add('active');
    }

    // 拖拽函数
    function dragstarted(event, d) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    }

    function dragged(event, d) {
      d.fx = event.x;
      d.fy = event.y;
    }

    function dragended(event, d) {
      if (!event.active) simulation.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    }

    // 控制函数
    function zoomIn() {
      svg.transition().call(d3.zoom().transform, currentTransform.scale(1.2));
    }

    function zoomOut() {
      svg.transition().call(d3.zoom().transform, currentTransform.scale(0.8));
    }

    function resetZoom() {
      svg.transition().call(d3.zoom().transform, d3.zoomIdentity);
    }

    function togglePhysics() {
      physicsEnabled = !physicsEnabled;
      if (physicsEnabled) {
        simulation.restart();
      } else {
        simulation.stop();
      }
    }

    // 搜索功能
    document.getElementById('searchInput').addEventListener('input', (e) => {
      const query = e.target.value.toLowerCase();
      if (!query) {
        g.selectAll('.node').style('opacity', 1);
        return;
      }

      g.selectAll('.node').style('opacity', d => {
        const match = d.name.toLowerCase().includes(query) ||
                     d.filePath.toLowerCase().includes(query);
        return match ? 1 : 0.2;
      });
    });

    // 启动
    init();
  </script>
</body>
</html>`;
  }
}
