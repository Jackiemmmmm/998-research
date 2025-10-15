# 切换到 Groq（推荐）

## 为什么选择 Groq？

- ✅ **完全支持工具调用** - 与 Gemini 兼容性 100%
- ✅ **高速率限制** - 30 RPM, 14,400 RPD（比 Gemini 高 2 倍！）
- ✅ **完全免费** - 无需付费
- ✅ **速度极快** - 专用 LPU 硬件
- ✅ **高质量模型** - Llama 3.3 70B, Mixtral 8x7B

## 🚀 3 步快速切换

### 步骤 1: 获取 API Key（2 分钟）

1. 访问：https://console.groq.com/
2. 注册账户（使用 Google/GitHub 快速注册）
3. 点击 "API Keys" → "Create API Key"
4. 复制 API key（格式：`gsk_...`）

### 步骤 2: 配置环境变量（30 秒）

```bash
# 方法 A: 编辑 .env 文件
cat >> .env << 'EOF'

# Groq Configuration
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_your_actual_api_key_here
GROQ_MODEL=llama-3.1-8b-instant
EOF

# 方法 B: 直接使用命令
echo "LLM_PROVIDER=groq" >> .env
echo "GROQ_API_KEY=gsk_your_actual_key" >> .env
echo "GROQ_MODEL=llama-3.1-8b-instant" >> .env
```

**重要**: 替换 `gsk_your_actual_api_key_here` 为你的实际 API key！

### 步骤 3: 运行评估（立即）

```bash
# 测试配置
python src/llm_config.py

# 快速评估（只需 2 秒延迟）
python run_evaluation.py --mode quick --delay 2.0

# 完整评估（约 10 分钟）
python run_evaluation.py --mode full --delay 2.0
```

---

## 📊 Groq 模型选择

### 推荐模型：

```bash
# 快速且准确（推荐用于评估）
GROQ_MODEL=llama-3.1-8b-instant

# 最高质量（稍慢）
GROQ_MODEL=llama-3.3-70b-versatile

# 长上下文支持
GROQ_MODEL=mixtral-8x7b-32768
```

### 性能对比：

| 模型 | 质量 | 速度 | 推荐用途 |
|------|------|------|---------|
| llama-3.1-8b-instant | ⭐⭐⭐⭐ | ⚡⚡⚡⚡⚡ | **评估（推荐）** |
| llama-3.3-70b-versatile | ⭐⭐⭐⭐⭐ | ⚡⚡⚡ | 最终报告 |
| mixtral-8x7b-32768 | ⭐⭐⭐⭐ | ⚡⚡⚡⚡ | 长任务 |

---

## ⚙️ 完整配置示例

编辑你的 `.env` 文件：

```bash
# LLM Provider Configuration
LLM_PROVIDER=groq

# Groq Configuration
GROQ_API_KEY=gsk_your_actual_api_key_here
GROQ_MODEL=llama-3.1-8b-instant

# Tool Configuration (保持不变)
TAVILY_API_KEY=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

# Optional: LangSmith (保持不变)
LANGSMITH_PROJECT=new-agent
```

---

## 🎯 速率限制建议

### Groq 配额：
- **每分钟请求数 (RPM)**: 30
- **每天请求数 (RPD)**: 14,400

### 推荐延迟设置：

```bash
# 快速测试（4 任务 × 2 patterns = 8 请求）
python run_evaluation.py --mode quick --delay 2.0

# 完整评估（16 任务 × 4 patterns × 2 = 128 请求）
python run_evaluation.py --mode full --delay 2.0

# 如果遇到限制，增加延迟
python run_evaluation.py --mode full --delay 3.0
```

**计算**：
- 延迟 2.0s = 每分钟最多 30 个请求 ✅
- 延迟 3.0s = 每分钟最多 20 个请求（更安全）

---

## ✅ 验证配置

```bash
# 1. 测试 LLM 配置
python src/llm_config.py

# 期望输出：
# ✅ Using Groq: llama-3.1-8b-instant
# Setup check: {'status': 'ok', ...}

# 2. 运行快速测试
python run_evaluation.py --mode quick --delay 2.0

# 3. 查看结果
cat reports/evaluation_report.md
```

---

## 🆚 Groq vs Ollama vs Gemini

| 特性 | Groq | Ollama | Gemini |
|------|------|--------|--------|
| 工具调用 | ✅ 完美支持 | ❌ 不支持 | ✅ 支持 |
| 速率限制 | 30 RPM | 无限制 | 15 RPM |
| 每日配额 | 14,400 RPD | 无限制 | 1,500 RPD |
| 速度 | ⚡⚡⚡⚡⚡ | ⚡⚡⚡ | ⚡⚡⚡ |
| 质量 | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| 成本 | 免费 | 免费 | 免费 |
| 网络要求 | 需要 | 不需要 | 需要 |
| **评估适用性** | **✅ 最佳** | ❌ 不适合 | ⚠️ 容易达限 |

---

## ❓ 常见问题

### Q: Groq 完全免费吗？
**A**: 是的！目前 Groq 的免费层已经足够进行开发和评估。

### Q: API key 安全吗？
**A**: 将 API key 保存在 `.env` 文件中，并确保 `.env` 在 `.gitignore` 中。

### Q: 如果达到速率限制怎么办？
**A**:
```bash
# 增加延迟到 5 秒
python run_evaluation.py --mode full --delay 5.0

# 或分批运行
python run_evaluation.py --mode category --category baseline --delay 3.0
```

### Q: 可以切换回 Ollama 吗？
**A**: 可以！只需修改 `.env`:
```bash
LLM_PROVIDER=ollama
```

---

## 🎉 总结

**推荐操作流程**：

1. ✅ 注册 Groq（2 分钟）
2. ✅ 配置 `.env`（30 秒）
3. ✅ 运行评估（10 分钟）
4. ✅ 查看结果

**Groq 是目前评估的最佳选择**：
- 完全支持工具调用
- 配额是 Gemini 的 2 倍
- 速度极快
- 完全免费

立即开始：https://console.groq.com/ 🚀
