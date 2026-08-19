import re
import uvicorn
import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from transformers import AutoModelForCausalLM, AutoTokenizer

app = FastAPI(title="Qwen3.5-0.8B Engine")

# 直接锁定 Qwen3.5 0.8B 模型标识
MODEL_ID = "Qwen/Qwen3.5-0.8B"

print(f"正在加载模型: {MODEL_ID} ...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    torch_dtype="auto",
    device_map="auto",
    trust_remote_code=True
)
print("Qwen3.5-0.8B 加载完成！")

SYSTEM_PROMPT = """你是一个专业的占卜与心理咨询辅助 AI。你的任务是接收用户的长段背景描述与占卜诉求，输出结构化的提炼、带相关度评分的标签与分析框架。

请严格按照以下 JSON 格式返回结果，不要包含任何 markdown 以外的多余文字：

{
  "summary": "一句话精简摘要（15-20字以内）",
  "tags": [
    {
      "name": "标签名称",
      "score": 0.95
    }
  ],
  "divination_framework": [
    {
      "dimension": "解析维度名称",
      "focus": "解读重点"
    }
  ]
}

【提取规则】
1. summary：极简提炼核心疑问（如：某事是否为某种征兆/某人是否会重逢）。
2. tags：提取1-4个相关标签，并为每个标签给出 0.0 到 1.0 之间的相关度评分（0.9 以上代表核心问题，0.6-0.8 代表次要关联）。
3. divination_framework：提供3-4个切入方向。
4. 语言限制：全局只能使用标准简体中文，严禁出现任何非中文字符或异常乱码。"""

def clean_text(text: str) -> str:
    pattern = r'[^\u4e00-\u9fa5\x20-\x7E\u3000-\u303f\uff01-\uff0f\uff1a-\uff20\uff5e\n\r\t]'
    return re.sub(pattern, '', text)

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    temperature: Optional[float] = 0.2

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest):
    if not request.messages:
        raise HTTPException(status_code=400, detail="Messages cannot be empty")

    user_content = request.messages[-1].content

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content}
    ]
    
    text_input = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )

    model_inputs = tokenizer([text_input], return_tensors="pt").to(model.device)

    with torch.no_grad():
        generated_ids = model.generate(
            **model_inputs,
            max_new_tokens=400,
            temperature=request.temperature,
            do_sample=True if request.temperature > 0 else False
        )

    generated_ids = [
        output_ids[len(input_ids):] 
        for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
    ]
    response_text = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
    cleaned_response = clean_text(response_text)

    prompt_tokens = len(model_inputs.input_ids[0])
    completion_tokens = len(generated_ids[0])

    return {
        "id": "qwen3.5-0.8b-chat",
        "model": MODEL_ID,
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": cleaned_response
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens
        }
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
