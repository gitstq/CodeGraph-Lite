/**
 * 代码解析器核心模块
 * 支持多语言AST解析
 */

import * as fs from 'fs';
import * as path from 'path';
import { parse } from '@babel/parser';
import traverse from '@babel/traverse';
import * as t from '@babel/types';
import { glob } from 'glob';
import {
  CodeNode,
  CodeEdge,
  KnowledgeGraph,
  ParseConfig,
  AnalysisResult,
  NodeType,
  EdgeType,
  DEFAULT_CONFIG,
  LANGUAGE_MAP
} from '../types';

export class CodeParser {
  private config: ParseConfig;
  private nodes: Map<string, CodeNode> = new Map();
  private edges: CodeEdge[] = [];
  private fileHashes: Map<string, string> = new Map();

  constructor(config: Partial<ParseConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  /**
   * 解析项目目录
   */
  async parseProject(projectPath: string): Promise<AnalysisResult> {
    const startTime = Date.now();
    this.nodes.clear();
    this.edges = [];

    // 获取所有目标文件
    const files = await this.getTargetFiles(projectPath);
    const languageDistribution: Record<string, number> = {};

    // 解析每个文件
    for (const filePath of files) {
      const language = this.detectLanguage(filePath);
      languageDistribution[language] = (languageDistribution[language] || 0) + 1;

      try {
        await this.parseFile(filePath, language);
      } catch (error) {
        console.warn(`⚠️  解析文件失败: ${filePath}`, error);
      }
    }

    // 构建知识图谱
    const graph: KnowledgeGraph = {
      nodes: Array.from(this.nodes.values()),
      edges: this.edges,
      metadata: {
        generatedAt: new Date().toISOString(),
        projectPath,
        fileCount: files.length,
        languageDistribution
      }
    };

    const statistics = this.calculateStatistics();

    return {
      graph,
      statistics,
      warnings: []
    };
  }

  /**
   * 获取目标文件列表
   */
  private async getTargetFiles(projectPath: string): Promise<string[]> {
    const files: string[] = [];

    for (const pattern of this.config.include) {
      const matches = await glob(pattern, {
        cwd: projectPath,
        absolute: true,
        ignore: this.config.exclude
      });
      files.push(...matches);
    }

    // 过滤文件大小
    return files.filter(file => {
      const stats = fs.statSync(file);
      return stats.isFile() && stats.size <= this.config.maxFileSize;
    });
  }

  /**
   * 检测文件语言
   */
  private detectLanguage(filePath: string): string {
    const ext = path.extname(filePath).toLowerCase();

    for (const [lang, config] of Object.entries(LANGUAGE_MAP)) {
      if (config.extensions.includes(ext)) {
        return lang;
      }
    }

    return 'unknown';
  }

  /**
   * 解析单个文件
   */
  private async parseFile(filePath: string, language: string): Promise<void> {
    const content = fs.readFileSync(filePath, 'utf-8');
    const relativePath = path.relative(process.cwd(), filePath);

    // 创建文件节点
    const fileNodeId = `file:${relativePath}`;
    const fileNode: CodeNode = {
      id: fileNodeId,
      type: NodeType.FILE,
      name: path.basename(filePath),
      filePath: relativePath,
      lineStart: 1,
      lineEnd: content.split('\n').length,
      language,
      metadata: {
        signature: `file ${relativePath}`
      }
    };
    this.nodes.set(fileNodeId, fileNode);

    // 根据语言选择解析器
    if (language === 'typescript' || language === 'javascript') {
      await this.parseJavaScriptFile(filePath, content, fileNodeId);
    }
    // 可以扩展支持其他语言
  }

  /**
   * 解析JavaScript/TypeScript文件
   */
  private async parseJavaScriptFile(
    filePath: string,
    content: string,
    fileNodeId: string
  ): Promise<void> {
    const relativePath = path.relative(process.cwd(), filePath);

    try {
      const ast = parse(content, {
        sourceType: 'module',
        plugins: [
          'typescript',
          'jsx',
          'decorators-legacy',
          'classProperties',
          'asyncGenerators',
          'dynamicImport'
        ]
      });

      traverse(ast, {
        // 函数声明
        FunctionDeclaration: (nodePath) => {
          const node = nodePath.node;
          if (node.id) {
            const funcNode = this.createFunctionNode(
              node.id.name,
              relativePath,
              node.loc?.start.line || 0,
              node.loc?.end.line || 0,
              node.params.map(p => this.getParamName(p)),
              this.getReturnType(node)
            );
            this.nodes.set(funcNode.id, funcNode);
            this.addEdge(fileNodeId, funcNode.id, EdgeType.CONTAINS);
          }
        },

        // 类声明
        ClassDeclaration: (nodePath) => {
          const node = nodePath.node;
          if (node.id) {
            const classNode = this.createClassNode(
              node.id.name,
              relativePath,
              node.loc?.start.line || 0,
              node.loc?.end.line || 0
            );
            this.nodes.set(classNode.id, classNode);
            this.addEdge(fileNodeId, classNode.id, EdgeType.CONTAINS);

            // 处理继承关系
            if (node.superClass && t.isIdentifier(node.superClass)) {
              this.addEdge(classNode.id, `class:${node.superClass.name}`, EdgeType.EXTENDS);
            }

            // 处理类方法
            node.body.body.forEach(member => {
              if (t.isClassMethod(member) && t.isIdentifier(member.key)) {
                const methodNode = this.createFunctionNode(
                  `${node.id!.name}.${member.key.name}`,
                  relativePath,
                  member.loc?.start.line || 0,
                  member.loc?.end.line || 0,
                  member.params.map(p => this.getParamName(p)),
                  this.getReturnType(member)
                );
                this.nodes.set(methodNode.id, methodNode);
                this.addEdge(classNode.id, methodNode.id, EdgeType.CONTAINS);
              }
            });
          }
        },

        // 接口声明
        TSInterfaceDeclaration: (nodePath) => {
          const node = nodePath.node;
          const interfaceNode: CodeNode = {
            id: `interface:${node.id.name}`,
            type: NodeType.INTERFACE,
            name: node.id.name,
            filePath: relativePath,
            lineStart: node.loc?.start.line || 0,
            lineEnd: node.loc?.end.line || 0,
            language: 'typescript',
            metadata: {
              signature: `interface ${node.id.name}`
            }
          };
          this.nodes.set(interfaceNode.id, interfaceNode);
          this.addEdge(fileNodeId, interfaceNode.id, EdgeType.CONTAINS);
        },

        // 导入声明
        ImportDeclaration: (nodePath) => {
          const node = nodePath.node;
          const source = node.source.value;

          node.specifiers.forEach(spec => {
            if (t.isImportSpecifier(spec) && t.isIdentifier(spec.imported)) {
              const importNode: CodeNode = {
                id: `import:${spec.local.name}`,
                type: NodeType.IMPORT,
                name: spec.local.name,
                filePath: relativePath,
                lineStart: node.loc?.start.line || 0,
                lineEnd: node.loc?.end.line || 0,
                language: 'typescript',
                metadata: {
                  signature: `import { ${spec.imported.name} } from '${source}'`
                }
              };
              this.nodes.set(importNode.id, importNode);
              this.addEdge(fileNodeId, importNode.id, EdgeType.IMPORTS);
            }
          });
        },

        // 导出声明
        ExportNamedDeclaration: (nodePath) => {
          const node = nodePath.node;
          if (node.declaration) {
            if (t.isFunctionDeclaration(node.declaration) && node.declaration.id) {
              const exportNode: CodeNode = {
                id: `export:${node.declaration.id.name}`,
                type: NodeType.EXPORT,
                name: node.declaration.id.name,
                filePath: relativePath,
                lineStart: node.loc?.start.line || 0,
                lineEnd: node.loc?.end.line || 0,
                language: 'typescript',
                metadata: {
                  signature: `export function ${node.declaration.id.name}`
                }
              };
              this.nodes.set(exportNode.id, exportNode);
              this.addEdge(fileNodeId, exportNode.id, EdgeType.CONTAINS);
            }
          }
        }
      });
    } catch (error) {
      console.warn(`⚠️  解析AST失败: ${filePath}`, error);
    }
  }

  /**
   * 创建函数节点
   */
  private createFunctionNode(
    name: string,
    filePath: string,
    lineStart: number,
    lineEnd: number,
    params: string[],
    returnType?: string
  ): CodeNode {
    return {
      id: `function:${name}`,
      type: NodeType.FUNCTION,
      name,
      filePath,
      lineStart,
      lineEnd,
      language: 'typescript',
      metadata: {
        signature: `function ${name}(${params.join(', ')})`,
        params,
        returnType
      }
    };
  }

  /**
   * 创建类节点
   */
  private createClassNode(
    name: string,
    filePath: string,
    lineStart: number,
    lineEnd: number
  ): CodeNode {
    return {
      id: `class:${name}`,
      type: NodeType.CLASS,
      name,
      filePath,
      lineStart,
      lineEnd,
      language: 'typescript',
      metadata: {
        signature: `class ${name}`
      }
    };
  }

  /**
   * 获取参数名称
   */
  private getParamName(param: any): string {
    if (t.isIdentifier(param)) {
      return param.name;
    }
    if (t.isAssignmentPattern(param) && t.isIdentifier(param.left)) {
      return param.left.name;
    }
    if (t.isRestElement(param) && t.isIdentifier(param.argument)) {
      return `...${param.argument.name}`;
    }
    if (t.isTSParameterProperty(param) && t.isIdentifier(param.parameter)) {
      return param.parameter.name;
    }
    return 'unknown';
  }

  /**
   * 获取返回类型
   */
  private getReturnType(node: t.FunctionDeclaration | t.ClassMethod): string | undefined {
    if (t.isTSFunctionType(node.returnType)) {
      return 'function';
    }
    if (t.isTSTypeAnnotation(node.returnType)) {
      return 'typed';
    }
    return undefined;
  }

  /**
   * 添加边
   */
  private addEdge(source: string, target: string, type: EdgeType): void {
    const edge: CodeEdge = {
      id: `edge:${source}->${target}:${type}`,
      source,
      target,
      type
    };
    this.edges.push(edge);
  }

  /**
   * 计算统计信息
   */
  private calculateStatistics() {
    let totalFiles = 0;
    let totalFunctions = 0;
    let totalClasses = 0;
    let totalDependencies = 0;

    for (const node of this.nodes.values()) {
      switch (node.type) {
        case NodeType.FILE:
          totalFiles++;
          break;
        case NodeType.FUNCTION:
          totalFunctions++;
          break;
        case NodeType.CLASS:
          totalClasses++;
          break;
        case NodeType.IMPORT:
          totalDependencies++;
          break;
      }
    }

    return {
      totalFiles,
      totalFunctions,
      totalClasses,
      totalDependencies
    };
  }
}
