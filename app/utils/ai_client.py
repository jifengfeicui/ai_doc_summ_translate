import json
from typing import Any, Dict, List, Optional

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models import Model, KnownModelName
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.providers.ollama import OllamaProvider

from app.utils.logger import logger


class AIClient:
    """基础 AI 客户端类"""
    def __init__(self, url: str, model_name: str, **kwargs):
        self.url = url
        self.model_name = model_name
        self.agent: Optional[Agent] = None
        
        # 默认参数配置
        self.default_params = {
            'temperature': kwargs.get('temperature', 0.7),
            'max_tokens': kwargs.get('max_tokens', 4096),
            'top_p': kwargs.get('top_p', 0.9),
        }

    def respond(self, prompt: str, **kwargs) -> str:
        """响应单一提示词"""
        pass

    def respond_chat(self, prompt: Dict[str, Any], **kwargs) -> str:
        """响应聊天格式提示词"""
        pass

    def chat_return_json(self, prompt: str, response_format: Any, **kwargs) -> Dict[str, Any]:
        """返回 JSON 格式响应"""
        pass


class PydanticAIClient(AIClient):
    """使用 Pydantic AI 的统一客户端"""
    
    def __init__(self, url: str, model_name: str, provider: str = "openai", **kwargs):
        """
        初始化 Pydantic AI 客户端
        
        Args:
            url: API 端点 URL
            model_name: 模型名称
            provider: 提供商类型 (openai, ollama 等)
            **kwargs: 其他参数 (temperature, max_tokens, top_p 等)
        """
        super().__init__(url, model_name, **kwargs)
        self.provider_type = provider
        
        # 确保 URL 格式正确
        base_url = f"http://{url}/v1" if not url.startswith("http") else f"{url}/v1"
        
        # 创建模型实例
        if provider == "openai":
            # 使用 OpenAI Provider
            provider_instance = OpenAIProvider(base_url=base_url, api_key="EMPTY")
            self.model = OpenAIChatModel(
                model_name=model_name,
                provider=provider_instance
            )
        elif provider == "ollama":
            # 使用 Ollama Provider
            provider_instance = OllamaProvider(base_url=base_url)
            self.model = OpenAIChatModel(
                model_name=model_name,
                provider=provider_instance
            )
        else:
            # 其他提供商可以直接使用模型名称
            self.model = model_name
        
        # 创建 Agent
        self.agent = Agent(self.model)
    
    def respond(self, prompt: str, **kwargs) -> str:
        """
        响应单一提示词
        
        Args:
            prompt: 提示词内容
            **kwargs: 可选参数 (temperature, max_tokens 等)
            
        Returns:
            模型响应的文本内容
        """
        try:
            # 合并默认参数和传入参数
            params = {**self.default_params, **kwargs}
            
            # Pydantic AI 的 run_sync 支持 model_settings
            model_settings = {}
            if 'temperature' in params:
                model_settings['temperature'] = params['temperature']
            if 'max_tokens' in params:
                model_settings['max_tokens'] = params['max_tokens']
            if 'top_p' in params:
                model_settings['top_p'] = params['top_p']
            
            result = self.agent.run_sync(prompt, model_settings=model_settings if model_settings else None)
            
            # 处理 AgentRunResult 对象
            if hasattr(result, 'response') and hasattr(result.response, 'parts') and len(result.response.parts) > 0:
                # 从 response.parts[0].content 获取文本内容
                return result.response.parts[0].content.strip()
            else:
                # 尝试其他可能的属性
                if hasattr(result, 'output'):
                    return str(result.output).strip()
                elif hasattr(result, 'content'):
                    return result.content.strip()
                else:
                    return str(result).strip()
        except Exception as e:
            logger.error(f"模型响应异常: {e}")
            return ""
    
    def respond_chat(self, prompt: Dict[str, Any], **kwargs) -> str:
        """
        响应聊天格式提示词
        
        Args:
            prompt: 包含 messages 的字典
            **kwargs: 可选参数 (temperature, max_tokens 等)
            
        Returns:
            模型响应的文本内容
        """
        try:
            messages = prompt.get("messages", [])
            if not messages:
                return ""
            
            # 将消息转换为用户提示
            # Pydantic AI 会自动处理系统消息和用户消息
            user_prompt = ""
            system_prompt = ""
            
            for msg in messages:
                role = msg.get("role", "")
                content = msg.get("content", "")
                
                if role == "system":
                    system_prompt = content
                elif role == "user":
                    user_prompt = content
            
            # 如果只有系统消息，将其作为用户提示
            final_prompt = user_prompt if user_prompt else system_prompt
            
            # 如果有系统提示且有用户提示，组合它们
            if system_prompt and user_prompt:
                final_prompt = f"{system_prompt}\n\n{user_prompt}"
            
            # 合并默认参数和传入参数
            params = {**self.default_params, **kwargs}
            
            # 构建 model_settings
            model_settings = {}
            if 'temperature' in params:
                model_settings['temperature'] = params['temperature']
            if 'max_tokens' in params:
                model_settings['max_tokens'] = params['max_tokens']
            if 'top_p' in params:
                model_settings['top_p'] = params['top_p']
            
            # 如果有系统提示，临时更新 Agent
            temp_agent = self.agent
            if system_prompt and not hasattr(self.agent, '_system_prompt'):
                temp_agent = Agent(
                    self.model,
                    system_prompt=system_prompt
                )
                
            result = temp_agent.run_sync(final_prompt, model_settings=model_settings if model_settings else None)
            
            # 处理 AgentRunResult 对象
            if hasattr(result, 'response') and hasattr(result.response, 'parts') and len(result.response.parts) > 0:
                # 从 response.parts[0].content 获取文本内容
                return result.response.parts[0].content.strip()
            else:
                # 尝试其他可能的属性
                if hasattr(result, 'output'):
                    return str(result.output).strip()
                elif hasattr(result, 'content'):
                    return result.content.strip()
                else:
                    return str(result).strip()
        except Exception as e:
            logger.error(f"模型聊天响应异常: {e}")
            return ""
    
    def chat_return_json(self, prompt: str, response_format: Any, **kwargs) -> Dict[str, Any]:
        """
        返回 JSON 格式响应
        
        Args:
            prompt: 提示词内容
            response_format: 期望的响应格式 (Pydantic 模型或字典)
            **kwargs: 可选参数 (temperature, max_tokens 等)
            
        Returns:
            解析后的 JSON 字典
        """
        try:
            # 合并默认参数和传入参数
            params = {**self.default_params, **kwargs}
            
            # 构建 model_settings
            model_settings = {}
            if 'temperature' in params:
                model_settings['temperature'] = params['temperature']
            if 'max_tokens' in params:
                model_settings['max_tokens'] = params['max_tokens']
            if 'top_p' in params:
                model_settings['top_p'] = params['top_p']
            
            # 如果 response_format 是 Pydantic 模型类，使用结构化输出
            if isinstance(response_format, type) and issubclass(response_format, BaseModel):
                agent = Agent(self.model, result_type=response_format)
                result = agent.run_sync(prompt, model_settings=model_settings if model_settings else None)
                
                # 处理结果
                if hasattr(result, 'output') and isinstance(result.output, response_format):
                    return result.output.model_dump()
                else:
                    logger.warning(f"无法获取预期的 Pydantic 模型输出，尝试其他方法")
            
            # 请求 JSON 格式并解析
            json_prompt = f"{prompt}\n\n请以 JSON 格式返回结果。"
            result = self.agent.run_sync(json_prompt, model_settings=model_settings if model_settings else None)
            
            # 处理 AgentRunResult 对象
            if hasattr(result, 'response') and hasattr(result.response, 'parts') and len(result.response.parts) > 0:
                response_text = result.response.parts[0].content.strip()
            elif hasattr(result, 'output'):
                response_text = str(result.output).strip()
            else:
                response_text = str(result).strip()
                
            # 尝试解析 JSON
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析异常: {e}")
            return {}
        except Exception as e:
            logger.error(f"模型 JSON 响应异常: {e}")
            return {}


class OllamaClient(PydanticAIClient):
    """Ollama 客户端 - 使用 Pydantic AI"""
    
    def __init__(self, url: str, model_name: str, **kwargs):
        """
        初始化 Ollama 客户端
        
        Args:
            url: Ollama 服务器地址 (例如: "127.0.0.1:11434")
            model_name: 模型名称
            **kwargs: 其他参数 (temperature, max_tokens, top_p 等)
        """
        # 确保 URL 格式正确
        if not url.startswith("http"):
            url = f"http://{url}"
        
        # 可以直接传入 system_prompt 参数
        system_prompt = kwargs.pop('system_prompt', None)
        
        super().__init__(url, model_name, provider="ollama", **kwargs)
        
        # 如果提供了系统提示，更新 Agent
        if system_prompt:
            self.agent = Agent(
                self.model,
                system_prompt=system_prompt
            )
            
        logger.info(f"已初始化 Ollama 客户端: {url} - 模型: {model_name}")


class LMClient(PydanticAIClient):
    """LM Studio 客户端 - 使用 Pydantic AI"""
    
    def __init__(self, url: str, model_name: str, **kwargs):
        """
        初始化 LM Studio 客户端
        
        Args:
            url: LM Studio 服务器地址
            model_name: 模型名称
            **kwargs: 其他参数 (temperature, max_tokens, top_p 等)
        """
        # 确保 URL 格式正确
        if not url.startswith("http"):
            url = f"http://{url}"
        
        # 可以直接传入 system_prompt 参数
        system_prompt = kwargs.pop('system_prompt', None)
            
        super().__init__(url, model_name, provider="openai", **kwargs)
        
        # 如果提供了系统提示，更新 Agent
        if system_prompt:
            self.agent = Agent(
                self.model,
                system_prompt=system_prompt
            )
            
        logger.info(f"已初始化 LM Studio 客户端: {url} - 模型: {model_name}")


if __name__ == '__main__':
    # 测试代码
    print("测试 Ollama 客户端...")
    
    # 创建客户端
    client = OllamaClient("127.0.0.1:11434", "gemma3:27b")
    
    # 测试简单响应
    response = client.respond("你好，请介绍一下 Python 语言")
    print(f"简单响应测试:\n{response}\n")
    
    # 测试聊天响应
    chat_response = client.respond_chat({
        "messages": [
            {"role": "system", "content": "你是一个有帮助的助手。"},
            {"role": "user", "content": "Python 的主要特点是什么？"}
        ]
    })
    print(f"聊天响应测试:\n{chat_response}\n")
    
    print("测试完成！")
