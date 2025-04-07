from typing import Dict, Optional, List, Callable, Any
import logging
import asyncio
from app.audio.audio_processor import AudioProcessor
import traceback
import time

class TranscriptionService:
    """转写服务，管理音频处理和转写"""
    
    def __init__(self):
        """初始化转写服务"""
        self.clients = {}
        self.logger = logging.getLogger("TranscriptionService")
        self.logger.setLevel(logging.DEBUG)
        
    async def register_client(self, client_id, callback=None, language='zh', model_type='tiny', debug_mode=False):
        """注册新的转写客户端"""
        self.logger.info(f"=== 注册新的转写客户端 ===")
        self.logger.info(f"客户端ID: {client_id}")
        self.logger.info(f"语言: {language}, 模型: {model_type}, 调试模式: {debug_mode}")
        
        try:
            # 创建音频处理器
            processor = AudioProcessor(
                language=language,
                model_type=model_type,
                callback=callback,
                debug_mode=debug_mode
            )
            
            # 存储客户端信息
            self.clients[client_id] = {
                'processor': processor,
                'language': language,
                'model_type': model_type,
                'callback': callback,
                'debug_mode': debug_mode,
                'registered_at': time.time()
            }
            
            # 启动处理器
            await processor.start()
            
            self.logger.info(f"客户端 {client_id} 注册成功，当前客户端数量: {len(self.clients)}")
            return processor
        except Exception as e:
            self.logger.error(f"注册客户端 {client_id} 时出错: {str(e)}")
            self.logger.error(traceback.format_exc())
            return None
    
    async def process_audio(self, client_id, audio_data):
        """处理音频数据"""
        if client_id not in self.clients:
            self.logger.warning(f"客户端 {client_id} 未注册，无法处理音频")
            return False
        
        try:
            client = self.clients[client_id]
            processor = client['processor']
            
            # 记录详细的音频处理日志
            self.logger.debug(f"处理客户端 {client_id} 的音频数据，大小: {len(audio_data)} 字节")
            
            # 检查处理器状态
            if not processor.running:
                self.logger.warning(f"客户端 {client_id} 的处理器未运行，尝试重新启动")
                await processor.start()
            
            # 发送音频数据到处理器
            start_time = time.time()
            await processor.process_audio(audio_data)
            process_time = time.time() - start_time
            
            # 记录处理时间
            if process_time > 0.1:  # 如果处理时间超过100ms，记录警告
                self.logger.warning(f"音频处理耗时较长: {process_time*1000:.1f}ms")
            else:
                self.logger.debug(f"音频处理完成: {process_time*1000:.1f}ms")
            
            return True
        except Exception as e:
            self.logger.error(f"处理客户端 {client_id} 的音频数据时出错: {str(e)}")
            self.logger.error(traceback.format_exc())
            return False
    
    async def unregister_client(self, client_id):
        """注销转写客户端"""
        if client_id in self.clients:
            self.logger.info(f"注销客户端 {client_id}")
            try:
                # 停止处理器
                client = self.clients[client_id]
                processor = client['processor']
                await processor.stop()
                
                # 删除客户端信息
                del self.clients[client_id]
                self.logger.info(f"客户端 {client_id} 已注销，剩余客户端数量: {len(self.clients)}")
                return True
            except Exception as e:
                self.logger.error(f"注销客户端 {client_id} 时出错: {str(e)}")
                self.logger.error(traceback.format_exc())
                return False
        else:
            self.logger.warning(f"客户端 {client_id} 不存在，无需注销")
            return True
    
    async def update_client_config(
        self, 
        client_id, 
        language=None, 
        model_type=None, 
        debug_mode=None,
        enable_realtime_transcription=None,
        use_main_model_for_realtime=None,
        realtime_model_type=None,
        realtime_processing_pause=None,
        stabilization_window=None,
        match_threshold=None,
        noise_suppression=None
    ):
        """更新客户端配置"""
        if client_id not in self.clients:
            self.logger.warning(f"客户端 {client_id} 未注册，无法更新配置")
            return False
        
        self.logger.info(f"=== 更新客户端 {client_id} 配置 ===")
        try:
            client = self.clients[client_id]
            processor = client['processor']
            callback = client['callback']
            
            # 记录配置变更
            if language is not None and language != client.get('language'):
                self.logger.info(f"语言: {client.get('language')} -> {language}")
                client['language'] = language
            
            if model_type is not None and model_type != client.get('model_type'):
                self.logger.info(f"模型: {client.get('model_type')} -> {model_type}")
                client['model_type'] = model_type
            
            if debug_mode is not None and debug_mode != client.get('debug_mode'):
                self.logger.info(f"调试模式: {client.get('debug_mode')} -> {debug_mode}")
                client['debug_mode'] = debug_mode

            # 更新实时转写配置
            if enable_realtime_transcription is not None:
                client['enable_realtime_transcription'] = enable_realtime_transcription
                self.logger.info(f"实时转写: {enable_realtime_transcription}")

            if use_main_model_for_realtime is not None:
                client['use_main_model_for_realtime'] = use_main_model_for_realtime
                self.logger.info(f"使用主模型进行实时转写: {use_main_model_for_realtime}")

            if realtime_model_type is not None:
                client['realtime_model_type'] = realtime_model_type
                self.logger.info(f"实时转写模型: {realtime_model_type}")

            if realtime_processing_pause is not None:
                client['realtime_processing_pause'] = realtime_processing_pause
                self.logger.info(f"实时处理暂停时间: {realtime_processing_pause}")

            if stabilization_window is not None:
                client['stabilization_window'] = stabilization_window
                self.logger.info(f"稳定化窗口: {stabilization_window}")

            if match_threshold is not None:
                client['match_threshold'] = match_threshold
                self.logger.info(f"匹配阈值: {match_threshold}")

            if noise_suppression is not None:
                client['noise_suppression'] = noise_suppression
                self.logger.info(f"噪声抑制: {noise_suppression}")
            
            # 停止旧处理器
            await processor.stop()
            
            # 创建新处理器
            new_processor = AudioProcessor(
                language=client['language'],
                model_type=client['model_type'],
                callback=callback,
                debug_mode=client.get('debug_mode', False),
                enable_realtime_transcription=client.get('enable_realtime_transcription', True),
                use_main_model_for_realtime=client.get('use_main_model_for_realtime', True),
                realtime_model_type=client.get('realtime_model_type', 'tiny'),
                realtime_processing_pause=client.get('realtime_processing_pause', 0.2),
                stabilization_window=client.get('stabilization_window', 2),
                match_threshold=client.get('match_threshold', 10),
                noise_suppression=client.get('noise_suppression', False)
            )
            
            # 更新客户端处理器
            client['processor'] = new_processor
            
            # 启动新处理器
            await new_processor.start()
            
            self.logger.info(f"客户端 {client_id} 配置更新成功")
            return True
        except Exception as e:
            self.logger.error(f"更新客户端 {client_id} 配置时出错: {str(e)}")
            self.logger.error(traceback.format_exc())
            return False

    async def cleanup(self) -> None:
        """清理所有客户端资源"""
        for client_id in list(self.clients.keys()):
            await self.unregister_client(client_id) 