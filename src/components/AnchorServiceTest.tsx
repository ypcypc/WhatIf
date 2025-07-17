import React, { useState, useEffect } from 'react';
import { 
  Play, 
  CheckCircle, 
  XCircle, 
  AlertTriangle, 
  Loader2, 
  RefreshCw,
  Database,
  FileText,
  Activity
} from 'lucide-react';
import {
  assembleText,
  validateAnchors,
  healthCheck,
} from '../services/anchorService';
import type {
  Anchor,
  AssembleRequest,
  AssembleResponse,
  ValidationResponse
} from '../services/anchorService';

interface TestResult {
  success: boolean;
  message: string;
  data?: any;
  error?: string;
}

const AnchorServiceTest: React.FC = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [healthStatus, setHealthStatus] = useState<TestResult | null>(null);
  const [validationResult, setValidationResult] = useState<TestResult | null>(null);
  const [assembleResult, setAssembleResult] = useState<TestResult | null>(null);
  const [assembledText, setAssembledText] = useState<string>('');

  // Test data from article_data.json - using first few anchors from chapter 1
  const testAnchors: Anchor[] = [
    { node_id: "a1_1", chunk_id: "ch1_1", chapter_id: 1 },
    { node_id: "a1_2", chunk_id: "ch1_2", chapter_id: 1 },
    { node_id: "a1_3", chunk_id: "ch1_3", chapter_id: 1 },
  ];

  const testRequest: AssembleRequest = {
    anchors: testAnchors,
    include_chapter_intro: true  // As requested by user
  };

  // Auto-run health check on component mount
  useEffect(() => {
    runHealthCheck();
  }, []);

  const runHealthCheck = async () => {
    try {
      setIsLoading(true);
      const health = await healthCheck();
      setHealthStatus({
        success: true,
        message: `Service is ${health.status}`,
        data: health
      });
    } catch (error) {
      setHealthStatus({
        success: false,
        message: 'Health check failed',
        error: error instanceof Error ? error.message : 'Unknown error'
      });
    } finally {
      setIsLoading(false);
    }
  };

  const runValidation = async () => {
    try {
      setIsLoading(true);
      const validation = await validateAnchors(testRequest);
      setValidationResult({
        success: validation.valid,
        message: validation.valid 
          ? `Validation passed! ${validation.stats.total_anchors} anchors, ${validation.stats.unique_chapters} chapters`
          : `Validation failed: ${validation.errors.join(', ')}`,
        data: validation
      });
    } catch (error) {
      setValidationResult({
        success: false,
        message: 'Validation request failed',
        error: error instanceof Error ? error.message : 'Unknown error'
      });
    } finally {
      setIsLoading(false);
    }
  };

  const runAssemble = async () => {
    try {
      setIsLoading(true);
      const result = await assembleText(testRequest);
      setAssembleResult({
        success: true,
        message: `Assembly successful! Generated ${result.spans.length} spans`,
        data: result
      });
      setAssembledText(result.text);
    } catch (error) {
      setAssembleResult({
        success: false,
        message: 'Assembly request failed',
        error: error instanceof Error ? error.message : 'Unknown error'
      });
      setAssembledText('');
    } finally {
      setIsLoading(false);
    }
  };

  const runAllTests = async () => {
    await runHealthCheck();
    await runValidation();
    await runAssemble();
  };

  const getStatusIcon = (result: TestResult | null) => {
    if (!result) return <AlertTriangle className="w-5 h-5 text-gray-400" />;
    if (result.success) return <CheckCircle className="w-5 h-5 text-green-500" />;
    return <XCircle className="w-5 h-5 text-red-500" />;
  };

  const getStatusColor = (result: TestResult | null) => {
    if (!result) return 'border-gray-300';
    if (result.success) return 'border-green-500';
    return 'border-red-500';
  };

  return (
    <div className="p-6 max-w-4xl mx-auto bg-white rounded-lg shadow-lg">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
          <Database className="w-6 h-6" />
          Anchor Service 连通性测试
        </h2>
        <button
          onClick={runAllTests}
          disabled={isLoading}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
          运行所有测试
        </button>
      </div>

      {/* Test Data Preview */}
      <div className="mb-6 p-4 bg-gray-50 rounded-lg">
        <h3 className="font-semibold mb-2 flex items-center gap-2">
          <FileText className="w-4 h-4" />
          测试数据 (基于 article_data.json)
        </h3>
        <div className="text-sm text-gray-600">
          <p><strong>锚点数量:</strong> {testAnchors.length}</p>
          <p><strong>章节:</strong> {testAnchors[0].chapter_id}</p>
          <p><strong>chunk_ids:</strong> {testAnchors.map(a => a.chunk_id).join(', ')}</p>
          <p><strong>include_chapter_intro:</strong> {testRequest.include_chapter_intro ? '是' : '否'}</p>
        </div>
      </div>

      {/* Test Results */}
      <div className="space-y-4">
        {/* Health Check */}
        <div className={`border-2 rounded-lg p-4 ${getStatusColor(healthStatus)}`}>
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-semibold flex items-center gap-2">
              <Activity className="w-4 h-4" />
              1. 健康检查
            </h3>
            <button
              onClick={runHealthCheck}
              disabled={isLoading}
              className="px-3 py-1 text-sm bg-gray-100 rounded hover:bg-gray-200 disabled:opacity-50"
            >
              重试
            </button>
          </div>
          <div className="flex items-center gap-2">
            {getStatusIcon(healthStatus)}
            <span className={healthStatus?.success ? 'text-green-700' : 'text-red-700'}>
              {healthStatus?.message || '未测试'}
            </span>
          </div>
          {healthStatus?.error && (
            <div className="mt-2 text-sm text-red-600 bg-red-50 p-2 rounded">
              错误: {healthStatus.error}
            </div>
          )}
        </div>

        {/* Validation */}
        <div className={`border-2 rounded-lg p-4 ${getStatusColor(validationResult)}`}>
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-semibold flex items-center gap-2">
              <CheckCircle className="w-4 h-4" />
              2. 锚点验证
            </h3>
            <button
              onClick={runValidation}
              disabled={isLoading}
              className="px-3 py-1 text-sm bg-gray-100 rounded hover:bg-gray-200 disabled:opacity-50"
            >
              重试
            </button>
          </div>
          <div className="flex items-center gap-2">
            {getStatusIcon(validationResult)}
            <span className={validationResult?.success ? 'text-green-700' : 'text-red-700'}>
              {validationResult?.message || '未测试'}
            </span>
          </div>
          {validationResult?.error && (
            <div className="mt-2 text-sm text-red-600 bg-red-50 p-2 rounded">
              错误: {validationResult.error}
            </div>
          )}
          {validationResult?.data && (
            <div className="mt-2 text-sm text-gray-600">
              <p>预计生成 {validationResult.data.stats.estimated_spans} 个文本段</p>
            </div>
          )}
        </div>

        {/* Assembly */}
        <div className={`border-2 rounded-lg p-4 ${getStatusColor(assembleResult)}`}>
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-semibold flex items-center gap-2">
              <Play className="w-4 h-4" />
              3. 文本组装
            </h3>
            <button
              onClick={runAssemble}
              disabled={isLoading}
              className="px-3 py-1 text-sm bg-gray-100 rounded hover:bg-gray-200 disabled:opacity-50"
            >
              重试
            </button>
          </div>
          <div className="flex items-center gap-2">
            {getStatusIcon(assembleResult)}
            <span className={assembleResult?.success ? 'text-green-700' : 'text-red-700'}>
              {assembleResult?.message || '未测试'}
            </span>
          </div>
          {assembleResult?.error && (
            <div className="mt-2 text-sm text-red-600 bg-red-50 p-2 rounded">
              错误: {assembleResult.error}
            </div>
          )}
        </div>
      </div>

      {/* Assembled Text Preview */}
      {assembledText && (
        <div className="mt-6 p-4 bg-blue-50 rounded-lg">
          <h3 className="font-semibold mb-2 text-blue-800">组装后的文本预览:</h3>
          <div className="text-sm text-gray-700 max-h-40 overflow-y-auto whitespace-pre-wrap border border-blue-200 p-3 rounded bg-white">
            {assembledText}
          </div>
          <div className="mt-2 text-xs text-blue-600">
            文本长度: {assembledText.length} 字符
          </div>
        </div>
      )}

      {/* Debug Info */}
      {assembleResult?.data && (
        <div className="mt-4 p-4 bg-gray-50 rounded-lg">
          <h3 className="font-semibold mb-2 text-gray-800">调试信息:</h3>
          <pre className="text-xs text-gray-600 overflow-x-auto">
            {JSON.stringify(assembleResult.data.spans, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
};

export default AnchorServiceTest; 