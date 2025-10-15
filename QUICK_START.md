# 快速开始指南

## 🚀 最快 5 分钟开始评估

### 步骤 1: 选择 LLM 提供商

你有 3 个免费选项：

#### 选项 A: Ollama（推荐 - 本地运行，无限制）

```bash
# 1. 安装 Ollama (macOS)
brew install ollama

# 2. 启动服务
ollama serve &

# 3. 下载模型
ollama pull llama3.2

# 4. 配置环境变量
cat >> .env << 'EOF'
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.2
OLLAMA_BASE_URL=http://localhost:11434
EOF
```

#### 选项 B: Groq（在线，高配额）

```bash
# 1. 注册获取 API key: https://console.groq.com/
# 2. 配置环境变量
cat >> .env << 'EOF'
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_your_api_key_here
GROQ_MODEL=llama-3.1-8b-instant
EOF
```

#### 选项 C: 继续使用 Gemini（有限制）

```bash
# 保持现有的 GOOGLE_API_KEY
cat >> .env << 'EOF'
LLM_PROVIDER=google_genai
GEMINI_MODEL=gemini-2.0-flash
EOF
```

---

### 步骤 2: 测试配置

```bash
# 测试 LLM 配置是否正确
python src/llm_config.py
```

你应该看到：
```
✅ Ollama: llama3.2 at http://localhost:11434
或
✅ Using Groq: llama-3.1-8b-instant
```

---

### 步骤 3: 运行评估

```bash
# 快速测试（2 个 patterns，4 个任务）
python run_evaluation.py --mode quick

# 完整评估（4 个 patterns，16 个任务）
python run_evaluation.py --mode full

# 单类别测试
python run_evaluation.py --mode category --category baseline
```

**延迟设置：**
- Ollama: `--delay 0`（无限制！）
- Groq: `--delay 2.0`（高配额）
- Gemini: `--delay 10.0`（低配额）

---

## 📊 查看结果

评估完成后，查看生成的报告：

```bash
# JSON 详细结果
cat reports/evaluation_results.json

# Markdown 报告
cat reports/evaluation_report.md

# CSV 对比表
cat reports/comparison_table.csv

# 可视化图表
open reports/figures/
```

---

## ❓ 故障排除

### 问题 1: "Cannot connect to Ollama"

```bash
# 确保 Ollama 正在运行
ollama serve &

# 测试连接
curl http://localhost:11434/api/tags
```

### 问题 2: "API key not found"

```bash
# 检查 .env 文件
cat .env

# 确保包含正确的配置
# 对于 Groq:
grep GROQ_API_KEY .env

# 对于 Gemini:
grep GOOGLE_API_KEY .env
```

### 问题 3: "429 Rate Limit"

```bash
# 增加延迟
python run_evaluation.py --mode quick --delay 10.0

# 或切换到 Ollama（无限制）
```

---

## 🎯 推荐配置

### 开发和调试
```bash
# 使用 Ollama，无延迟
LLM_PROVIDER=ollama
python run_evaluation.py --mode quick --delay 0
```

### 正式评估
```bash
# 使用 Groq 或 Ollama
LLM_PROVIDER=groq  # 或 ollama
python run_evaluation.py --mode full --delay 2.0
```

---

## 📚 更多文档

- 免费 LLM 设置详细指南: `FREE_LLM_SETUP.md`
- 速率限制解决方案: `RATE_LIMIT_GUIDE.md`
- 评估框架文档: `src/evaluation/README.md`

---

## ✅ 检查清单

- [ ] 选择并配置 LLM provider
- [ ] 测试配置 (`python src/llm_config.py`)
- [ ] 运行快速测试验证
- [ ] 运行完整评估
- [ ] 查看生成的报告

完成后你就能得到 4 个 patterns 的完整对比分析！🎉
