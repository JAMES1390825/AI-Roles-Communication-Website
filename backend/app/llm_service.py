# app/llm_service.py
import os
from openai import AsyncOpenAI # 修改为 AsyncOpenAI
from dotenv import load_dotenv
from typing import List, Dict, Optional, Union # 导入 Union
import httpx # 导入 httpx
import base64 # 导入 base64
import io # 导入 io 模块
from qiniu import Auth, put_data, etag # 导入七牛云 SDK 相关的模块
import uuid # 导入 uuid 模块

load_dotenv(override=True) # 强制覆盖已存在的环境变量

# 从 .env 文件获取 Qwen API Key 和 Base URL
QINIU_OPENAI_API_KEY = os.getenv("QINIU_OPENAI_API_KEY")
QINIU_OPENAI_BASE_URL = os.getenv("QINIU_OPENAI_BASE_URL") # 直接从 .env 获取，确保一致
QINIU_OPENAI_ASR_MODEL_ID = os.getenv("QINIU_OPENAI_ASR_MODEL_ID", "asr") # ASR Model ID
QINIU_OPENAI_TTS_MODEL_ID = os.getenv("QINIU_OPENAI_TTS_MODEL_ID", "tts") # TTS Model ID
# 七牛云存储 (Kodo) 配置
QINIU_ACCESS_KEY = os.getenv("QINIU_ACCESS_KEY")
QINIU_SECRET_KEY = os.getenv("QINIU_SECRET_KEY")
QINIU_BUCKET_NAME = os.getenv("QINIU_BUCKET_NAME")
QINIU_DOMAIN = os.getenv("QINIU_DOMAIN") # 七牛云存储的自定义域名或测试域名

if not QINIU_OPENAI_API_KEY:
    raise ValueError("QINIU_OPENAI_API_KEY environment variable not set.")
if not QINIU_OPENAI_BASE_URL:
    raise ValueError("QINIU_OPENAI_BASE_URL environment variable not set.")
if not QINIU_ACCESS_KEY or not QINIU_SECRET_KEY or not QINIU_BUCKET_NAME or not QINIU_DOMAIN:
    raise ValueError("Qiniu Kodo environment variables (ACCESS_KEY, SECRET_KEY, BUCKET_NAME, DOMAIN) must be set.")

print(f"QINIU_OPENAI_BASE_URL: {QINIU_OPENAI_BASE_URL}") # 添加调试打印
# 初始化 AsyncOpenAI 客户端，指向七牛云的兼容接口
client = AsyncOpenAI(
    api_key=QINIU_OPENAI_API_KEY,
    base_url=QINIU_OPENAI_BASE_URL,
)

async def get_qwen_response(
    system_prompt: str,
    chat_history: List[Dict[str, str]], # 聊天历史，包含 sender_type 和 content
    user_message: str,
    few_shot_examples: Optional[List[Dict[str, str]]] = None,
    temperature: float = 0.7,
    max_tokens: int = 500,
    model: str = "deepseek-v3" # 使用七牛云 Node.js 示例中的模型ID
) -> str:
    messages = []

    # 添加系统提示
    messages.append({"role": "system", "content": system_prompt})

    # 添加 Few-Shot 示例
    if few_shot_examples:
        for example in few_shot_examples:
            if "user" in example:
                messages.append({"role": "user", "content": example["user"]})
            if "ai" in example: # 注意 Few-shot 示例中的 AI 回复在 OpenAI API 中通常用 'assistant' 角色
                messages.append({"role": "assistant", "content": example["ai"]})

    # 添加历史消息
    for msg in chat_history:
        # 将我们数据库中的 sender_type ('user' 或 'ai') 转换为 LLM 期望的 role ('user' 或 'assistant')
        role_type = "user" if msg["sender_type"] == "user" else "assistant"
        messages.append({"role": role_type, "content": msg["content"]})

    # 添加当前用户消息
    messages.append({"role": "user", "content": user_message})

    try:
        completion = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"Error calling Qwen API: {e}")
        return "Sorry, I am unable to respond at the moment."

async def get_asr_transcript(audio_file_like: Union[str, io.BytesIO], model: str = QINIU_OPENAI_ASR_MODEL_ID) -> str:
    """将音频文件转录为文本"""
    try:
        audio_content: bytes
        filename: str

        if isinstance(audio_file_like, io.BytesIO):
            audio_content = audio_file_like.getvalue()
            filename = f"audio-{uuid.uuid4()}.webm" # 生成唯一文件名
        elif isinstance(audio_file_like, str):
            with open(audio_file_like, "rb") as f:
                audio_content = f.read()
            filename = os.path.basename(audio_file_like) # 使用原始文件名
        else:
            raise ValueError("audio_file_like must be a BytesIO object or a file path string.")

        # 上传音频到七牛云 Kodo
        public_url = await upload_audio_to_qiniu_kodo(audio_content, filename)
        if not public_url:
            print("Failed to upload audio to Qiniu Kodo.")
            return ""

        # 调用七牛云 ASR API
        url = f"{QINIU_OPENAI_BASE_URL}/voice/asr"
        headers = {
            "Authorization": f"Bearer {QINIU_OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "audio": {
                "url": public_url, # 传递公共访问 URL
                "encoding": "webm", # 根据前端录音格式调整
            },
            "request": {
                "language": "zh", # 或根据需要设置为 "en"
                "profanity_filter": False
            }
        }

        print(f"ASR Request URL: {url}")
        print(f"ASR Request Headers: {headers}")
        print(f"ASR Request Payload: {payload}")

        async with httpx.AsyncClient() as http_client:
            response = await http_client.post(url, headers=headers, json=payload)
            response.raise_for_status() # 检查 HTTP 错误
            
            response_data = response.json()
            transcript = response_data.get("data", {}).get("text")
            if not transcript:
                print(f"No transcript found in ASR response. Response: {response_data}")
                return ""
            return transcript
    except httpx.HTTPStatusError as e:
        print(f"Error calling Qiniu ASR API: {e} - {e.response.text}")
        return ""
    except Exception as e:
        print(f"Error in get_asr_transcript: {e}")
        return ""

async def get_tts_audio(text: str, model: str = QINIU_OPENAI_TTS_MODEL_ID, voice_type: str = "qiniu_zh_female_tmjxxy") -> bytes:
    """将文本转为音频并返回音频字节流 (使用七牛云 TTS API)"""
    url = f"{QINIU_OPENAI_BASE_URL}/voice/tts"
    headers = {
        "Authorization": f"Bearer {QINIU_OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "audio": {
            "voice_type": voice_type, # 使用七牛云的音色类型
            "encoding": "mp3", # 音频编码
            "speed_ratio": 1.0
        },
        "request": {
            "text": text
        }
    }

    print(f"TTS Request URL: {url}") # 调试打印
    print(f"TTS Request Headers: {headers}") # 调试打印
    print(f"TTS Request Payload: {payload}") # 调试打印
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status() # 检查 HTTP 错误
            
            response_data = response.json()
            base64_audio = response_data.get("data")
            if not base64_audio:
                raise ValueError("No audio data found in TTS response.")
            
            return base64.b64decode(base64_audio) # 解码 base64 音频数据
    except httpx.HTTPStatusError as e:
        print(f"Error calling Qiniu TTS API: {e} - {e.response.text}")
        return b""
    except Exception as e:
        print(f"Error calling Qiniu TTS API: {e}")
        return b""
 
async def upload_audio_to_qiniu_kodo(audio_content: bytes, filename: str) -> Optional[str]:
    """将音频内容上传到七牛云 Kodo，并返回公共访问 URL。"""
    try:
        q = Auth(QINIU_ACCESS_KEY, QINIU_SECRET_KEY)
        token = q.upload_token(QINIU_BUCKET_NAME, filename, 3600) # 有效期 1 小时
        
        # 使用 put_data 上传文件
        # put_data 返回三个值：ret, info, url_path
        # ret 包含上传成功后的文件信息，info 包含响应信息
        ret, info = put_data(token, filename, audio_content)
        
        if ret and info.status_code == 200:
            # 上传成功，构建公共访问 URL
            public_url = f"https://{QINIU_DOMAIN}/{filename}"
            print(f"Successfully uploaded {filename} to Qiniu Kodo. URL: {public_url}")
            return public_url
        else:
            print(f"Failed to upload {filename} to Qiniu Kodo. Info: {info}")
            return None
    except Exception as e:
        print(f"Error uploading audio to Qiniu Kodo: {e}")
        return None