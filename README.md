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

3. 安装FFmpeg（用于Silero VAD）
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get update
sudo apt-get install ffmpeg

# CentOS/RHEL
sudo yum install ffmpeg
```

4. 配置环境变量
```bash
cp .env.example .env
# 编辑.env文件，填入必要的API密钥
```

5. 运行服务
```bash
./run.sh
# 或者
python -m uvicorn app.main:app --reload
```

## 可能的问题与解决方案

### FFmpeg相关错误

如果您在启动时看到与FFmpeg相关的错误（例如找不到libavcodec.XX.dylib），这是因为Silero VAD依赖于FFmpeg。虽然系统会自动回退到WebRTC VAD，但如果您希望使用更准确的Silero VAD，请确保正确安装FFmpeg。

### WebSocket连接问题

如果WebSocket连接频繁断开，请检查网络稳定性，并确保客户端正确处理重连逻辑。

## API接口

- WebSocket `/ws/transcribe`：用于实时音频转写
- HTTP GET `/test/ws-status`：检查WebSocket连接状态

## 许可证

MIT
