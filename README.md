# 实时语音转写系统后端

这是一个基于FastAPI和Whisper的实时语音转写系统后端，能够实现低延迟、高精度的语音转写，并支持多种语言。

## 功能特点

- 实时语音转写与处理
- 支持多种语言的识别
- 文本智能优化（使用Gemini API）
- 实时翻译功能
- 自动语音检测
- WebSocket低延迟通信
- RNNoise降噪处理

## 技术栈

- FastAPI
- WebSocket
- OpenAI Whisper
- Google Gemini API
- Python 3.9+

## 安装与使用

1. 克隆仓库
```bash
git clone https://github.com/Terryzhang-jp/realtime_transcirbe_backend.git
cd realtime_transcirbe_backend
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 配置环境变量
```bash
cp .env.example .env
# 编辑.env文件，填入必要的API密钥
```

4. 运行服务
```bash
./run.sh
# 或者
python -m uvicorn app.main:app --reload
```

## API接口

- WebSocket `/ws/transcribe`：用于实时音频转写
- HTTP GET `/test/ws-status`：检查WebSocket连接状态

## 许可证

MIT
