<template>
  <div class="app-container">
    <h1>智能招聘助手</h1>
    
    <div class="input-section">
      <textarea 
        v-model="jobDescription" 
        placeholder="请输入岗位要求和招聘信息..."
        rows="5"
        class="input-textarea"
      ></textarea>  
      
      <div class="input-actions">
        <button 
          class="btn-submit"
          @click="submitRequest" 
          :disabled="isSubmitting"
        >
          {{ isSubmitting ? '处理中...' : '开始招聘' }}
        </button>
        
        <div class="file-upload-section">
          <label class="upload-label">
            <input 
              type="file" 
              multiple 
              accept=".pdf,.doc,.docx" 
              @change="handleFileUpload"
              :disabled="isSubmitting"
            />
            <span class="upload-button">上传简历</span>
          </label>
          
          <div class="uploaded-files" v-if="uploadedFiles.length > 0">
            <span class="file-count">已上传 {{ uploadedFiles.length }} 份简历</span>
            <ul class="file-list">
              <li v-for="(file, index) in uploadedFiles" :key="index" class="file-item">
                {{ file.name }}
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>

    <div class="progress-section" v-if="steps.length > 0" id="steps-container">
      <div 
        v-for="(step, index) in steps" 
        :key="index" 
        class="step-card"
        :class="{ 'error': step.isError, 'processing': step.isProcessing, 'show': step.show }"
      >
        <div class="step-header">
          <div class="step-title">
            {{ step.title }}
            <!-- 加载动画：当 isProcessing 为 true 时显示旋转圈圈 -->
            <span class="loading-spinner" v-if="step.isProcessing">⟳</span>
          </div>
          <div class="step-time">{{ new Date(step.timestamp).toLocaleTimeString() }}</div>
        </div>
        
        <!-- 思考部分 - 可展开/收缩 -->
        <div class="thinking-section" v-if="step.thinking">
          <div class="thinking-header" @click="step.showThinking = !step.showThinking">
            <span class="thinking-title">思考过程</span>
            <span class="toggle-icon" :class="{ 'expanded': step.showThinking }">
              ▼
            </span>
          </div>
          <div class="thinking-content" v-show="step.showThinking">
            {{ step.thinking }}
          </div>
        </div>
        
        <!-- 响应内容部分 -->
        <div class="step-content markdown-body" v-if="step.content" v-html="parseMarkdown(step.content)"></div>
      </div>
    </div>

    <!-- 最终报告部分 -->
    <div class="report-section" v-if="reportContent">
      <h2>招聘结果报告</h2>
      <div class="report-content" v-html="parseMarkdown(reportContent)"></div>
      <button @click="copyReport">复制报告</button>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onBeforeUnmount } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const jobDescription = ref('')
const isSubmitting = ref(false)
const steps = ref([])
const reportContent = ref('')
const eventSource = ref(null)
const uploadedFiles = ref([])

const currentActiveStep = ref(null); // 使用 ref 确保响应式
const activeSubSteps = ref(new Map()); // 追踪writing步骤的活跃子块（key为section_id）

// WebSocket连接
let wsConnection = null;

// Markdown解析方法，增加安全过滤
const parseMarkdown = (content) => {
  if (!content) return '';
  // 1. 先用 marked 将 Markdown 解析为 HTML
  const html = marked.parse(content);
  // 2. 用 DOMPurify 过滤危险 HTML 内容（防止 XSS）
  return DOMPurify.sanitize(html);
};

// 处理文件上传
const handleFileUpload = (event) => {
  const files = Array.from(event.target.files);
  uploadedFiles.value = files;
  console.log(`选择了 ${files.length} 份简历`);
};

// 提交请求
const submitRequest = async () => {
  if (!jobDescription.value.trim()) {
    alert('请输入岗位要求！');
    return;
  }

  if (uploadedFiles.value.length === 0) {
    alert('请至少上传一份简历！');
    return;
  }

  isSubmitting.value = true;
  steps.value = [];
  reportContent.value = '';

  // 创建任务ID
  const taskId = Date.now().toString();

  // 上传简历文件
  const formData = new FormData();
  uploadedFiles.value.forEach((file) => {
    formData.append('files', file);
  });

  try {
    const uploadResponse = await fetch('/api/upload-resumes', {
      method: 'POST',
      body: formData,
    });

    if (!uploadResponse.ok) {
      throw new Error(`上传失败: ${uploadResponse.statusText}`);
    }

    const uploadResult = await uploadResponse.json();
    console.log('上传结果:', uploadResult);

    // 启动招聘流程
    const startResponse = await fetch('/api/start-recruitment-with-files', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        job_description: jobDescription.value,
        resume_paths: uploadResult.file_paths,
      }),
    });

    if (!startResponse.ok) {
      throw new Error(`启动招聘流程失败: ${startResponse.statusText}`);
    }

    const startResult = await startResponse.json();
    console.log('启动结果:', startResult);

    // 连接WebSocket获取实时状态
    const wsUrl = `ws://localhost:8000/ws/${taskId}`;
    wsConnection = new WebSocket(wsUrl);

    wsConnection.onmessage = (event) => {
      try {
        const backData = JSON.parse(event.data);
        console.log('Received data:', backData);
        handleBackendData(backData); // 统一处理后端数据
      } catch (error) {
        console.error('Error processing WebSocket message:', error);
      }
    };

    wsConnection.onerror = (error) => {
      console.error('WebSocket connection error:', error);
      addStep('错误', '连接服务器失败', true);
      finishProcessing();
    };

    wsConnection.onclose = () => {
      console.log('WebSocket connection closed');
      finishProcessing();
    };

  } catch (error) {
    console.error('提交请求失败:', error);
    alert(`提交请求失败: ${error.message}`);
    finishProcessing();
  }
};

// 统一处理后端数据
const handleBackendData = (backData) => {
  const { step, state, data } = backData;
  const handlers = {
    extracting: () => handleExtracting(step, data),
    profiling: () => handleProfiling(step, data),
    reasoning: () => handleReasoning(step, data),
    validating: () => handleValidating(step, data),
    completed: () => handleComplete(step, data),
    error: () => handleError(step, data),
    finished: () => handleFinish()
  };

  if (handlers[state]) {
    handlers[state]();
  } else {
    console.warn('Unknown state:', state, 'in step:', step);
  }
};

// 处理「提取」状态
const handleExtracting = (step, data) => {
  if (!currentActiveStep.value || currentActiveStep.value.step !== step) {
    // 创建新步骤
    const stepElement = {
      step,
      title: '简历解析中',
      thinking: data?.thinking || '',
      content: data?.content || '',
      isProcessing: true,
      isError: false,
      timestamp: new Date().toISOString(),
      show: false,
      showThinking: true,
    };
    steps.value.push(stepElement);
    currentActiveStep.value = stepElement;

    nextTick(() => {
      stepElement.show = true;
      autoScroll();
    });
  } else {
    // 更新现有步骤
    currentActiveStep.value.isProcessing = true;
    currentActiveStep.value.title = '简历解析中';
    if (data) {
      currentActiveStep.value.content += data;
    }
    autoScroll();
  }
};

// 处理「画像构建」状态
const handleProfiling = (step, data) => {
  if (!currentActiveStep.value || currentActiveStep.value.step !== step) {
    // 创建新步骤
    const stepElement = {
      step,
      title: '候选人画像构建中',
      thinking: data?.thinking || '',
      content: data?.content || '',
      isProcessing: true,
      isError: false,
      timestamp: new Date().toISOString(),
      show: false,
      showThinking: true,
    };
    steps.value.push(stepElement);
    currentActiveStep.value = stepElement;

    nextTick(() => {
      stepElement.show = true;
      autoScroll();
    });
  } else {
    // 更新现有步骤
    currentActiveStep.value.isProcessing = true;
    currentActiveStep.value.title = '候选人画像构建中';
    if (data) {
      currentActiveStep.value.content += data;
    }
    autoScroll();
  }
};

// 处理「推理评估」状态
const handleReasoning = (step, data) => {
  if (!currentActiveStep.value || currentActiveStep.value.step !== step) {
    // 创建新步骤
    const stepElement = {
      step,
      title: '候选人推理评估中',
      thinking: data?.thinking || '',
      content: data?.content || '',
      isProcessing: true,
      isError: false,
      timestamp: new Date().toISOString(),
      show: false,
      showThinking: true,
    };
    steps.value.push(stepElement);
    currentActiveStep.value = stepElement;

    nextTick(() => {
      stepElement.show = true;
      autoScroll();
    });
  } else {
    // 更新现有步骤
    currentActiveStep.value.isProcessing = true;
    currentActiveStep.value.title = '候选人推理评估中';
    if (data) {
      currentActiveStep.value.content += data;
    }
    autoScroll();
  }
};

// 处理「质量校验」状态
const handleValidating = (step, data) => {
  if (!currentActiveStep.value || currentActiveStep.value.step !== step) {
    // 创建新步骤
    const stepElement = {
      step,
      title: '评估结果校验中',
      thinking: data?.thinking || '',
      content: data?.content || '',
      isProcessing: true,
      isError: false,
      timestamp: new Date().toISOString(),
      show: false,
      showThinking: true,
    };
    steps.value.push(stepElement);
    currentActiveStep.value = stepElement;

    nextTick(() => {
      stepElement.show = true;
      autoScroll();
    });
  } else {
    // 更新现有步骤
    currentActiveStep.value.isProcessing = true;
    currentActiveStep.value.title = '评估结果校验中';
    if (data) {
      currentActiveStep.value.content += data;
    }
    autoScroll();
  }
};

// 处理「阶段完成」状态
const handleComplete = (step, data) => {
  if (!currentActiveStep.value || currentActiveStep.value.step !== step) {
    console.warn(`No active step found for completed step: ${step}`);
    return;
  }
  // 更新步骤内容（关闭加载动画，显示结果）
  currentActiveStep.value.isProcessing = false;
  currentActiveStep.value.title = `${getStepName(step)}完成`;
  if (data) {
    currentActiveStep.value.content += data;
  }
  currentActiveStep.value = null; // 清除活跃状态，等待下一阶段
  autoScroll();
};

// 处理「阶段出错」状态
const handleError = (step, data) => {
  if (!currentActiveStep.value || currentActiveStep.value.step !== step) {
    console.warn(`No active step found for error step: ${step}`);
    return;
  }
  // 更新步骤内容（关闭加载动画，显示错误信息）
  currentActiveStep.value.isProcessing = false;
  currentActiveStep.value.isError = true;
  currentActiveStep.value.title = `${getStepName(step)}出现错误`;
  
  // 处理错误信息
  if (data) {
    currentActiveStep.value.content += data;
  }
  
  currentActiveStep.value = null; // 清除活跃状态
  autoScroll();
};

// 处理「所有阶段完成」状态
const handleFinish = () => {
  // 新增最终完成步骤
  const finishStep = {
    step: 'finish',
    title: '招聘流程完成',
    content: '所有候选人已评估完毕',
    thinking: '',
    isProcessing: false,
    isError: false,
    timestamp: new Date().toISOString(),
    show: false,
    showThinking: false
  };
  steps.value.push(finishStep);
  nextTick(() => {
    finishStep.show = true;
    autoScroll();
    finishProcessing(); // 关闭连接
  });
};

// 辅助函数：获取阶段中文名称
const getStepName = (step) => {
  const stepNames = {
    extracting: '简历解析',
    profiling: '画像构建',
    reasoning: '推理评估',
    validating: '质量校验',
    completed: '完成',
    finished: '结束'
  };
  return stepNames[step] || step;
};

// 结束流程
const finishProcessing = () => {
  isSubmitting.value = false;
  if (wsConnection) {
    wsConnection.close();
  }
  activeSubSteps.value.clear(); // 清理活跃子块Map
};

// 自动滚动到最新步骤
const autoScroll = () => {
  // 实现滚动逻辑（例如滚动到容器底部）
  const container = document.getElementById('steps-container');
  if (container) {
    container.scrollTop = container.scrollHeight;
  }
};

const copyReport = () => {
  if (!reportContent.value) return
  navigator.clipboard.writeText(reportContent.value)
}
</script>

<style scoped>
.app-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  color: #333;
  width: 100%;
  box-sizing: border-box;
}

h1 {
  text-align: center;
  color: #2c3e50;
  margin-bottom: 30px;
  font-weight: 600;
  font-size: clamp(24px, 3vw, 32px);
}

.input-section {
  margin-bottom: 20px;
  background: #f8f9fa;
  padding: clamp(15px, 3vw, 25px);
  border-radius: 10px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
  max-width: 100%;
  width: 100%;
  box-sizing: border-box;
}

.input-textarea {
  width: 100%;
  padding: clamp(12px, 2vw, 18px);
  margin-bottom: clamp(10px, 2vw, 20px);
  border: 1px solid #e1e5e9;
  border-radius: 8px;
  font-size: clamp(14px, 1.5vw, 16px);
  line-height: 1.5;
  transition: border-color 0.3s, box-shadow 0.3s;
  resize: vertical;
  font-family: inherit;
  box-sizing: border-box;
  min-height: 120px;
  max-height: 300px;
}

.input-textarea:focus {
  outline: none;
  border-color: #3498db;
  box-shadow: 0 0 0 3px rgba(52, 152, 219, 0.15);
}

.input-textarea::placeholder {
  color: #adb5bd;
}

.input-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: clamp(10px, 2vw, 20px);
  flex-wrap: wrap;
}

.btn-submit {
  padding: clamp(10px, 1.5vw, 14px) clamp(20px, 4vw, 30px);
  background: #3498db;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: clamp(14px, 1.5vw, 16px);
  font-weight: 500;
  transition: background 0.3s, transform 0.2s;
  flex-shrink: 0;
  min-width: fit-content;
}

.btn-submit:hover:not(:disabled) {
  background: #2980b9;
  transform: translateY(-1px);
}

.btn-submit:active:not(:disabled) {
  transform: translateY(0);
}

.btn-submit:disabled {
  background: #bdc3c7;
  cursor: not-allowed;
  transform: none;
}

.file-upload-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
  align-items: flex-start;
  flex-shrink: 0;
}

.upload-label {
  display: block;
  position: relative;
  cursor: pointer;
}

.upload-label input[type="file"] {
  position: absolute;
  opacity: 0;
  width: 100%;
  height: 100%;
  cursor: pointer;
}

.upload-button {
  display: inline-block;
  padding: 10px 16px;
  background: #e3f2fd;
  color: #3498db;
  border: 2px solid #3498db;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
  text-align: center;
}

.upload-button:hover {
  background: #3498db;
  color: white;
  transform: translateY(-1px);
}

.uploaded-files {
  margin-top: 10px;
  width: 100%;
}

.file-count {
  font-size: 14px;
  color: #7f8c8d;
  font-weight: 500;
}

.file-list {
  list-style: none;
  padding: 0;
  margin: 5px 0 0 0;
  max-height: 100px;
  overflow-y: auto;
}

.file-item {
  padding: 5px 0;
  font-size: 13px;
  color: #555;
  border-bottom: 1px solid #eee;
}

.file-item:last-child {
  border-bottom: none;
}

@media (max-width: 1200px) {
  .input-section {
    padding: 18px;
  }
  
  .input-textarea {
    padding: 14px;
    font-size: 15px;
  }
}

@media (max-width: 992px) {
  .input-section {
    padding: 16px;
  }
  
  .input-textarea {
    padding: 13px;
    font-size: 15px;
    min-height: 100px;
  }
}

@media (max-width: 768px) {
  .app-container {
    padding: 15px;
    max-width: 100%;
  }
  
  .input-section {
    padding: 15px;
    border-radius: 8px;
  }
  
  .input-actions {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }
  
  .btn-submit {
    width: 100%;
    padding: 12px 20px;
    font-size: 15px;
  }
  
  .file-upload-section {
    width: 100%;
    align-items: stretch;
  }
  
  .input-textarea {
    padding: 12px;
    font-size: 14px;
    min-height: 80px;
  }
  
  .progress-section,
  .report-section {
    max-width: 100%;
  }
}

@media (max-width: 480px) {
  .app-container {
    padding: 10px;
  }
  
  h1 {
    font-size: 24px;
    margin-bottom: 20px;
  }
  
  .input-section {
    padding: 12px;
  }
  
  .input-textarea {
    padding: 10px;
    font-size: 14px;
    min-height: 70px;
    max-height: 200px;
  }
  
  .btn-submit {
    padding: 10px 16px;
    font-size: 14px;
  }
  
  .upload-button {
    padding: 8px 12px;
    font-size: 12px;
  }
}

@media (min-width: 1400px) {
  .app-container {
    max-width: 1000px;
  }
}

.progress-section {
  margin: 0 auto 20px;
  max-width: 1000px;
  max-height: 500px;
  overflow-y: auto;
  padding-right: 5px;
}

.step-card {
  transition: all 0.3s ease;
  opacity: 0;
  transform: translateY(20px);
  border-radius: 10px;
  padding: 0;
  margin-bottom: 20px;
  background: white;
  box-shadow: 0 3px 15px rgba(0, 0, 0, 0.08);
  overflow: hidden;
}

.step-card.show {
  opacity: 1;
  transform: translateY(0);
}

.step-card.error {
  border-left: 5px solid #e74c3c;
}

.step-card.processing {
  border-left: 5px solid #3498db;
}

.step-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  background: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
}

.step-title {
  font-weight: 600;
  font-size: 16px;
  color: #2c3e50;
  display: flex;
  align-items: center;
}

.loading-spinner {
  display: inline-block;
  margin-left: 8px;
  animation: spin 1s linear infinite;
  color: #3498db;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.step-time {
  font-size: 14px;
  color: #7f8c8d;
}

.thinking-section {
  border-bottom: 1px solid #e9ecef;
}

.thinking-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  cursor: pointer;
  background: #f1f8ff;
  transition: background 0.2s;
}

.thinking-header:hover {
  background: #e3f2fd;
}

.thinking-title {
  font-weight: 500;
  color: #3498db;
}

.toggle-icon {
  transition: transform 0.3s;
  color: #7f8c8d;
}

.toggle-icon.expanded {
  transform: rotate(180deg);
}

.thinking-content {
  padding: 15px 20px;
  background: #f8fafc;
  color: #4a5568;
  font-size: 14px;
  line-height: 1.5;
  white-space: pre-wrap;
  border-top: 1px solid #e2e8f0;
}

.step-content {
  padding: 20px;
  white-space: pre-wrap;
  line-height: 1.6;
  color: #2d3748;
}

.report-section {
  margin: 30px auto;
  max-width: 1000px;
  background: #f8f9fa;
  padding: 20px;
  border-radius: 10px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}

.report-section h2 {
  margin-top: 0;
  color: #2c3e50;
  font-weight: 600;
}

.report-content {
  background: white;
  padding: 15px;
  border-radius: 8px;
  margin-bottom: 15px;
  line-height: 1.6;
  white-space: pre-wrap;
}

.report-section button {
  background: #27ae60;
  color: white;
  border: none;
  padding: 12px 25px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 16px;
  font-weight: 500;
  transition: background 0.3s;
}

.report-section button:hover {
  background: #219653;
}

/* 滚动条样式 */
.progress-section::-webkit-scrollbar {
  width: 6px;
}

.progress-section::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 10px;
}

.progress-section::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 10px;
}

.progress-section::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

/* 引入Markdown样式（可根据需要调整） */
.markdown-body {
  box-sizing: border-box;
  min-width: 200px;
  max-width: 980px;
  margin: 0 auto;
  padding: 16px;
  line-height: 1.5;
  word-break: break-word;
}

.markdown-body h1,
.markdown-body h2,
.markdown-body h3 {
  margin-top: 24px;
  margin-bottom: 16px;
  font-weight: 600;
  line-height: 1.25;
}

.markdown-body p {
  margin-top: 0;
  margin-bottom: 16px;
}

.markdown-body ul,
.markdown-body ol {
  padding-left: 2em;
  margin-top: 0;
  margin-bottom: 16px;
}

.markdown-body strong {
  font-weight: 600;
}

.markdown-body em {
  font-style: italic;
}

.markdown-body a {
  color: #0366d6;
  text-decoration: none;
}

.markdown-body a:hover {
  text-decoration: underline;
}

.markdown-body code {
  padding: 0.2em 0.4em;
  margin: 0;
  font-size: 85%;
  background-color: rgba(27, 31, 35, 0.05);
  border-radius: 3px;
}
</style>
