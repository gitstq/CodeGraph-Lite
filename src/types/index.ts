/**
 * CodeGraph-Lite 类型定义
 * 核心数据结构接口
 */

// 节点类型
export enum NodeType {
  FILE = 'file',
  FUNCTION = 'function',
  CLASS = 'class',
  INTERFACE = 'interface',
  VARIABLE = 'variable',
  IMPORT = 'import',
  EXPORT = 'export'
}

// 边类型
export enum EdgeType {
  CONTAINS = 'contains',
  CALLS = 'calls',
  IMPORTS = 'imports',
  EXTENDS = 'extends',
  IMPLEMENTS = 'implements',
  DEPENDS_ON = 'depends_on'
}

// 代码节点
export interface CodeNode {
  id: string;
  type: NodeType;
  name: string;
  filePath: string;
  lineStart: number;
  lineEnd: number;
  language: string;
  metadata?: {
    signature?: string;
    params?: string[];
    returnType?: string;
    modifiers?: string[];
    comments?: string;
  };
}

// 关系边
export interface CodeEdge {
  id: string;
  source: string;
  target: string;
  type: EdgeType;
  metadata?: {
    line?: number;
    column?: number;
  };
}

// 知识图谱
export interface KnowledgeGraph {
  nodes: CodeNode[];
  edges: CodeEdge[];
  metadata: {
    generatedAt: string;
    projectPath: string;
    fileCount: number;
    languageDistribution: Record<string, number>;
  };
}

// 解析配置
export interface ParseConfig {
  include: string[];
  exclude: string[];
  languages: string[];
  maxFileSize: number;
  incremental: boolean;
}

// 分析结果
export interface AnalysisResult {
  graph: KnowledgeGraph;
  statistics: {
    totalFiles: number;
    totalFunctions: number;
    totalClasses: number;
    totalDependencies: number;
  };
  warnings: string[];
}

// 语言支持配置
export interface LanguageConfig {
  extensions: string[];
  parser: string;
  plugins?: string[];
}

// 导出默认配置
export const DEFAULT_CONFIG: ParseConfig = {
  include: ['src/**/*', 'lib/**/*', 'packages/**/*'],
  exclude: [
    'node_modules/**',
    'dist/**',
    'build/**',
    '**/*.test.*',
    '**/*.spec.*',
    '**/*.min.*'
  ],
  languages: ['typescript', 'javascript', 'python', 'go'],
  maxFileSize: 1024 * 1024, // 1MB
  incremental: true
};

// 语言映射
export const LANGUAGE_MAP: Record<string, LanguageConfig> = {
  typescript: {
    extensions: ['.ts', '.tsx'],
    parser: '@babel/parser',
    plugins: ['typescript', 'jsx']
  },
  javascript: {
    extensions: ['.js', '.jsx', '.mjs'],
    parser: '@babel/parser',
    plugins: ['jsx']
  },
  python: {
    extensions: ['.py'],
    parser: 'python-ast',
    plugins: []
  },
  go: {
    extensions: ['.go'],
    parser: 'go-ast',
    plugins: []
  }
};
