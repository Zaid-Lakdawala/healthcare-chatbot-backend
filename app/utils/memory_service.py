
from openai import OpenAI
from app.models.memory_model import MemoryModel

client = OpenAI()


class MemoryService:

    @staticmethod
    def summarize_conversation(messages: list[str | dict]) -> str:
      
        text_lines = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            text_lines.append(f"{role}: {content}")
        convo_text = "\n".join(text_lines)

        if not convo_text.strip():
            return ""

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a memory compression engine. "
                        "From this conversation, extract ONLY long-term relevant information "
                        "about the user: personality, stable preferences, important facts, "
                        "health or lifestyle patterns, and other details that would be useful "
                        "for future conversations. DO NOT include transient chit-chat, greetings, "
                        "or one-off context."
                    ),
                },
                {"role": "user", "content": convo_text},
            ],
        )

        return resp.choices[0].message.content.strip()

    @staticmethod
    def merge_summaries(old: str, new: str) -> str:
        """
        Combines old + new memory into a single concise summary.
        """
        if not old and not new:
            return ""
        if not old:
            return new
        if not new:
            return old

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are merging two memory summaries into one. "
                        "Keep it short, remove duplicates, keep only stable facts, "
                        "preferences, and important history."
                    ),
                },
                {
                    "role": "user",
                    "content": f"OLD MEMORY:\n{old}\n\nNEW MEMORY:\n{new}",
                },
            ],
        )

        return resp.choices[0].message.content.strip()

    @staticmethod
    def update_user_memory(user_id: str, conversation: dict):
       
        if not conversation:
            return

        messages = conversation.get("messages", [])
        if not messages:
            return

        # 1. Summarize this conversation
        new_summary = MemoryService.summarize_conversation(messages)
        if not new_summary:
            return

        # 2. Load old summary
        old_summary = MemoryModel.get_summary(user_id)

        # 3. Merge
        merged = MemoryService.merge_summaries(old_summary, new_summary)

        # 4. Store
        MemoryModel.save_summary(user_id, merged)
