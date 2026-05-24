import React, { useMemo } from 'react';
import { Tag, Space } from 'antd';

interface CodeLine {
  lineNumber: number;
  content: string;
  type: 'same' | 'diff-add' | 'diff-remove' | 'diff-modify';
  matchedLine?: number;
}

interface CodeCompareProps {
  codeA: string;
  codeB: string;
  titleA: string;
  titleB: string;
  similarityScore?: number;
  syntaxScore?: number;
  semanticScore?: number;
}

const levenshteinDistance = (s1: string, s2: string): number => {
  const costs: number[] = [];
  
  for (let i = 0; i <= s1.length; i++) {
    let lastValue = i;
    for (let j = 0; j <= s2.length; j++) {
      if (i === 0) {
        costs[j] = j;
      } else if (j > 0) {
        let newValue = costs[j - 1];
        if (s1.charAt(i - 1) !== s2.charAt(j - 1)) {
          newValue = Math.min(Math.min(newValue, lastValue), costs[j]) + 1;
        }
        costs[j - 1] = lastValue;
        lastValue = newValue;
      }
    }
    if (i > 0) {
      costs[s2.length] = lastValue;
    }
  }
  
  return costs[s2.length];
};

const calculateSimilarity = (str1: string, str2: string): number => {
  const longer = str1.length > str2.length ? str1 : str2;
  const shorter = str1.length > str2.length ? str2 : str1;
  
  if (longer.length === 0) return 1.0;
  
  const editDistance = levenshteinDistance(longer, shorter);
  return (longer.length - editDistance) / longer.length;
};

const CodeCompare: React.FC<CodeCompareProps> = ({ codeA, codeB, titleA, titleB, similarityScore, syntaxScore, semanticScore }) => {
  const analyzedLines = useMemo(() => {
    const linesA = codeA.split('\n');
    const linesB = codeB.split('\n');
    
    const resultA: CodeLine[] = [];
    const resultB: CodeLine[] = [];
    
    const maxLen = Math.max(linesA.length, linesB.length);
    
    for (let i = 0; i < maxLen; i++) {
      const lineA = linesA[i] || '';
      const lineB = linesB[i] || '';
      
      let typeA: CodeLine['type'] = 'same';
      let typeB: CodeLine['type'] = 'same';
      
      if (lineA === lineB) {
        typeA = 'same';
        typeB = 'same';
      } else if (!lineA) {
        typeA = 'diff-remove';
        typeB = 'diff-add';
      } else if (!lineB) {
        typeA = 'diff-add';
        typeB = 'diff-remove';
      } else {
        const trimmedA = lineA.trim();
        const trimmedB = lineB.trim();
        
        if (trimmedA.length > 0 && trimmedB.length > 0) {
          const similarity = calculateSimilarity(trimmedA, trimmedB);
          if (similarity > 0.6) {
            typeA = 'diff-modify';
            typeB = 'diff-modify';
          } else {
            typeA = 'diff-add';
            typeB = 'diff-add';
          }
        } else {
          typeA = 'diff-add';
          typeB = 'diff-add';
        }
      }
      
      resultA.push({
        lineNumber: i + 1,
        content: lineA,
        type: typeA,
        matchedLine: i + 1
      });
      
      resultB.push({
        lineNumber: i + 1,
        content: lineB,
        type: typeB,
        matchedLine: i + 1
      });
    }
    
    return { linesA: resultA, linesB: resultB };
  }, [codeA, codeB]);

  const getLineStyle = (type: CodeLine['type']) => {
    switch (type) {
      case 'diff-add':
        return { backgroundColor: '#d4edda' };
      case 'diff-remove':
        return { backgroundColor: '#f8d7da' };
      case 'diff-modify':
        return { backgroundColor: '#fff3cd' };
      default:
        return { backgroundColor: 'transparent' };
    }
  };

  const getLineIcon = (type: CodeLine['type']) => {
    switch (type) {
      case 'diff-add':
        return <span style={{ color: '#28a745', fontWeight: 'bold' }}>+</span>;
      case 'diff-remove':
        return <span style={{ color: '#dc3545', fontWeight: 'bold' }}>-</span>;
      case 'diff-modify':
        return <span style={{ color: '#ffc107', fontWeight: 'bold' }}>~</span>;
      default:
        return <span style={{ color: '#6c757d' }}>&nbsp;</span>;
    }
  };

  const renderCodePanel = (lines: CodeLine[], title: string) => (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
      <div style={{ 
        padding: '8px 12px', 
        backgroundColor: '#1e293b', 
        color: '#f1f5f9',
        fontWeight: 600,
        borderTopLeftRadius: 8,
        borderTopRightRadius: 8
      }}>
        {title}
      </div>
      <div style={{ 
        flex: 1, 
        overflow: 'auto', 
        backgroundColor: '#f8fafc',
        border: '1px solid #e2e8f0',
        borderTop: 'none',
        borderBottomLeftRadius: 8,
        borderBottomRightRadius: 8
      }}>
        {lines.map((line, index) => (
          <div 
            key={index}
            style={{ 
              display: 'flex',
              ...getLineStyle(line.type),
              borderBottom: '1px solid #e2e8f0'
            }}
          >
            <div style={{ 
              width: 50, 
              padding: '4px 8px', 
              textAlign: 'right',
              color: '#94a3b8',
              fontSize: '12px',
              borderRight: '1px solid #e2e8f0',
              backgroundColor: '#f1f5f9'
            }}>
              <span style={{ marginRight: 4 }}>{getLineIcon(line.type)}</span>
              {line.lineNumber}
            </div>
            <pre style={{ 
              flex: 1, 
              margin: 0, 
              padding: '4px 12px',
              fontSize: '13px',
              fontFamily: "'Consolas', 'Monaco', 'Courier New', monospace",
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-all'
            }}>
              {line.content || ' '}
            </pre>
          </div>
        ))}
      </div>
    </div>
  );

  return (
    <div style={{ width: '100%' }}>
      {similarityScore !== undefined && (
        <div style={{ marginBottom: 16, padding: 12, backgroundColor: '#f8fafc', borderRadius: 8 }}>
          <Space>
            <Tag color="purple">综合相似度: {similarityScore}%</Tag>
            {syntaxScore !== undefined && (
              <Tag color="blue">语法相似度: {syntaxScore}%</Tag>
            )}
            {semanticScore !== undefined && (
              <Tag color="green">语义相似度: {semanticScore}%</Tag>
            )}
          </Space>
        </div>
      )}
      
      <Space align="center" size={16} style={{ width: '100%' }}>
        {renderCodePanel(analyzedLines.linesA, titleA)}
        {renderCodePanel(analyzedLines.linesB, titleB)}
      </Space>
      
      <div style={{ marginTop: 16, padding: 12, backgroundColor: '#e0f2fe', borderRadius: 8 }}>
        <div style={{ fontSize: '12px', color: '#0369a1' }}>
          <strong>图例说明：</strong>
          <Space size={16}>
            <span>
              <span style={{ display: 'inline-block', width: 16, height: 16, backgroundColor: '#d4edda', marginRight: 4 }}></span>
              新增/不同
            </span>
            <span>
              <span style={{ display: 'inline-block', width: 16, height: 16, backgroundColor: '#f8d7da', marginRight: 4 }}></span>
              删除/缺失
            </span>
            <span>
              <span style={{ display: 'inline-block', width: 16, height: 16, backgroundColor: '#fff3cd', marginRight: 4 }}></span>
              修改/相似
            </span>
            <span>
              <span style={{ display: 'inline-block', width: 16, height: 16, backgroundColor: 'transparent', border: '1px solid #e2e8f0', marginRight: 4 }}></span>
              相同
            </span>
          </Space>
        </div>
      </div>
    </div>
  );
};

export default CodeCompare;