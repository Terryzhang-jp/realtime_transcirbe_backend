from typing import Dict, Optional, List, Callable, Any
import logging
import asyncio
from app.audio.audio_processor import AudioProcessor
import traceback
import time
from app import config

class TranscriptionService:
    """转写服务，管理音频处理和转写"""
    
    def __init__(self):
        """初始化转写服务"""
        self.clients = {}
        self.client_history = {}  # 存储每个客户端的历史句子，格式: {client_id: [句子1, 句子2, 句子3]}
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
                'callback': callback,
                'language': language,
                'model_type': model_type,
                'debug_mode': debug_mode,
                'target_language': 'en',  # 默认翻译为英文
                'registered_at': time.time(),
                'keywords': [],  # 添加关键词列表字段
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
            #self.logger.debug(f"处理客户端 {client_id} 的音频数据，大小: {len(audio_data)} 字节")
            
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
                #self.logger.debug(f"音频处理完成: {process_time*1000:.1f}ms")
                pass
            
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
        target_language=None
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
            
            # 记录所有传入的配置参数
            self.logger.info(f"配置更新请求参数:")
            self.logger.info(f"  language: {language}")
            self.logger.info(f"  model_type: {model_type}")
            self.logger.info(f"  target_language: {target_language}")
            
            # 记录配置变更
            if language is not None and language != client.get('language'):
                self.logger.info(f"语言: {client.get('language')} -> {language}")
                client['language'] = language
            
            if model_type is not None and model_type != client.get('model_type'):
                self.logger.info(f"模型: {client.get('model_type')} -> {model_type}")
                client['model_type'] = model_type
            
            if target_language is not None and target_language != client.get('target_language'):
                self.logger.info(f"翻译目标语言: {client.get('target_language')} -> {target_language}")
                client['target_language'] = target_language
            
            # 验证语言和模型是否在支持的列表中
            if client['language'] not in config.AVAILABLE_LANGUAGES:
                self.logger.error(f"不支持的语言: {client['language']}")
                return False
            
            if client['model_type'] not in config.AVAILABLE_MODELS:
                self.logger.error(f"不支持的模型: {client['model_type']}")
                return False
            
            # 检查语言和模型组合是否兼容
            self.logger.info(f"验证语言和模型组合: {client['language']}/{client['model_type']}")
            
            self.logger.info(f"停止旧处理器...")
            # 停止旧处理器
            await processor.stop()
            
            # 记录创建新处理器的详细信息
            self.logger.info(f"创建新的AudioProcessor实例:")
            self.logger.info(f"  语言: {client['language']}")
            self.logger.info(f"  模型: {client['model_type']}")
            
            # 创建新处理器
            try:
                # 添加更多日志和异常捕获
                self.logger.info(f"语言检查: {client['language']} 是否在可用语言列表中: {'是' if client['language'] in config.AVAILABLE_LANGUAGES else '否'}")
                self.logger.info(f"模型检查: {client['model_type']} 是否在可用模型列表中: {'是' if client['model_type'] in config.AVAILABLE_MODELS else '否'}")
                self.logger.info(f"调用AudioProcessor构造函数...")
                
                try:
                    new_processor = AudioProcessor(
                        language=client['language'],
                        model_type=client['model_type'],
                        callback=callback,
                        debug_mode=client.get('debug_mode', False)
                    )
                except ValueError as ve:
                    self.logger.error(f"创建处理器时出现值错误: {ve}")
                    raise
                except RuntimeError as re:
                    self.logger.error(f"创建处理器时出现运行时错误: {re}")
                    raise
                except Exception as e:
                    self.logger.error(f"创建处理器时出现其他错误: {e}, 类型: {type(e).__name__}")
                    raise
                
                self.logger.info(f"AudioProcessor构造成功，处理器配置:")
                self.logger.info(f"  语言: {new_processor.language}")
                self.logger.info(f"  模型: {new_processor.model_type}")
                self.logger.info(f"  设备: {new_processor.device}")
                
                # 更新客户端处理器
                client['processor'] = new_processor
                
                # 启动新处理器
                self.logger.info(f"启动新处理器...")
                await new_processor.start()
                
                self.logger.info(f"客户端 {client_id} 配置更新成功")
                return True
            except Exception as e:
                self.logger.error(f"创建新处理器失败: {str(e)}")
                self.logger.error(traceback.format_exc())
                # 尝试恢复旧处理器
                self.logger.info(f"尝试恢复旧处理器...")
                try:
                    await processor.start()
                    self.logger.info(f"旧处理器恢复成功")
                except Exception as e2:
                    self.logger.error(f"恢复旧处理器失败: {str(e2)}")
                return False
        except Exception as e:
            self.logger.error(f"更新客户端 {client_id} 配置时出错: {str(e)}")
            self.logger.error(traceback.format_exc())
            return False
    
    def get_client_config(self, client_id):
        """获取客户端配置"""
        if client_id not in self.clients:
            return {"error": "客户端未注册"}
        
        client = self.clients[client_id]
        # 返回客户端配置的副本
        return {
            "client_id": client_id,
            "language": client.get('language', 'unknown'),
            "model_type": client.get('model_type', 'unknown'),
            "target_language": client.get('target_language', 'en'),
            "debug_mode": client.get('debug_mode', False),
            "registered_at": client.get('registered_at', 0),
            "processor_running": client['processor'].running if 'processor' in client else False,
            "active": True,
            "keywords": client.get('keywords', []),  # 添加关键词字段
        }
    
    async def update_client_keywords(self, client_id: str, keywords: List[str]) -> bool:
        """更新客户端关键词
        
        这不会触发AudioProcessor重启，只是更新存储的关键词列表。
        
        Args:
            client_id: 客户端ID
            keywords: 关键词列表
            
        Returns:
            bool: 是否成功更新关键词
        """
        if client_id not in self.clients:
            self.logger.warning(f"客户端 {client_id} 未注册，无法更新关键词")
            return False
        
        try:
            self.logger.info(f"更新客户端 {client_id} 关键词: {keywords}")
            self.clients[client_id]['keywords'] = keywords
            return True
        except Exception as e:
            self.logger.error(f"更新客户端 {client_id} 关键词时出错: {str(e)}")
            self.logger.error(traceback.format_exc())
            return False
    
    def get_client_keywords(self, client_id: str) -> List[str]:
        """获取客户端关键词列表
        
        Args:
            client_id: 客户端ID
            
        Returns:
            List[str]: 关键词列表，如果客户端不存在返回空列表
        """
        if client_id not in self.clients:
            self.logger.warning(f"客户端 {client_id} 未注册，无法获取关键词")
            return []
        
        return self.clients[client_id].get('keywords', [])

    async def cleanup(self) -> None:
        """清理所有客户端资源"""
        for client_id in list(self.clients.keys()):
            await self.unregister_client(client_id) 