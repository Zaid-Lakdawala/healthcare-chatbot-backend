from openai import OpenAI
client = OpenAI()

class EmbedService:

    @staticmethod
    def embed_text_list(text_list):
        result = client.embeddings.create(
            model="text-embedding-3-large",
            input=text_list
        )
        return [e.embedding for e in result.data]

    @staticmethod
    def embed_query(text):
        result = client.embeddings.create(
            model="text-embedding-3-large",
            input=text
        )
        return result.data[0].embedding
