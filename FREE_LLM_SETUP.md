# 免费 LLM 配置指南

本指南帮助你配置免费的大模型替代方案，避免 API 速率限制。

---

## 方案 1: Ollama（最推荐，本地运行）

### 优势
- ✅ **完全免费，无速率限制**
- ✅ 本地运行，隐私保护
- ✅ 不需要 API key
- ✅ 支持多种开源模型

### 安装步骤

#### 1. 下载并安装 Ollama

**macOS:**
```bash
# 使用 Homebrew
brew install ollama

# 或从官网下载：https://ollama.com/download
```

**Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Windows:**
下载安装包：https://ollama.com/download

#### 2. 启动 Ollama 服务

```bash
ollama serve
```

保持这个终端运行（或后台运行）。

#### 3. 下载模型

在另一个终端中：

```bash
# 推荐模型（按大小和质量排序）

# Llama 3.2 (3B) - 快速，适合测试
ollama pull llama3.2

# Llama 3.1 (8B) - 平衡性能
ollama pull llama3.1

# Qwen 2.5 (7B) - 优秀的多语言支持
ollama pull qwen2.5

# Mistral (7B) - 高质量开源模型
ollama pull mistral
```

#### 4. 测试 Ollama

```bash
ollama run llama3.2 "What is 2+2?"
```

#### 5. 配置项目使用 Ollama

编辑 `.env` 文件，添加：
```bash
# Ollama 配置
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.2
OLLAMA_BASE_URL=http://localhost:11434
```

---

## 方案 2: Groq（在线免费，速率限制宽松）

### 优势
- ✅ 免费配额高：**30 RPM, 14,400 RPD**
- ✅ 速度极快（专用 LPU 硬件）
- ✅ 支持主流开源模型

### 配置步骤

#### 1. 获取 API Key

1. 访问：https://console.groq.com/
2. 注册账户（免费）
3. 创建 API Key

#### 2. 配置环境变量

编辑 `.env` 文件，添加：
```bash
# Groq 配置
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_your_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

**推荐的 Groq 模型：**
- `llama-3.3-70b-versatile` - 最新，质量高
- `llama-3.1-8b-instant` - 快速，适合测试
- `mixtral-8x7b-32768` - 长上下文

---

## 方案 3: Cerebras（在线免费）

### 优势
- ✅ 完全免费
- ✅ 速度快

### 配置步骤

#### 1. 获取 API Key

1. 访问：https://inference.cerebras.ai/
2. 注册账户
3. 获取 API Key

#### 2. 配置环境变量

编辑 `.env` 文件：
```bash
# Cerebras 配置
LLM_PROVIDER=cerebras
CEREBRAS_API_KEY=your_api_key_here
CEREBRAS_MODEL=llama3.1-8b
```

---

## 使用配置

### 方式 1: 通过环境变量（推荐）

编辑 `.env` 文件，设置默认 provider：

```bash
# 选择一个 provider
LLM_PROVIDER=ollama  # 或 groq, cerebras, google_genai

# Ollama 配置（如果使用 Ollama）
OLLAMA_MODEL=llama3.2
OLLAMA_BASE_URL=http://localhost:11434

# Groq 配置（如果使用 Groq）
GROQ_API_KEY=your_key_here
GROQ_MODEL=llama-3.1-8b-instant

# Cerebras 配置（如果使用 Cerebras）
CEREBRAS_API_KEY=your_key_here
CEREBRAS_MODEL=llama3.1-8b

# Google Gemini 配置（原来的）
GOOGLE_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.0-flash
```

### 方式 2: 命令行参数

```bash
# 使用 Ollama
python run_evaluation.py --mode quick --provider ollama

# 使用 Groq
python run_evaluation.py --mode quick --provider groq

# 使用 Cerebras
python run_evaluation.py --mode quick --provider cerebras
```

---

## 性能对比

| Provider | 速度 | 配额限制 | 需要安装 | 隐私 | 推荐指数 |
|----------|------|---------|---------|------|---------|
| **Ollama** | 快 (取决于硬件) | 无限制 | ✓ | 完全本地 | ⭐⭐⭐⭐⭐ |
| **Groq** | 极快 | 30 RPM, 14400 RPD | ✗ | API 调用 | ⭐⭐⭐⭐ |
| **Cerebras** | 快 | 较高 | ✗ | API 调用 | ⭐⭐⭐ |
| **Gemini** | 中 | 15 RPM, 1500 RPD | ✗ | API 调用 | ⭐⭐ |

---

## 推荐使用策略

### 开发和调试阶段：
```bash
# 使用 Ollama - 无限制，快速迭代
python run_evaluation.py --mode quick --provider ollama --delay 0
```

### 正式评估阶段：
```bash
# 使用 Groq - 高质量，速度快，配额高
python run_evaluation.py --mode full --provider groq --delay 2.0
```

### 需要本地隐私：
```bash
# 使用 Ollama - 数据不离开本地
python run_evaluation.py --mode full --provider ollama --delay 0
```

---

## 故障排除

### Ollama 相关

**问题：连接失败**
```bash
# 确保 Ollama 服务正在运行
ollama serve

# 测试连接
curl http://localhost:11434/api/tags
```

**问题：模型未找到**
```bash
# 列出已安装的模型
ollama list

# 下载需要的模型
ollama pull llama3.2
```

### Groq 相关

**问题：API Key 无效**
- 检查 `.env` 文件中的 `GROQ_API_KEY`
- 确认在 Groq Console 中 API Key 已启用

**问题：速率限制**
- Groq 限制：30 RPM, 14400 RPD
- 使用 `--delay 2.0` 即可（每分钟最多 30 个请求）

---

## 快速启动命令

### Ollama (推荐用于开发)
```bash
# 1. 启动 Ollama
ollama serve &

# 2. 下载模型
ollama pull llama3.2

# 3. 运行评估（无延迟！）
python run_evaluation.py --mode quick --provider ollama --delay 0
```

### Groq (推荐用于正式评估)
```bash
# 1. 配置 .env
echo "GROQ_API_KEY=your_key_here" >> .env

# 2. 运行评估
python run_evaluation.py --mode full --provider groq --delay 2.0
```

---

## 推荐配置组合

**方案 A: 纯本地（最推荐）**
```bash
# 使用 Ollama，完全免费无限制
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.2
OLLAMA_BASE_URL=http://localhost:11434
```

**方案 B: 混合使用**
```bash
# 开发时用 Ollama，正式评估用 Groq
# 通过命令行参数切换
python run_evaluation.py --mode quick --provider ollama    # 开发
python run_evaluation.py --mode full --provider groq       # 正式
```

---

## 更多资源

- Ollama 官网: https://ollama.com/
- Groq 官网: https://groq.com/
- Cerebras 官网: https://cerebras.ai/
- Ollama 模型库: https://ollama.com/library
