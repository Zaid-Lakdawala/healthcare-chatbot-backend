class ChunkService:
    @staticmethod
    def split_text(text, chunk_size=250):
        words = text.split()
        chunks = []

        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i:i + chunk_size])
            chunks.append(chunk)

        return chunks
