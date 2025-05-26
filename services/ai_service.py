import g4f
from g4f.Provider import provider
from config.config import config

g4f.Provider.OpenRouter.api_key = config.OPENROUTER_API_KEY

class AIService:

    @staticmethod
    async def get_response(content: str, ai_promt: str) -> str:
        response = await g4f.ChatCompletion.create_async(
            model="deepseek/deepseek-chat-v3-0324:free",
            messages=[
                {"role": "system", "content": ai_promt},
                {"role": "user", "content": content}
            ],
            web_search=False,
            provider=g4f.Provider.OpenRouter
        )
        return response