import g4f

class AIService:
    @staticmethod
    async def get_response(prompt: str) -> str:
        try:
            response = await g4f.ChatCompletion.create_async(
                model=g4f.models.gpt_3_5_turbo,
                messages=[{"role": "user", "content": prompt}],
            )
            return response
        except Exception as e:
            return f"Ошибка при получении ответа: {str(e)}"