from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from typing import Dict, List, Optional, Any
import logging
import asyncio
import uuid
import json
import traceback
import time
from app.services.transcription import TranscriptionService
from app.services.text_processor import text_processor
from app import config

# 创建路由器
router = APIRouter()

# 创建转写服务实例
transcription_service = TranscriptionService()

# 维护活跃的WebSocket连接
active_connections: Dict[str, WebSocket] = {}
# 记录音频统计
audio_stats: Dict[str, Dict[str, Any]] = {}

async def get_transcription_service() -> TranscriptionService:
    """依赖注入：获取转写服务实例"""
    return transcription_service

@router.get("/ws/status", response_model=Dict[str, Any])
async def get_websocket_status():
    """获取当前所有WebSocket连接状态和配置信息"""
    logger = logging.getLogger("API:ws-status")
    
    # 收集活跃连接信息
    connections_info = []
    for client_id, websocket in active_connections.items():
        # 获取客户端配置
        config = transcription_service.get_client_config(client_id)
        
        # 获取音频统计（如果有）
        stats = {}
        if client_id in audio_stats:
            stats = audio_stats[client_id]
        
        # 合并信息
        conn_info = {
            "client_id": client_id,
            "connected": True,
            "config": config,
            "audio_stats": {
                "total_chunks": stats.get("total_chunks", 0),
                "total_bytes": stats.get("total_bytes", 0),
                "first_chunk_time": stats.get("first_chunk_time"),
                "last_chunk_time": stats.get("last_chunk_time"),
            }
        }
        connections_info.append(conn_info)
    
    # 获取所有注册客户端（可能有些已断开连接但仍在服务中）
    registered_clients = []
    for client_id, client in transcription_service.clients.items():
        if client_id not in [c["client_id"] for c in connections_info]:
            config = transcription_service.get_client_config(client_id)
            registered_clients.append({
                "client_id": client_id,
                "connected": False,
                "config": config,
                "disconnected": True
            })
    
    logger.info(f"当前活跃连接: {len(connections_info)}")
    logger.info(f"已注册但未连接的客户端: {len(registered_clients)}")
    
    # 返回结果
    return {
        "timestamp": time.time(),
        "active_connections": len(connections_info),
        "registered_clients": len(transcription_service.clients),
        "connections": connections_info + registered_clients
    }

@router.get("/ws/client/{client_id}/config")
async def get_client_config(client_id: str):
    """获取特定客户端的配置信息（用于调试）"""
    logger = logging.getLogger(f"API:client-config:{client_id}")
    
    if client_id not in transcription_service.clients:
        return {"error": "客户端不存在", "client_id": client_id}
    
    # 获取客户端配置
    config = transcription_service.get_client_config(client_id)
    
    # 获取处理器的原始配置
    client = transcription_service.clients[client_id]
    processor = client.get('processor')
    
    # 增加处理器信息，更全面地了解语言设置
    processor_info = {
        "language": getattr(processor, "language", "unknown"),
        "model_type": getattr(processor, "model_type", "unknown"),
        "device": getattr(processor, "device", "unknown"),
        "running": getattr(processor, "running", False),
        "initial_prompt": getattr(processor, "initial_prompt", ""),
    }
    
    logger.info(f"获取客户端 {client_id} 配置")
    logger.info(f"客户端配置: {config}")
    logger.info(f"处理器配置: {processor_info}")
    
    return {
        "client_id": client_id,
        "config": config,
        "processor": processor_info,
        "connected": client_id in active_connections,
        "timestamp": time.time()
    }

@router.post("/ws/client/{client_id}/config")
async def update_client_config(client_id: str, config: Dict[str, Any]):
    """更新特定客户端的配置（用于调试）"""
    logger = logging.getLogger(f"API:update-config:{client_id}")
    logger.info(f"手动更新客户端 {client_id} 配置: {config}")
    
    if client_id not in transcription_service.clients:
        return {"error": "客户端不存在", "client_id": client_id}
    
    # 语言和模型检查
    language = config.get("language")
    # 同时支持model和model_type字段
    model_type = config.get("model_type") or config.get("model")
    target_language = config.get("target_language", "en")
    
    # 记录详细的字段信息
    logger.info(f"接收到的配置字段: language={language}, model_type={model_type}, target_language={target_language}")
    
    if language and language not in config.AVAILABLE_LANGUAGES:
        logger.error(f"配置中的语言 {language} 不在支持的语言列表中")
        return {"success": False, "client_id": client_id, "message": f"不支持的语言: {language}"}
    
    if model_type and model_type not in config.AVAILABLE_MODELS:
        logger.error(f"配置中的模型 {model_type} 不在支持的模型列表中")
        return {"success": False, "client_id": client_id, "message": f"不支持的模型: {model_type}"}
    
    # 获取当前配置用于比较
    current_config = transcription_service.get_client_config(client_id)
    logger.info(f"当前配置: {current_config}")
    
    # 传递配置
    try:
        # 记录详细的操作过程
        logger.info(f"开始更新配置...")
        
        success = await transcription_service.update_client_config(
            client_id=client_id,
            language=language,
            model_type=model_type,
            target_language=target_language
        )
        
        if success:
            # 获取更新后的配置
            new_config = transcription_service.get_client_config(client_id)
            logger.info(f"客户端 {client_id} 配置更新成功")
            logger.info(f"新配置: {new_config}")
            return {"success": True, "client_id": client_id, "message": "配置已成功更新", "config": new_config}
        else:
            logger.error(f"客户端 {client_id} 配置更新失败")
            # 获取更详细的错误原因
            client = transcription_service.clients[client_id]
            processor_info = None
            if 'processor' in client:
                processor = client['processor']
                processor_info = {
                    "language": getattr(processor, "language", "unknown"),
                    "model_type": getattr(processor, "model_type", "unknown"),
                    "running": getattr(processor, "running", False)
                }
            
            return {
                "success": False, 
                "client_id": client_id, 
                "message": "配置更新失败",
                "current_config": current_config,
                "processor_info": processor_info
            }
    except Exception as e:
        logger.error(f"更新过程发生异常: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "success": False, 
            "client_id": client_id, 
            "message": f"配置更新过程中发生错误: {str(e)}",
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc()
        }

@router.websocket("/ws/transcribe/{client_id}")
async def websocket_transcribe(
    websocket: WebSocket, 
    client_id: Optional[str] = None,
    service: TranscriptionService = Depends(get_transcription_service)
):
    """WebSocket端点，处理音频流和返回转写结果"""
    # 如果没有提供client_id，生成一个
    if not client_id or client_id == "undefined":
        client_id = str(uuid.uuid4())
        logging.info(f"为新连接生成客户端ID: {client_id}")
    else:
        logging.info(f"使用现有客户端ID: {client_id}")
        
    logger = logging.getLogger(f"WS:{client_id}")
    logger.setLevel(logging.DEBUG)
    
    # 初始化音频统计
    audio_stats[client_id] = {
        "first_chunk_time": None,
        "last_chunk_time": None,
        "total_chunks": 0,
        "total_bytes": 0,
        "max_chunk_size": 0,
        "min_chunk_size": float('inf'),
    }
    
    try:
        # 接受WebSocket连接
        await websocket.accept()
        logger.info(f"已接受WebSocket连接: {client_id}")
        
        # 保存连接
        active_connections[client_id] = websocket
        
        # 发送连接成功消息
        await websocket.send_json({
            "event": "connected",
            "client_id": client_id
        })
        
        # 注册客户端并设置回调函数
        logger.info(f"正在注册转写客户端: {client_id}")
        processor = None
        
        try:
            # 注册转写客户端
            processor = await service.register_client(
                client_id=client_id,
                callback=send_transcription_result,
                debug_mode=True
            )
            
            if not processor:
                logger.error(f"注册客户端失败: {client_id}")
                await websocket.send_json({
                    "event": "error",
                    "message": "注册客户端失败"
                })
                return
                
            logger.info(f"客户端注册成功: {client_id}")
            
        except Exception as e:
            logger.error(f"注册客户端时发生异常: {e}")
            logger.error(traceback.format_exc())
            await websocket.send_json({
                "event": "error",
                "message": f"服务器错误: {str(e)}"
            })
            return
        
        # 监听客户端消息
        while True:
            try:
                # 接收消息
                data = await websocket.receive()
                
                # 处理二进制音频数据
                if "bytes" in data:
                    audio_data = data["bytes"]
                    now = time.time()
                    
                    # 记录详细的音频调试信息
                    logger.debug(f"收到音频数据: {len(audio_data)} 字节")
                    
                    # 更新音频统计
                    stats = audio_stats[client_id]
                    if stats["first_chunk_time"] is None:
                        stats["first_chunk_time"] = now
                        logger.info(f"收到第一个音频块: {len(audio_data)} 字节")
                    
                    stats["last_chunk_time"] = now
                    stats["total_chunks"] += 1
                    stats["total_bytes"] += len(audio_data)
                    stats["max_chunk_size"] = max(stats["max_chunk_size"], len(audio_data))
                    stats["min_chunk_size"] = min(stats["min_chunk_size"], len(audio_data))
                    
                    # 每10块记录一次统计信息
                    if stats["total_chunks"] % 20 == 0:
                        logger.info(f"音频统计: 总块数={stats['total_chunks']}, 总字节数={stats['total_bytes']}, "
                                   f"平均块大小={stats['total_bytes']/stats['total_chunks']:.1f}, "
                                   f"持续时间={now - stats['first_chunk_time']:.1f}秒")
                    
                    # 处理音频数据
                    start_time = time.time()
                    try:
                        # 发送音频数据到音频处理器
                        await service.process_audio(client_id, audio_data)
                        process_time = time.time() - start_time
                        
                        if process_time > 0.1:  # 如果处理时间超过100ms，记录警告
                            logger.warning(f"音频处理耗时较长: {process_time*1000:.1f}ms")
                    except Exception as e:
                        logger.error(f"处理音频数据时出错: {str(e)}")
                        logger.error(traceback.format_exc())
                
                # 处理文本消息（配置和控制命令）
                elif "text" in data:
                    try:
                        message = json.loads(data["text"])
                        event_type = message.get("event")
                        logger.debug(f"收到文本消息: {event_type}")
                        
                        # 处理配置事件
                        if event_type == "config":
                            config = message.get("config", {})
                            language = config.get("language", "zh")
                            # 同时支持model和model_type字段
                            model_type = config.get("model_type") or config.get("model", "tiny")
                            target_language = config.get("target_language", "en")
                            
                            # 立即发送配置接收确认
                            await websocket.send_json({
                                "event": "config_received",
                                "status": "processing"
                            })
                            
                            # 更新客户端配置
                            logger.info(f"更新客户端配置: language={language}, model_type={model_type}, target_language={target_language}")
                            success = await service.update_client_config(
                                client_id=client_id,
                                language=language,
                                model_type=model_type,
                                target_language=target_language
                            )
                            
                            if success:
                                await websocket.send_json({
                                    "event": "config_updated",
                                    "status": "success",
                                    "config": config
                                })
                                logger.info(f"配置已更新: language={language}, model_type={model_type}")
                            else:
                                await websocket.send_json({
                                    "event": "config_updated",
                                    "status": "error",
                                    "message": "更新配置失败"
                                })
                    except json.JSONDecodeError:
                        logger.warning(f"接收到无效的JSON消息")
            except WebSocketDisconnect:
                logger.info(f"WebSocket断开连接: {client_id}")
                break
            except Exception as e:
                logger.error(f"处理WebSocket消息时出错: {e}")
                logger.error(traceback.format_exc())
                try:
                    await websocket.send_json({
                        "event": "error",
                        "message": f"处理消息时出错: {str(e)}"
                    })
                except:
                    logger.error("无法发送错误消息，连接可能已断开")
                    break
                    
    except WebSocketDisconnect:
        logger.info(f"WebSocket断开连接: {client_id}")
    except Exception as e:
        logger.error(f"WebSocket处理时出错: {e}")
        logger.error(traceback.format_exc())
    finally:
        # 清理资源
        if client_id in active_connections:
            del active_connections[client_id]
        if client_id in audio_stats:
            stats = audio_stats[client_id]
            if stats["first_chunk_time"] is not None:
                duration = time.time() - stats["first_chunk_time"]
                logger.info(f"会话统计: 总块数={stats['total_chunks']}, 总字节数={stats['total_bytes']}, "
                          f"持续时间={duration:.1f}秒")
            del audio_stats[client_id]
        await service.unregister_client(client_id)
        logger.info(f"客户端资源已清理: {client_id}")

async def send_transcription_result(text: str) -> None:
    """将转写结果发送给客户端
    
    此函数是关键的回调函数，会被音频处理器调用来发送转写结果
    """
    logger = logging.getLogger("WebSocket-Transcription")
    logger.setLevel(logging.DEBUG)
    
    # 添加非常明显的分隔线，确保在终端中可以看到转写结果
    logger.info("\n" + "="*80)
    logger.info("【收到转写结果】")
    logger.info(f"转写文本: {text}")
    
    # 检查文本是否为空
    if not text or not text.strip():
        logger.warning(f"转写结果为空，跳过发送")
        logger.info("="*80 + "\n")
        return
    
    # 获取活动连接客户端ID列表
    clients = list(active_connections.keys())
    logger.info(f"当前活动连接: {len(clients)}个")
    for client_id in clients:
        logger.info(f" - 客户端: {client_id}")
    
    # 记录活动连接状态
    if not clients:
        logger.warning("没有活动的WebSocket连接，无法发送转写结果")
        logger.info("="*80 + "\n")
        return
    
    # 获取当前时间戳
    timestamp = time.time()
    
    # 异步处理文本（文本优化和翻译）
    try:
        # 从TranscriptionService查询客户端语言配置
        for client_id in clients:
            try:
                # 获取客户端语言配置
                client_language = "zh"  # 默认中文
                target_language = "en"  # 默认翻译为英文
                
                # 如果能获取到客户端配置，则使用配置中的语言
                if client_id in transcription_service.clients:
                    client = transcription_service.clients[client_id]
                    client_language = client.get('language', 'zh')
                    target_language = client.get('target_language', 'en')
                
                # 调用文本处理服务
                logger.info(f"开始处理文本: {text[:30]}...")
                processed_result = await text_processor.process_text(
                    text=text,
                    source_language=client_language,
                    target_language=target_language
                )
                
                logger.info(f"文本处理结果: 优化={processed_result['refined_text'][:30]}...")
                logger.info(f"文本处理结果: 翻译={processed_result['translation'][:30]}...")
                
                # 向客户端发送结果
                websocket = active_connections[client_id]
                
                # 构造消息
                message = {
                    "event": "transcription",
                    "text": text,
                    "refined_text": processed_result.get("refined_text", text),
                    "translation": processed_result.get("translation", ""),
                    "timestamp": timestamp,
                    "source_language": client_language,
                    "target_language": target_language
                }
                
                # 记录WebSocket状态
                ws_state = None
                if hasattr(websocket, 'client_state'):
                    ws_state = websocket.client_state.name
                logger.info(f"客户端 {client_id} WebSocket状态: {ws_state}")
                
                # 检查WebSocket连接状态
                if ws_state == "CONNECTED":
                    # 发送消息
                    logger.info(f"正在发送转写结果到客户端: {client_id}")
                    logger.debug(f"消息内容: {message}")
                    await websocket.send_json(message)
                    logger.info(f"已成功发送转写结果到客户端: {client_id}")
                else:
                    logger.warning(f"客户端WebSocket连接状态异常: {client_id}, 状态: {ws_state}")
                    
            except Exception as e:
                logger.error(f"处理并发送文本到客户端 {client_id} 时出错: {str(e)}")
                logger.error(traceback.format_exc())
                
                # 尝试发送原始文本
                try:
                    websocket = active_connections[client_id]
                    await websocket.send_json({
                        "event": "transcription",
                        "text": text,
                        "timestamp": timestamp
                    })
                    logger.info(f"已发送原始转写结果到客户端: {client_id}")
                except:
                    logger.error(f"发送原始转写结果到客户端 {client_id} 时出错")
    
    except Exception as e:
        logger.error(f"处理转写结果时出错: {str(e)}")
        logger.error(traceback.format_exc())
        
        # 向所有连接的客户端发送原始转写结果
        for client_id in clients:
            try:
                websocket = active_connections[client_id]
                # 构造消息
                message = {
                    "event": "transcription",
                    "text": text,
                    "timestamp": timestamp
                }
                await websocket.send_json(message)
                logger.info(f"已发送原始转写结果到客户端: {client_id}")
            except Exception as e:
                logger.error(f"发送转写结果到客户端 {client_id} 时出错: {str(e)}")
    
    # 记录发送结果统计
    logger.info(f"转写结果处理完成")
    logger.info("="*80 + "\n")

@router.get("/test")
async def test_websocket_route():
    """测试WebSocket连接是否正常工作"""
    return {"status": "WebSocket路由正常", "active_connections": len(active_connections)} 