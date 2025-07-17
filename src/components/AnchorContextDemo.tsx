import React, { useState } from 'react';
import { buildAnchorContext } from '../services/anchorService';
import type { Anchor, AnchorContextRequest, AnchorContextResponse } from '../services/anchorService';

interface AnchorContextDemoProps {
  onBack: () => void;
}

const AnchorContextDemo: React.FC<AnchorContextDemoProps> = ({ onBack }) => {
  const [contextResponse, setContextResponse] = useState<AnchorContextResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 预设的测试锚点
  const testAnchors = {
    anchor1: { node_id: "a1_5", chunk_id: "ch1_5", chapter_id: 1 },
    anchor2: { node_id: "a1_10", chunk_id: "ch1_10", chapter_id: 1 },
    anchor3: { node_id: "a1_15", chunk_id: "ch1_15", chapter_id: 1 },
    anchor4: { node_id: "a1_20", chunk_id: "ch1_20", chapter_id: 1 },
  };

  const runContextTest = async (
    currentAnchor: Anchor,
    previousAnchor?: Anchor,
    includeTail: boolean = false,
    isLastInChapter: boolean = false
  ) => {
    setIsLoading(true);
    setError(null);

    try {
      const request: AnchorContextRequest = {
        current_anchor: currentAnchor,
        previous_anchor: previousAnchor,
        include_tail: includeTail,
        is_last_anchor_in_chapter: isLastInChapter
      };

      console.log('发送锚点上下文请求:', request);
      const response = await buildAnchorContext(request);
      setContextResponse(response);
    } catch (err) {
      console.error('锚点上下文构造失败:', err);
      setError(err instanceof Error ? err.message : '构造上下文失败');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="galgame-container">
      {/* 顶部状态栏 */}
      <div className="top-status-bar">
        <div className="status-left">
          <button 
            className="status-btn" 
            title="返回主菜单"
            onClick={onBack}
          >
            <span>← 返回</span>
          </button>
        </div>
        <div className="status-right">
          <span className="text-sm text-gray-600">锚点上下文构造演示</span>
        </div>
      </div>

      {/* 主内容区域 */}
      <div className="p-6 max-w-6xl mx-auto bg-white rounded-lg shadow-lg" style={{ marginTop: '80px', height: 'calc(100vh - 100px)', overflow: 'auto' }}>
        <h2 className="text-2xl font-bold text-gray-800 mb-6">锚点上下文构造演示</h2>
        
        {/* 测试按钮区域 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <div className="p-4 border rounded-lg">
            <h3 className="font-semibold mb-3">基础测试</h3>
            <div className="space-y-2">
              <button
                onClick={() => runContextTest(testAnchors.anchor1)}
                disabled={isLoading}
                className="w-full px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
              >
                测试单个锚点 (ch1_5)
              </button>
              <button
                onClick={() => runContextTest(testAnchors.anchor2, testAnchors.anchor1)}
                disabled={isLoading}
                className="w-full px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
              >
                测试前后锚点 (ch1_5 → ch1_10)
              </button>
            </div>
          </div>

          <div className="p-4 border rounded-lg">
            <h3 className="font-semibold mb-3">高级测试</h3>
            <div className="space-y-2">
              <button
                onClick={() => runContextTest(testAnchors.anchor3, testAnchors.anchor2, true, false)}
                disabled={isLoading}
                className="w-full px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700 disabled:opacity-50"
              >
                包含尾部内容 (ch1_15)
              </button>
              <button
                onClick={() => runContextTest(testAnchors.anchor4, testAnchors.anchor3, true, true)}
                disabled={isLoading}
                className="w-full px-4 py-2 bg-orange-600 text-white rounded hover:bg-orange-700 disabled:opacity-50"
              >
                章节最后锚点 (ch1_20)
              </button>
            </div>
          </div>
        </div>

        {/* 加载状态 */}
        {isLoading && (
          <div className="text-center py-4">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <p className="mt-2 text-gray-600">正在构造上下文...</p>
          </div>
        )}

        {/* 错误信息 */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <h3 className="font-semibold text-red-800 mb-2">错误</h3>
            <p className="text-red-700">{error}</p>
          </div>
        )}

        {/* 结果展示 */}
        {contextResponse && (
          <div className="space-y-6">
            {/* 统计信息 */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h3 className="font-semibold text-blue-800 mb-3">上下文统计</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <span className="font-medium">总长度:</span>
                  <span className="ml-2">{contextResponse.context_stats.total_length} 字符</span>
                </div>
                <div>
                  <span className="font-medium">包含块数:</span>
                  <span className="ml-2">{contextResponse.context_stats.chunks_included}</span>
                </div>
                <div>
                  <span className="font-medium">有前文:</span>
                  <span className="ml-2">{contextResponse.context_stats.has_prefix ? '是' : '否'}</span>
                </div>
                <div>
                  <span className="font-medium">有尾部:</span>
                  <span className="ml-2">{contextResponse.context_stats.has_tail ? '是' : '否'}</span>
                </div>
              </div>
            </div>

            {/* 锚点信息 */}
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <h3 className="font-semibold text-green-800 mb-3">当前锚点</h3>
              <div className="text-sm">
                <p><span className="font-medium">节点ID:</span> {contextResponse.current_anchor.node_id}</p>
                <p><span className="font-medium">块ID:</span> {contextResponse.current_anchor.chunk_id}</p>
                <p><span className="font-medium">章节ID:</span> {contextResponse.current_anchor.chapter_id}</p>
              </div>
            </div>

            {/* 构造的上下文 */}
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
              <h3 className="font-semibold text-gray-800 mb-3">构造的上下文</h3>
              <div className="bg-white border rounded p-4 max-h-96 overflow-y-auto">
                <pre className="whitespace-pre-wrap text-sm text-gray-700 leading-relaxed">
                  {contextResponse.context}
                </pre>
              </div>
              <div className="mt-2 text-xs text-gray-500">
                这段文本可以直接传给 LLM 服务作为上下文
              </div>
            </div>

            {/* 详细统计 */}
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <h3 className="font-semibold text-yellow-800 mb-3">详细统计</h3>
              <div className="text-sm space-y-1">
                <p><span className="font-medium">提供了前一锚点:</span> {contextResponse.context_stats.previous_anchor_provided ? '是' : '否'}</p>
                <p><span className="font-medium">请求包含尾部:</span> {contextResponse.context_stats.include_tail_requested ? '是' : '否'}</p>
                <p><span className="font-medium">是章节最后锚点:</span> {contextResponse.context_stats.is_last_anchor_in_chapter ? '是' : '否'}</p>
              </div>
            </div>
          </div>
        )}

        {/* 说明文档 */}
        <div className="mt-8 bg-gray-100 rounded-lg p-4">
          <h3 className="font-semibold text-gray-800 mb-3">功能说明</h3>
          <div className="text-sm text-gray-700 space-y-2">
            <p><strong>锚点上下文构造逻辑:</strong></p>
            <ol className="list-decimal list-inside space-y-1 ml-4">
              <li>定位当前锚点在章节中的位置</li>
              <li>提取"前文" (从上一锚点结束后 或 章节开头 到当前锚点前)</li>
              <li>追加锚点本身</li>
              <li>视情况再加"尾部" (如果是章节最后锚点且需要)</li>
            </ol>
            <p className="mt-3"><strong>使用场景:</strong> 为LLM服务提供精确的上下文，确保生成内容与故事情节紧密衔接。</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AnchorContextDemo;
