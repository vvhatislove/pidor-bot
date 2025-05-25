import g4f
from g4f.Provider import provider
from config.config import config
g4f.Provider.OpenRouter.api_key = config.OPENROUTER_API_KEY

class AIService:

    @staticmethod
    async def get_response(prompt: str) -> str:
        print(prompt)
        response = await g4f.ChatCompletion.create_async(
            model="deepseek/deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            web_search=False,
            provider=g4f.Provider.OpenRouter
        )
        return response