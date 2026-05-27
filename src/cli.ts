#!/usr/bin/env node

/**
 * CodeGraph-Lite CLI
 * 命令行入口
 */

import { Command } from 'commander';
import * as fs from 'fs';
import * as path from 'path';
import { CodeParser } from './core/parser';
import { VisualizerServer } from './core/visualizer';
import { ParseConfig, KnowledgeGraph } from './types';

const program = new Command();

program
  .name('codegraph-lite')
  .description('🚀 轻量级代码结构可视化工具')
  .version('1.0.0');

program
  .command('analyze')
  .description('📊 分析代码库并生成知识图谱')
  .argument('<path>', '项目路径')
  .option('-o, --output <file>', '输出文件路径', '.codegraph/graph.json')
  .option('-i, --include <patterns>', '包含文件模式', 'src/**/*')
  .option('-e, --exclude <patterns>', '排除文件模式', 'node_modules/**')
  .option('--incremental', '启用增量分析', true)
  .action(async (projectPath, options) => {
    try {
      console.log('🚀 CodeGraph-Lite 开始分析...');
      console.log(`📁 项目路径: ${path.resolve(projectPath)}`);

      const config: Partial<ParseConfig> = {
        include: options.include.split(','),
        exclude: options.exclude.split(','),
        incremental: options.incremental
      };

      const parser = new CodeParser(config);
      const result = await parser.parseProject(projectPath);

      // 确保输出目录存在
      const outputDir = path.dirname(options.output);
      if (!fs.existsSync(outputDir)) {
        fs.mkdirSync(outputDir, { recursive: true });
      }

      // 保存图谱
      fs.writeFileSync(options.output, JSON.stringify(result.graph, null, 2));

      console.log('\n✅ 分析完成!');
      console.log(`📊 统计信息:`);
      console.log(`   📁 文件数: ${result.statistics.totalFiles}`);
      console.log(`   🔧 函数数: ${result.statistics.totalFunctions}`);
      console.log(`   📦 类数: ${result.statistics.totalClasses}`);
      console.log(`   🔗 依赖数: ${result.statistics.totalDependencies}`);
      console.log(`\n💾 图谱已保存: ${path.resolve(options.output)}`);

      if (result.warnings.length > 0) {
        console.log(`\n⚠️  警告 (${result.warnings.length}):`);
        result.warnings.forEach(w => console.log(`   - ${w}`));
      }
    } catch (error) {
      console.error('❌ 分析失败:', error);
      process.exit(1);
    }
  });

program
  .command('visualize')
  .description('🌐 启动可视化服务器')
  .option('-p, --port <number>', '服务器端口', '3000')
  .option('-g, --graph <file>', '知识图谱文件路径', '.codegraph/graph.json')
  .option('--no-open', '不自动打开浏览器')
  .action(async (options) => {
    try {
      const graphPath = path.resolve(options.graph);

      if (!fs.existsSync(graphPath)) {
        console.error(`❌ 图谱文件不存在: ${graphPath}`);
        console.log('💡 请先运行: codegraph analyze <path>');
        process.exit(1);
      }

      console.log('🌐 启动可视化服务器...');

      const graph: KnowledgeGraph = JSON.parse(fs.readFileSync(graphPath, 'utf-8'));
      const server = new VisualizerServer(parseInt(options.port));

      server.loadGraph(graph);
      await server.start();

      console.log(`\n🎉 可视化服务已启动!`);
      console.log(`🌐 访问地址: http://localhost:${options.port}`);

      if (options.open) {
        await server.openBrowser();
      }

      console.log('\n💡 提示:');
      console.log('   - 按 Ctrl+C 停止服务器');
      console.log('   - 在浏览器中拖拽节点可调整布局');
      console.log('   - 使用鼠标滚轮缩放视图');

      // 保持进程运行
      process.on('SIGINT', () => {
        console.log('\n👋 正在关闭服务器...');
        server.stop();
        process.exit(0);
      });
    } catch (error) {
      console.error('❌ 启动失败:', error);
      process.exit(1);
    }
  });

program
  .command('export')
  .description('📤 导出图谱为其他格式')
  .option('-g, --graph <file>', '知识图谱文件路径', '.codegraph/graph.json')
  .option('-f, --format <format>', '导出格式 (json|dot|csv)', 'json')
  .option('-o, --output <file>', '输出文件路径')
  .action(async (options) => {
    try {
      const graphPath = path.resolve(options.graph);

      if (!fs.existsSync(graphPath)) {
        console.error(`❌ 图谱文件不存在: ${graphPath}`);
        process.exit(1);
      }

      const graph: KnowledgeGraph = JSON.parse(fs.readFileSync(graphPath, 'utf-8'));
      let output: string;
      let ext: string;

      switch (options.format) {
        case 'dot':
          output = exportToDot(graph);
          ext = 'dot';
          break;
        case 'csv':
          output = exportToCsv(graph);
          ext = 'csv';
          break;
        case 'json':
        default:
          output = JSON.stringify(graph, null, 2);
          ext = 'json';
          break;
      }

      const outputPath = options.output || `.codegraph/graph.${ext}`;
      fs.writeFileSync(outputPath, output);

      console.log(`✅ 导出成功: ${path.resolve(outputPath)}`);
    } catch (error) {
      console.error('❌ 导出失败:', error);
      process.exit(1);
    }
  });

program
  .command('stats')
  .description('📈 显示代码库统计信息')
  .option('-g, --graph <file>', '知识图谱文件路径', '.codegraph/graph.json')
  .action(async (options) => {
    try {
      const graphPath = path.resolve(options.graph);

      if (!fs.existsSync(graphPath)) {
        console.error(`❌ 图谱文件不存在: ${graphPath}`);
        console.log('💡 请先运行: codegraph analyze <path>');
        process.exit(1);
      }

      const graph: KnowledgeGraph = JSON.parse(fs.readFileSync(graphPath, 'utf-8'));

      console.log('📊 CodeGraph-Lite 统计报告');
      console.log('═'.repeat(50));
      console.log(`📁 项目路径: ${graph.metadata.projectPath}`);
      console.log(`🕐 生成时间: ${new Date(graph.metadata.generatedAt).toLocaleString()}`);
      console.log('');

      // 节点统计
      const nodeTypes: Record<string, number> = {};
      graph.nodes.forEach(n => {
        nodeTypes[n.type] = (nodeTypes[n.type] || 0) + 1;
      });

      console.log('📈 节点统计:');
      Object.entries(nodeTypes)
        .sort(([,a], [,b]) => b - a)
        .forEach(([type, count]) => {
          const icon = getTypeIcon(type);
          console.log(`   ${icon} ${type}: ${count}`);
        });

      console.log('');
      console.log('🔗 关系数量:', graph.edges.length);

      console.log('');
      console.log('🌐 语言分布:');
      Object.entries(graph.metadata.languageDistribution)
        .sort(([,a], [,b]) => b - a)
        .forEach(([lang, count]) => {
          console.log(`   ${lang}: ${count} 个文件`);
        });

      // 最大文件
      console.log('');
      console.log('📄 最大文件 (按节点数):');
      const fileNodes = graph.nodes.filter(n => n.type === 'file');
      const fileNodeCounts: Record<string, number> = {};
      graph.nodes.forEach(n => {
        if (n.type !== 'file') {
          fileNodeCounts[n.filePath] = (fileNodeCounts[n.filePath] || 0) + 1;
        }
      });

      Object.entries(fileNodeCounts)
        .sort(([,a], [,b]) => b - a)
        .slice(0, 5)
        .forEach(([file, count]) => {
          console.log(`   ${file}: ${count} 个节点`);
        });

    } catch (error) {
      console.error('❌ 统计失败:', error);
      process.exit(1);
    }
  });

// 导出为DOT格式 (Graphviz)
function exportToDot(graph: KnowledgeGraph): string {
  const colors: Record<string, string> = {
    file: '#ff6b6b',
    function: '#4ecdc4',
    class: '#45b7d1',
    interface: '#96ceb4',
    variable: '#dda0dd',
    import: '#feca57',
    export: '#ff9ff3'
  };

  let dot = 'digraph CodeGraph {\n';
  dot += '  rankdir=TB;\n';
  dot += '  node [shape=box, style=rounded];\n\n';

  // 节点
  graph.nodes.forEach(node => {
    const label = node.name.replace(/"/g, '\\"');
    const color = colors[node.type] || '#888888';
    dot += `  "${node.id}" [label="${label}", fillcolor="${color}", style=filled];\n`;
  });

  dot += '\n';

  // 边
  graph.edges.forEach(edge => {
    dot += `  "${edge.source}" -> "${edge.target}";\n`;
  });

  dot += '}';
  return dot;
}

// 导出为CSV格式
function exportToCsv(graph: KnowledgeGraph): string {
  // 节点CSV
  let csv = 'id,type,name,filePath,lineStart,lineEnd,language\n';
  graph.nodes.forEach(node => {
    csv += `"${node.id}","${node.type}","${node.name}","${node.filePath}",${node.lineStart},${node.lineEnd},"${node.language}"\n`;
  });

  csv += '\n';

  // 边CSV
  csv += 'id,source,target,type\n';
  graph.edges.forEach(edge => {
    csv += `"${edge.id}","${edge.source}","${edge.target}","${edge.type}"\n`;
  });

  return csv;
}

// 获取类型图标
function getTypeIcon(type: string): string {
  const icons: Record<string, string> = {
    file: '📁',
    function: '🔧',
    class: '📦',
    interface: '🔌',
    variable: '📋',
    import: '📥',
    export: '📤'
  };
  return icons[type] || '•';
}

program.parse();
