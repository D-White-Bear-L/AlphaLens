<template>
  <div class="news-trace-result">
    <!-- 置信度和深度标签 -->
    <div class="badges-container">
      <div class="confidence-badge" :class="confidenceClass">
        {{ confidenceText }}
      </div>
      <div v-if="maxDepth" class="depth-badge">
        <el-icon><DataAnalysis /></el-icon>
        <span>{{ depthText }}</span>
      </div>
    </div>

    <!-- 原始声明 -->
    <h3 class="original-claim">溯源事件: {{ result.original_claim }}</h3>

    <!-- 摘要 -->
    <div class="summary">
      {{ result.summary || '暂无摘要' }}
    </div>

    <!-- 标签页 -->
    <el-tabs v-model="activeTab" class="result-tabs">
      <!-- 来源列表 -->
      <el-tab-pane name="sources">
        <template #label>
          <el-icon><Document /></el-icon>
          <span>来源列表</span>
        </template>
        <div class="sources-section">
          <h4>
            <el-icon><Document /></el-icon>
            来源列表 ({{ sources.length }})
          </h4>
          <div v-if="sources.length === 0" class="empty-state">
            <div class="empty-icon">
              <el-icon :size="48"><Box /></el-icon>
            </div>
            <p>未找到相关来源</p>
          </div>
          <div v-else class="sources-grid">
            <el-card v-for="(source, index) in sources" :key="index" class="source-card">
              <div class="source-title">
                <a :href="source.url" target="_blank" rel="noopener noreferrer">
                  {{ index + 1 }}. {{ source.title || '无标题' }}
                </a>
              </div>
              <div class="source-url">{{ source.url }}</div>
              <div class="source-snippet">
                {{ source.snippet ? (source.snippet.length > 200 ? source.snippet.substring(0, 200) + '...' : source.snippet) : '暂无摘要' }}
              </div>
              <div class="source-meta">
                <span v-if="source.published_date">
                  <el-icon><Calendar /></el-icon>
                  {{ source.published_date }}
                </span>
                <span v-if="source.author">
                  <el-icon><Edit /></el-icon>
                  {{ source.author }}
                </span>
                <span class="source-score">相关性: {{ ((source.relevance_score || 0) * 100).toFixed(0) }}%</span>
              </div>
            </el-card>
          </div>
        </div>
      </el-tab-pane>

      <!-- 时间线 -->
      <el-tab-pane name="timeline">
        <template #label>
          <el-icon><Calendar /></el-icon>
          <span>时间线</span>
        </template>
        <div class="timeline-section">
          <h4>
            <el-icon><Calendar /></el-icon>
            事件时间线
          </h4>
          <div v-if="timeline.length === 0" class="empty-state">
            <div class="empty-icon">
              <el-icon :size="48"><Calendar /></el-icon>
            </div>
            <p>暂无时间线数据</p>
          </div>
          <div v-else class="timeline-container">
            <div class="timeline-line"></div>
            <div v-for="(event, index) in sortedTimeline" :key="index" class="timeline-event">
              <div class="timeline-dot"></div>
              <div class="timeline-date">
                {{ event.date || '日期未知' }}
                <span class="timeline-importance" :class="`importance-${event.importance || 'medium'}`">
                  {{ event.importance || 'medium' }}
                </span>
              </div>
              <div class="timeline-event-text">{{ event.event }}</div>
              <a v-if="event.source_url" :href="event.source_url" target="_blank" class="source-link">
                查看来源
              </a>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- 因果关系 -->
      <el-tab-pane name="causal">
        <template #label>
          <el-icon><Link /></el-icon>
          <span>因果关系</span>
        </template>
        <div class="causal-section">
          <h4>
            <el-icon><Link /></el-icon>
            因果关系
          </h4>
          <div v-if="causalRelations.length === 0" class="empty-state">
            <div class="empty-icon">
              <el-icon :size="48"><Link /></el-icon>
            </div>
            <p>暂无因果关系数据</p>
          </div>
          <div v-else>
            <div v-for="(rel, index) in causalRelations" :key="index" class="causal-relation">
              <div class="causal-cause">
                <strong>原因:</strong> {{ rel.cause }}
              </div>
              <div class="causal-arrow">↓</div>
              <div class="causal-effect">
                <strong>结果:</strong> {{ rel.effect }}
              </div>
              <div class="causal-meta">
                <span>关系类型: {{ getRelationTypeText(rel.relationship_type) }}</span>
                <span>置信度: {{ ((rel.confidence || 0) * 100).toFixed(0) }}%</span>
                <span v-if="rel.evidence">证据: {{ rel.evidence }}</span>
              </div>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- 知识图谱 -->
      <el-tab-pane name="knowledge">
        <template #label>
          <el-icon><Share /></el-icon>
          <span>知识图谱</span>
        </template>
        <div class="kg-section">
          <h4>
            <el-icon><Share /></el-icon>
            知识图谱
          </h4>
          <div v-if="!knowledgeGraph || !knowledgeGraph.nodes || knowledgeGraph.nodes.length === 0" class="empty-state">
            <div class="empty-icon">
              <el-icon :size="48"><Share /></el-icon>
            </div>
            <p>暂无知识图谱数据</p>
          </div>
          <div v-else>
            <div class="kg-stats">
              <div class="kg-stat-item">
                <span>节点数:</span>
                <span class="kg-stat-value">{{ knowledgeGraph.nodes.length }}</span>
              </div>
              <div class="kg-stat-item">
                <span>关系数:</span>
                <span class="kg-stat-value">{{ (knowledgeGraph.edges || []).length }}</span>
              </div>
            </div>
            <div class="kg-toggle-view">
              <el-button :type="kgView === 'graph' ? 'primary' : ''" @click="kgView = 'graph'">
                <el-icon><DataAnalysis /></el-icon>
                图谱视图
              </el-button>
              <el-button :type="kgView === 'list' ? 'primary' : ''" @click="kgView = 'list'">
                <el-icon><List /></el-icon>
                列表视图
              </el-button>
            </div>
            <!-- 图例 -->
            <div class="kg-legend">
              <div class="kg-legend-title">
                <el-icon><InfoFilled /></el-icon>
                <span>图例</span>
              </div>
              <div class="kg-legend-items">
                <div v-for="type in nodeTypes" :key="type.value" class="kg-legend-item">
                  <div class="kg-legend-color" :style="{ backgroundColor: getTypeColor(type.value) }"></div>
                  <el-icon class="kg-legend-icon"><component :is="getTypeIcon(type.value)" /></el-icon>
                  <span class="kg-legend-label">{{ type.label }}</span>
                </div>
              </div>
            </div>
            <div v-if="kgView === 'graph'" id="kg-network" class="kg-network"></div>
            <div v-else class="kg-list">
              <div 
                v-for="node in knowledgeGraph.nodes" 
                :key="node.id" 
                class="kg-node-item"
                :style="{ borderLeftColor: getTypeColor(node.type) }"
              >
                <div class="kg-node-color-indicator" :style="{ backgroundColor: getTypeColor(node.type) }"></div>
                <span class="kg-node-type">
                  <el-icon><component :is="getTypeIcon(node.type)" /></el-icon>
                  {{ getTypeLabel(node.type) }}
                </span>
                <span class="kg-node-label">{{ node.label }}</span>
              </div>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- 层次结构 -->
      <el-tab-pane name="hierarchy">
        <template #label>
          <el-icon><Operation /></el-icon>
          <span>层次结构</span>
        </template>
        <div class="hierarchy-section">
          <h4>
            <el-icon><Operation /></el-icon>
            溯源层次结构
          </h4>
          <div v-if="!hierarchyGraph || !hierarchyGraph.nodes || hierarchyGraph.nodes.length === 0" class="empty-state">
            <div class="empty-icon">
              <el-icon :size="48"><Operation /></el-icon>
            </div>
            <p>暂无层次结构数据</p>
          </div>
          <div v-else>
            <div class="hierarchy-stats">
              <div class="hierarchy-stat-item">
                <span>节点数:</span>
                <span class="hierarchy-stat-value">{{ hierarchyGraph.nodes.length }}</span>
              </div>
              <div class="hierarchy-stat-item">
                <span>最大深度:</span>
                <span class="hierarchy-stat-value">{{ hierarchyGraph.max_depth + 1 }} 层</span>
              </div>
              <div class="hierarchy-stat-item">
                <span>根节点:</span>
                <span class="hierarchy-stat-value">{{ getRootNodeLabel() }}</span>
              </div>
            </div>
            <div class="hierarchy-toggle-view">
              <el-button :type="hierarchyView === 'tree' ? 'primary' : ''" @click="hierarchyView = 'tree'">
                <el-icon><DataAnalysis /></el-icon>
                树形视图
              </el-button>
              <el-button :type="hierarchyView === 'list' ? 'primary' : ''" @click="hierarchyView = 'list'">
                <el-icon><List /></el-icon>
                列表视图
              </el-button>
            </div>
            <div v-if="hierarchyView === 'tree'" id="hierarchy-network" class="hierarchy-network"></div>
            <div v-else class="hierarchy-list">
              <div v-for="level in sortedHierarchyLevels" :key="level" class="hierarchy-level">
                <div class="hierarchy-level-header">
                  <el-icon><Folder /></el-icon>
                  第 {{ level + 1 }} 层 ({{ getNodesByLevel(level).length }} 个节点)
                </div>
                <div class="hierarchy-level-nodes">
                  <div 
                    v-for="node in getNodesByLevel(level)" 
                    :key="node.id" 
                    class="hierarchy-node-item"
                  >
                    <div class="hierarchy-node-main">
                      <span class="hierarchy-node-label">{{ node.label }}</span>
                      <span class="hierarchy-node-level">L{{ node.level + 1 }}</span>
                    </div>
                    <div v-if="node.description" class="hierarchy-node-desc">
                      {{ node.description }}
                    </div>
                    <div class="hierarchy-node-meta">
                      <span v-if="node.source_count > 0">
                        <el-icon><Document /></el-icon>
                        {{ node.source_count }} 个来源
                      </span>
                      <span v-if="node.children_count > 0">
                        <el-icon><FolderOpened /></el-icon>
                        {{ node.children_count }} 个子节点
                      </span>
                    </div>
                    <div v-if="node.source_urls && node.source_urls.length > 0" class="hierarchy-node-sources">
                      <div 
                        v-for="(url, idx) in node.source_urls.slice(0, 3)" 
                        :key="idx"
                        class="hierarchy-source-link"
                      >
                        <a :href="url" target="_blank" rel="noopener noreferrer">
                          {{ url }}
                        </a>
                      </div>
                      <div v-if="node.source_urls.length > 3" class="hierarchy-more-sources">
                        还有 {{ node.source_urls.length - 3 }} 个来源...
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- 深度分析 -->
      <el-tab-pane name="analysis">
        <template #label>
          <el-icon><Search /></el-icon>
          <span>深度分析</span>
        </template>
        <div class="analysis-section">
          <h4>
            <el-icon><Search /></el-icon>
            深度分析
          </h4>
          <div class="analysis-content">
            {{ result.analysis || result.summary || '暂无深度分析' }}
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, markRaw } from 'vue'
import { 
  Document, 
  Box, 
  Calendar, 
  Edit, 
  Link, 
  Share, 
  DataAnalysis, 
  List, 
  Search,
  User,
  OfficeBuilding,
  Location,
  InfoFilled,
  QuestionFilled,
  Operation,
  Folder,
  FolderOpened
} from '@element-plus/icons-vue'

const props = defineProps({
  result: {
    type: Object,
    required: true
  }
})

const activeTab = ref('sources')
const kgView = ref('graph')
const hierarchyView = ref('tree')

const confidence = computed(() => props.result.confidence || 0)
const confidenceClass = computed(() => {
  if (confidence.value >= 0.7) return 'confidence-high'
  if (confidence.value >= 0.4) return 'confidence-medium'
  return 'confidence-low'
})
const confidenceText = computed(() => {
  if (confidence.value >= 0.7) return `置信度: 高 (${(confidence.value * 100).toFixed(0)}%)`
  if (confidence.value >= 0.4) return `置信度: 中 (${(confidence.value * 100).toFixed(0)}%)`
  return `置信度: 低 (${(confidence.value * 100).toFixed(0)}%)`
})

const maxDepth = computed(() => props.result.max_depth || null)
const depthText = computed(() => {
  const depthMap = {
    1: '浅层 (快速)',
    2: '中等 (推荐)',
    3: '深层 (详细)',
    4: '极深 (全面)'
  }
  return depthMap[maxDepth.value] || `深度 ${maxDepth.value}`
})

const sources = computed(() => props.result.sources || [])
const timeline = computed(() => props.result.timeline || [])
const causalRelations = computed(() => props.result.causal_relations || [])
const knowledgeGraph = computed(() => props.result.knowledge_graph || null)
const hierarchyGraph = computed(() => props.result.hierarchy_graph || null)

const sortedTimeline = computed(() => {
  return [...timeline.value].sort((a, b) => {
    const dateA = a.date || ''
    const dateB = b.date || ''
    return dateA.localeCompare(dateB)
  })
})

const getRelationTypeText = (type) => {
  const typeMap = {
    'direct': '直接',
    'indirect': '间接',
    'correlation': '相关'
  }
  return typeMap[type] || type
}

const getTypeLabel = (type) => {
  const typeMap = {
    'person': '【人物】',
    'organization': '【组织】',
    'location': '【地点】',
    'concept': '【概念】',
    'event': '【事件】',
    'unknown': '【未知】'
  }
  return typeMap[type] || type
}

const getTypeIcon = (type) => {
  const iconMap = {
    'person': markRaw(User),
    'organization': markRaw(OfficeBuilding),
    'location': markRaw(Location),
    'concept': markRaw(InfoFilled),
    'event': markRaw(Calendar),
    'unknown': markRaw(QuestionFilled)
  }
  return iconMap[type] || markRaw(QuestionFilled)
}

// 节点类型配置（用于图例）
const nodeTypes = [
  { value: 'person', label: '人物' },
  { value: 'organization', label: '组织' },
  { value: 'location', label: '地点' },
  { value: 'concept', label: '概念' },
  { value: 'event', label: '事件' },
  { value: 'unknown', label: '未知' }
]

// 获取节点类型对应的颜色（高区分度配色方案）
const getTypeColor = (type) => {
  const typeColors = {
    'person': '#E74C3C',      // 鲜艳红色 - 人物
    'organization': '#3498DB', // 鲜明蓝色 - 组织
    'location': '#9B59B6',     // 紫色 - 地点
    'concept': '#F39C12',      // 橙色 - 概念
    'event': '#27AE60',        // 鲜明绿色 - 事件
    'unknown': '#95A5A6'       // 中灰色 - 未知
  }
  return typeColors[type] || typeColors.unknown
}

// 知识图谱可视化
let kgNetwork = null

const initKnowledgeGraph = () => {
  if (!window.vis || !knowledgeGraph.value) return

  const container = document.getElementById('kg-network')
  if (!container) return

  const typeColors = {
    'person': '#E74C3C',      // 鲜艳红色 - 人物
    'organization': '#3498DB', // 鲜明蓝色 - 组织
    'location': '#9B59B6',     // 紫色 - 地点
    'concept': '#F39C12',      // 橙色 - 概念
    'event': '#27AE60',        // 鲜明绿色 - 事件
    'unknown': '#95A5A6'       // 中灰色 - 未知
  }

  const nodes = new window.vis.DataSet(
    knowledgeGraph.value.nodes.map(node => ({
      id: node.id,
      label: node.label || node.id, // 确保有标签，如果没有则使用ID
      title: `${getTypeLabel(node.type)}\n${node.label || node.id}${node.properties ? '\n' + Object.entries(node.properties).map(([k, v]) => `${k}: ${v}`).join('\n') : ''}`,
      color: {
        background: typeColors[node.type] || typeColors.unknown,
        border: '#333',
        highlight: {
          background: typeColors[node.type] || typeColors.unknown,
          border: '#667eea'
        }
      },
      shape: 'dot',
      size: 20,
      font: { size: 14, color: '#333', face: 'Microsoft YaHei, Arial, sans-serif' }, // 使用中文字体
      borderWidth: 2
    }))
  )

  const edges = new window.vis.DataSet(
    (knowledgeGraph.value.edges || []).map(edge => ({
      from: edge.source,
      to: edge.target,
      label: edge.relationship,
      width: edge.weight ? Math.max(1, edge.weight * 3) : 1,
      color: { color: '#667eea', highlight: '#764ba2' },
      arrows: { to: { enabled: true, scaleFactor: 0.8 } },
      smooth: { type: 'continuous', roundness: 0.5 }
    }))
  )

  const data = { nodes, edges }
  const options = {
    nodes: {
      shape: 'dot',
      size: 25,
      font: { 
        size: 14,
        face: 'Microsoft YaHei, Arial, sans-serif' // 使用中文字体
      },
      borderWidth: 2,
      shadow: true
    },
    edges: {
      width: 2,
      color: { color: '#667eea', highlight: '#764ba2' },
      smooth: { type: 'continuous', roundness: 0.5 },
      arrows: { to: { enabled: true, scaleFactor: 0.8 } },
      font: {
        size: 12,
        face: 'Microsoft YaHei, Arial, sans-serif', // 边的标签也使用中文字体
        align: 'middle'
      }
    },
    physics: {
      enabled: true,
      stabilization: { enabled: true, iterations: 200 },
      barnesHut: {
        gravitationalConstant: -2000,
        centralGravity: 0.3,
        springLength: 200,
        springConstant: 0.04,
        damping: 0.09
      }
    },
    interaction: {
      hover: true,
      zoomView: true,
      dragView: true
    }
  }

  kgNetwork = new window.vis.Network(container, data, options)
}

onMounted(() => {
  // 加载 vis-network 库
  if (!window.vis) {
    const script = document.createElement('script')
    script.src = 'https://unpkg.com/vis-network/standalone/umd/vis-network.min.js'
    script.onload = () => {
      if (activeTab.value === 'knowledge' && kgView.value === 'graph') {
        initKnowledgeGraph()
      }
    }
    document.head.appendChild(script)
  } else if (activeTab.value === 'knowledge' && kgView.value === 'graph') {
    initKnowledgeGraph()
  }
})

watch([activeTab, kgView], () => {
  if (activeTab.value === 'knowledge' && kgView.value === 'graph') {
    setTimeout(() => {
      initKnowledgeGraph()
    }, 100)
  }
})

watch([activeTab, hierarchyView], () => {
  if (activeTab.value === 'hierarchy' && hierarchyView.value === 'tree') {
    setTimeout(() => {
      initHierarchyGraph()
    }, 100)
  }
})

// 层次结构相关方法
const getRootNodeLabel = () => {
  if (!hierarchyGraph.value || !hierarchyGraph.value.nodes) return 'N/A'
  const rootNode = hierarchyGraph.value.nodes.find(n => n.id === hierarchyGraph.value.root_id)
  return rootNode ? rootNode.label : 'N/A'
}

const sortedHierarchyLevels = computed(() => {
  if (!hierarchyGraph.value || !hierarchyGraph.value.nodes) return []
  const levels = new Set(hierarchyGraph.value.nodes.map(n => n.level))
  return Array.from(levels).sort((a, b) => a - b)
})

const getNodesByLevel = (level) => {
  if (!hierarchyGraph.value || !hierarchyGraph.value.nodes) return []
  return hierarchyGraph.value.nodes.filter(n => n.level === level)
}

// 层次结构图可视化
let hierarchyNetwork = null

const initHierarchyGraph = () => {
  if (!window.vis || !hierarchyGraph.value) return

  const container = document.getElementById('hierarchy-network')
  if (!container) return

  // 清除之前的网络
  if (hierarchyNetwork) {
    hierarchyNetwork.destroy()
    hierarchyNetwork = null
  }

  // 准备节点数据
  const nodes = new window.vis.DataSet(
    hierarchyGraph.value.nodes.map(node => {
      // 根据层级设置不同的颜色
      const levelColors = {
        0: '#FF6B6B',  // 根节点 - 红色
        1: '#4ECDC4',  // Level 1 - 青色
        2: '#95E1D3',  // Level 2 - 浅青色
        3: '#FFE66D',  // Level 3 - 黄色
        4: '#A8E6CF',  // Level 4+ - 浅绿色
      }
      const color = levelColors[node.level] || '#D3D3D3'
      
      // 构建节点标题（用于悬停提示）
      // 显示时转换为用户友好的层级编号（从1开始）
      let title = `第 ${node.level + 1} 层: ${node.label || node.id}`
      if (node.description) {
        title += `\n\n描述: ${node.description}`
      }
      if (node.source_count > 0) {
        title += `\n来源数: ${node.source_count}`
        if (node.source_urls && node.source_urls.length > 0) {
          title += `\n来源: ${node.source_urls.slice(0, 3).join(', ')}`
          if (node.source_urls.length > 3) {
            title += `\n...还有 ${node.source_urls.length - 3} 个来源`
          }
        }
      }
      if (node.children_count > 0) {
        title += `\n子节点数: ${node.children_count}`
      }
      
      // 处理标签：如果太长，自动换行（每行最多15个字符）
      let displayLabel = node.label || node.id
      if (displayLabel.length > 30) {
        // 对于很长的标签，尝试在合适的位置换行
        const words = displayLabel.split(/[\s，。、]/)
        let lines = []
        let currentLine = ''
        
        for (let word of words) {
          if ((currentLine + word).length <= 20) {
            currentLine += (currentLine ? ' ' : '') + word
          } else {
            if (currentLine) lines.push(currentLine)
            currentLine = word
          }
        }
        if (currentLine) lines.push(currentLine)
        displayLabel = lines.join('\n')
      }

      // 计算节点宽度，根据标签长度自适应
      const labelLength = node.label ? node.label.length : 0
      const minWidth = 100
      const maxWidth = 300
      const width = Math.min(maxWidth, Math.max(minWidth, labelLength * 8 + 40))
      
      return {
        id: node.id,
        label: displayLabel, // 使用处理后的标签（支持换行）
        title: title,
        level: node.level,
        color: {
          background: color,
          border: '#333',
          highlight: {
            background: color,
            border: '#667eea'
          }
        },
        shape: 'box',
        widthConstraint: {
          minimum: minWidth,
          // maximum: maxWidth
        },
        heightConstraint: {
          minimum: 40,
          // maximum: 100
        },
        font: { 
          size: 13 + (node.level === 0 ? 2 : 0), // 根节点字体稍大
          color: '#333',
          bold: node.level === 0,
          face: 'Microsoft YaHei, Arial, sans-serif', // 使用中文字体
          multi: true, // 支持多行文本
          align: 'center'
        },
        borderWidth: node.level === 0 ? 3 : 2,
        margin: {
          top: 10,
          right: 10,
          bottom: 10,
          left: 10
        }
      }
    })
  )

  // 准备边数据（父子关系）
  const edges = new window.vis.DataSet(
    hierarchyGraph.value.nodes
      .filter(node => node.parent_id) // 只包含有父节点的节点
      .map(node => ({
        from: node.parent_id,
        to: node.id,
        arrows: { to: { enabled: true, scaleFactor: 0.8 } },
        color: { color: '#667eea', highlight: '#764ba2' },
        width: 2,
        smooth: { type: 'continuous', roundness: 0.5 }
      }))
  )

  const data = { nodes, edges }
  
  // 使用层次布局
  const options = {
    layout: {
      hierarchical: {
        enabled: true,
        direction: 'UD', // 从上到下
        sortMethod: 'directed', // 有向排序
        levelSeparation: 120, // 层级间距（增加以适应更大的节点）
        nodeSpacing: 180, // 同层节点间距（增加以适应更宽的节点）
        treeSpacing: 250, // 树间距（增加以适应更宽的节点）
        blockShifting: true,
        edgeMinimization: true,
        parentCentralization: true
      }
    },
    nodes: {
      shape: 'box',
      font: { 
        size: 13,
        face: 'Microsoft YaHei, Arial, sans-serif', // 使用中文字体
        multi: true, // 支持多行文本
        align: 'center'
      },
      borderWidth: 2,
      shadow: true,
      margin: {
        top: 10,
        right: 10,
        bottom: 10,
        left: 10
      },
      widthConstraint: {
        minimum: 100,
        // maximum: 300
      },
      heightConstraint: {
        minimum: 40,
        // maximum: 120
      }
    },
    edges: {
      width: 2,
      color: { color: '#667eea', highlight: '#764ba2' },
      smooth: { type: 'continuous', roundness: 0.5 },
      arrows: { to: { enabled: true, scaleFactor: 0.8 } }
    },
    physics: {
      enabled: false // 层次布局不需要物理引擎
    },
    interaction: {
      hover: true,
      zoomView: true,
      dragView: true,
      tooltipDelay: 200
    }
  }

  hierarchyNetwork = new window.vis.Network(container, data, options)
  
  // 添加点击事件
  hierarchyNetwork.on('click', (params) => {
    if (params.nodes.length > 0) {
      const nodeId = params.nodes[0]
      const node = hierarchyGraph.value.nodes.find(n => n.id === nodeId)
      if (node && node.source_urls && node.source_urls.length > 0) {
        // 可以在这里添加显示来源的弹窗或其他交互
        console.log('Node clicked:', node)
      }
    }
  })
}

onMounted(() => {
  // 加载 vis-network 库
  if (!window.vis) {
    const script = document.createElement('script')
    script.src = 'https://unpkg.com/vis-network/standalone/umd/vis-network.min.js'
    script.onload = () => {
      if (activeTab.value === 'knowledge' && kgView.value === 'graph') {
        initKnowledgeGraph()
      }
      if (activeTab.value === 'hierarchy' && hierarchyView.value === 'tree') {
        initHierarchyGraph()
      }
    }
    document.head.appendChild(script)
  } else {
    if (activeTab.value === 'knowledge' && kgView.value === 'graph') {
      initKnowledgeGraph()
    }
    if (activeTab.value === 'hierarchy' && hierarchyView.value === 'tree') {
      initHierarchyGraph()
    }
  }
})
</script>

<style scoped>
.news-trace-result {
  padding: 20px;
}

.badges-container {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 15px;
  flex-wrap: wrap;
}

.confidence-badge {
  display: inline-block;
  padding: 8px 16px;
  border-radius: 20px;
  font-weight: 600;
}

.depth-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 20px;
  font-weight: 600;
  background: #e3f2fd;
  color: #1976d2;
  font-size: 14px;
}

.depth-badge .el-icon {
  font-size: 16px;
}

.confidence-high {
  background: #d4edda;
  color: #155724;
}

.confidence-medium {
  background: #fff3cd;
  color: #856404;
}

.confidence-low {
  background: #f8d7da;
  color: #721c24;
}

.original-claim {
  font-size: 18px;
  color: #333;
  margin-bottom: 15px;
}

.summary {
  background: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  border-left: 4px solid #409eff;
  margin-bottom: 20px;
  line-height: 1.6;
  white-space: pre-wrap;
}

.result-tabs {
  margin-top: 20px;
}

.sources-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 20px;
  margin-top: 20px;
}

.source-card {
  transition: transform 0.2s;
}

.source-card:hover {
  transform: translateY(-3px);
}

.source-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 8px;
}

.source-title a {
  color: #409eff;
  text-decoration: none;
}

.source-title a:hover {
  text-decoration: underline;
}

.source-url {
  color: #666;
  font-size: 14px;
  margin-bottom: 8px;
  word-break: break-all;
}

.source-snippet {
  color: #555;
  font-size: 14px;
  line-height: 1.5;
  margin-bottom: 10px;
}

.source-meta {
  display: flex;
  gap: 15px;
  font-size: 12px;
  color: #888;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid #e0e0e0;
}

.source-score {
  display: inline-block;
  padding: 4px 10px;
  background: #e3f2fd;
  color: #1976d2;
  border-radius: 12px;
  font-weight: 600;
}

.timeline-container {
  position: relative;
  padding-left: 30px;
  margin-top: 20px;
}

.timeline-line {
  position: absolute;
  left: 10px;
  top: 0;
  bottom: 0;
  width: 2px;
  background: #409eff;
}

.timeline-event {
  position: relative;
  margin-bottom: 25px;
  padding-left: 20px;
}

.timeline-dot {
  position: absolute;
  left: -25px;
  top: 5px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #409eff;
  border: 3px solid white;
  box-shadow: 0 0 0 2px #409eff;
}

.timeline-date {
  font-weight: 600;
  color: #409eff;
  margin-bottom: 5px;
}

.timeline-event-text {
  color: #555;
  line-height: 1.6;
}

.timeline-importance {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 12px;
  margin-left: 10px;
}

.importance-high {
  background: #f8d7da;
  color: #721c24;
}

.importance-medium {
  background: #fff3cd;
  color: #856404;
}

.importance-low {
  background: #d1ecf1;
  color: #0c5460;
}

.source-link {
  display: inline-block;
  margin-top: 5px;
  font-size: 14px;
  color: #409eff;
  text-decoration: none;
}

.source-link:hover {
  text-decoration: underline;
}

.causal-relation {
  background: #f8f9fa;
  border-left: 4px solid #409eff;
  padding: 15px;
  margin-bottom: 15px;
  border-radius: 4px;
}

.causal-cause, .causal-effect {
  margin: 8px 0;
  padding: 8px;
  background: white;
  border-radius: 4px;
}

.causal-cause {
  border-left: 3px solid #dc3545;
}

.causal-effect {
  border-left: 3px solid #28a745;
}

.causal-arrow {
  text-align: center;
  font-size: 24px;
  color: #409eff;
  margin: 5px 0;
}

.causal-meta {
  display: flex;
  gap: 15px;
  margin-top: 10px;
  font-size: 14px;
  color: #666;
}

.kg-stats {
  display: flex;
  gap: 20px;
  padding: 15px;
  background: #f8f9fa;
  border-radius: 8px;
  margin-bottom: 15px;
}

.kg-stat-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.kg-stat-value {
  font-weight: 600;
  color: #409eff;
}

.kg-toggle-view {
  margin-bottom: 15px;
}

.kg-legend {
  background: #f8f9fa;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 12px;
}

.kg-legend-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  font-size: 14px;
  color: #333;
  margin-bottom: 8px;
  padding-bottom: 6px;
  border-bottom: 1px solid #e0e0e0;
}

.kg-legend-title .el-icon {
  color: #409eff;
  font-size: 14px;
}

.kg-legend-items {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.kg-legend-item {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 4px 8px;
  background: white;
  border-radius: 4px;
  border: 1px solid #e0e0e0;
  transition: all 0.2s;
}

.kg-legend-item:hover {
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
  transform: translateY(-1px);
}

.kg-legend-color {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 1.5px solid #fff;
  box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.1);
  flex-shrink: 0;
}

.kg-legend-icon {
  font-size: 14px;
  color: #666;
  flex-shrink: 0;
}

.kg-legend-label {
  font-size: 12px;
  color: #333;
  font-weight: 500;
}

.kg-network {
  width: 100%;
  height: 600px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  background: #fafafa;
}

.kg-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.kg-node-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  background: #f8f9fa;
  border-radius: 8px;
  border-left: 4px solid #409eff;
  transition: all 0.2s;
}

.kg-node-item:hover {
  background: #f0f0f0;
  transform: translateX(2px);
}

.kg-node-color-indicator {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 2px solid #fff;
  box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.1);
  flex-shrink: 0;
}

.kg-node-type {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  background: #e3f2fd;
  color: #1976d2;
  border-radius: 10px;
  font-size: 12px;
  flex-shrink: 0;
}

.kg-node-label {
  flex: 1;
  font-weight: 500;
  color: #333;
}

.analysis-content {
  background: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  line-height: 1.8;
  white-space: pre-wrap;
  color: #333;
}

.empty-state {
  text-align: center;
  padding: 40px;
  color: #999;
}

.empty-icon {
  margin-bottom: 16px;
  opacity: 0.5;
  display: flex;
  justify-content: center;
  align-items: center;
}

.empty-icon .el-icon {
  color: #999;
}

h4 {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 15px;
}

h4 .el-icon {
  font-size: 20px;
  color: #409eff;
}

.el-tabs .el-tab-pane .el-icon {
  margin-right: 4px;
}

.source-meta .el-icon {
  margin-right: 4px;
  font-size: 14px;
  vertical-align: middle;
}

.kg-node-type {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.kg-node-type .el-icon {
  font-size: 14px;
}

.kg-toggle-view .el-button .el-icon {
  margin-right: 4px;
}

/* 层次结构样式 */
.hierarchy-section {
  margin-top: 20px;
}

.hierarchy-stats {
  display: flex;
  gap: 20px;
  padding: 15px;
  background: #f8f9fa;
  border-radius: 8px;
  margin-bottom: 15px;
  flex-wrap: wrap;
}

.hierarchy-stat-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.hierarchy-stat-value {
  font-weight: 600;
  color: #409eff;
}

.hierarchy-toggle-view {
  margin-bottom: 15px;
}

.hierarchy-network {
  width: 100%;
  height: 700px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  background: #fafafa;
}

.hierarchy-list {
  margin-top: 20px;
}

.hierarchy-level {
  margin-bottom: 30px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  overflow: hidden;
}

.hierarchy-level-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 12px 20px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}

.hierarchy-level-nodes {
  padding: 15px;
  background: #fafafa;
}

.hierarchy-node-item {
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 15px;
  margin-bottom: 12px;
  transition: all 0.3s;
}

.hierarchy-node-item:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.hierarchy-node-main {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.hierarchy-node-label {
  font-size: 16px;
  font-weight: 600;
  color: #333;
  flex: 1;
}

.hierarchy-node-level {
  display: inline-block;
  padding: 4px 12px;
  background: #e3f2fd;
  color: #1976d2;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.hierarchy-node-desc {
  color: #666;
  font-size: 14px;
  line-height: 1.6;
  margin-bottom: 10px;
  padding: 8px;
  background: #f8f9fa;
  border-radius: 4px;
}

.hierarchy-node-meta {
  display: flex;
  gap: 15px;
  font-size: 13px;
  color: #888;
  margin-bottom: 10px;
  padding-top: 10px;
  border-top: 1px solid #e0e0e0;
}

.hierarchy-node-meta span {
  display: flex;
  align-items: center;
  gap: 4px;
}

.hierarchy-node-sources {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed #e0e0e0;
}

.hierarchy-source-link {
  margin-bottom: 6px;
}

.hierarchy-source-link a {
  color: #409eff;
  text-decoration: none;
  font-size: 12px;
  word-break: break-all;
}

.hierarchy-source-link a:hover {
  text-decoration: underline;
}

.hierarchy-more-sources {
  color: #999;
  font-size: 12px;
  font-style: italic;
  margin-top: 6px;
}

.hierarchy-toggle-view .el-button .el-icon {
  margin-right: 4px;
}
</style>

